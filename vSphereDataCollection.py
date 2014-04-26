from flask import Flask, render_template, request, jsonify, redirect, url_for

import utils

import os
import logging, logging.config

from apscheduler.scheduler import Scheduler

import atexit
import datetime
import shelve
import logging_tree

import config


logging.config.dictConfig(config.loggingconfig)
logger = logging.getLogger()

#logging_tree.printout(node=None)




sched = Scheduler()
sched.start()
atexit.register(lambda: sched.shutdown(wait=False,close_jobstores=True,))




## try to delete file ##

#
# try:
#     os.remove(config.get_config('data_dir') + '/vsphereinventory.gz')
#     os.remove(config.get_config('data_dir') + '/vsphereinventory')
#
# except Exception, e:  ## if failed, report it back to the user ##
#
#      pass
#
# try:
#     os.remove(config.get_config('data_dir') + '/vspheredatacollection.data.gz')
#
# except Exception, e:  ## if failed, report it back to the user ##
#     pass



app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/status', methods=['GET'])
def status():
    liveconfig = shelve.open(config.systemconfig['live_config_file'], writeback=True)
    perf_filename = liveconfig['data_dir'] + '/vspheredatacollection.data.gz'
    inv_filename = liveconfig['data_dir'] + '/vsphereinventory.gz'
    debug_filename = "./debug.log"

    perf_size = 0
    inv_size = 0

    try:
        perf_size = os.path.getsize(perf_filename)
    except:
        perf_size = "NotFound"

    try:
        inv_size = os.path.getsize(inv_filename)
    except:
        inv_size = "NotFound"

    try:
        debug_size = sizeof_fmt(os.path.getsize(debug_filename))
    except:
        debug_size = "NotFound"

    perf_estimate = 0
    try:
        perf_estimate = (perf_size / int(r.get("runs_completed"))) * int(config.get_config('run_count'))
    except:
        pass


    return render_template('status.html',
                           jobs=sched.get_jobs(),
                           datafile_name=perf_filename,
                           datafile_size=sizeof_fmt(perf_size),
                           inventory_name=inv_filename,
                           inventory_size=sizeof_fmt(inv_size),
                           debug_name=debug_filename,
                           debug_size=debug_size,
                           runs = liveconfig['runs_completed'],
                           runs_target = liveconfig['run_count'],
                           perf_estimate = sizeof_fmt(perf_estimate)

    )
    liveconfig.close()

@app.route('/inventory', methods=['GET'])
def inventory():
    sched.add_date_job(
        utils.collect_and_write_inventory,
        date=datetime.datetime.now()+datetime.timedelta(seconds=10)
    )
    return render_template('inventory.html',message="Inventory Collection Background Job Started")

@app.route('/configuration', methods=['GET'])
def collectionsetup():
    liveconfig = shelve.open(config.systemconfig['live_config_file'], writeback=True)
    if len(liveconfig) != 0:
        logger.info("Clearing existing live_config_file: %s" % config.systemconfig['live_config_file'])
        liveconfig.clear()
    liveconfig.sync()
    liveconfig.close()
    return render_template('collectionsetup.html')


@app.route('/pushconfig', methods=['POST'])
def pushconfig():
    try:
        liveconfig = shelve.open(config.systemconfig['live_config_file'], writeback=True)
        liveconfig['vcenter_user'] = request.form['username']
        liveconfig['vcenter_pwd'] = request.form['password']
        liveconfig['run_count'] = int(request.form['runcount'])
        liveconfig['vcenter_host'] =request.form['vcenter']
        liveconfig['interval'] =int(request.form['interval'])
        liveconfig['data_dir'] = config.systemconfig['data_dir']
        logger.debug(liveconfig)
        liveconfig.close()
        return render_template('pushconfig.html',message="Configuration Saved to Database")
    except Exception, e:
        return "Incorrect entry, please try again"


@app.route('/runperf/<requestedtype>', methods=['GET'])
def runperf(requestedtype):
    liveconfig = shelve.open(config.systemconfig['live_config_file'], writeback=True)
    liveconfig["runs_completed"] = 0
    sched.add_interval_job(
        utils.collect_and_write_data,
        args=[requestedtype],
        seconds=liveconfig['interval'],
        max_runs=liveconfig['run_count'],
        start_date=datetime.datetime.now(),
    )

    return redirect(url_for('status'))



def sizeof_fmt(num):
    if type(num) == type(""):
        return "Error"
    for x in ['B', 'KB', 'MB', 'GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
