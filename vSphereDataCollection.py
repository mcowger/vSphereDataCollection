from flask import Flask, render_template, request, jsonify, redirect, url_for
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl
import pyVmomi
import utils
from pprint import pformat
import json
from urllib import unquote
import traceback
from RedisConfigHelper import RedisConfigHelper
import os
import logging, logging.config
from redis import StrictRedis
from apscheduler.scheduler import Scheduler
from apscheduler.jobstores.redis_store import RedisJobStore
import atexit
import datetime

logging.basicConfig(filename='debug.log', level=logging.DEBUG, format="%(asctime)s|%(name)s|%(levelname)s|%(module)s:%(lineno)d|%(message)s")
logger = logging.getLogger()

r = StrictRedis()
logger.info("Deleting all job keys")
for key_name in r.keys("jobs.*"):
    r.delete(key_name)

logger.info("Resetting Run Count")
r.set("runs_completed","0")

sched = Scheduler()
sched.add_jobstore(RedisJobStore(), 'redis')
sched.start()
atexit.register(lambda: sched.shutdown(wait=False,close_jobstores=True,))

## try to delete file ##



config = RedisConfigHelper()

try:
    os.remove(config.get_config('data_dir') + '/vsphereinventory.gz')
    os.remove(config.get_config('data_dir') + '/vsphereinventory')

except Exception, e:  ## if failed, report it back to the user ##

     pass

try:
    os.remove(config.get_config('data_dir') + '/vspheredatacollection.data.gz')

except Exception, e:  ## if failed, report it back to the user ##
    pass



app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/status', methods=['GET'])
def status():
    perf_filename = config.get_config('data_dir') + '/vspheredatacollection.data.gz'
    inv_filename = config.get_config('data_dir') + '/vsphereinventory.gz'

    perf_size = 0
    inv_size = 0

    try:
        perf_size = os.path.getsize(perf_filename)
    except:
        pass

    try:
        inv_size = os.path.getsize(inv_filename)
    except:
        pass

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
                           runs = r.get("runs_completed"),
                           runs_target = config.get_config('run_count'),
                           perf_estimate = sizeof_fmt(perf_estimate)

    )

@app.route('/inventory', methods=['GET'])
def inventory():
    utils.collect_and_write_inventory()
    return render_template('inventory.html',message="Inventory Collection Started")

@app.route('/configuration', methods=['GET'])
def collectionsetup():
    return render_template('collectionsetup.html')


@app.route('/pushconfig', methods=['POST'])
def pushconfig():
    config.clear()
    config.set_config('vcenter_user',request.form['username'])
    config.set_config('vcenter_pwd',request.form['password'])
    config.set_config('run_count' , int(request.form['runcount']))
    config.set_config('vcenter_host' , request.form['vcenter'])
    config.set_config('interval' , int(request.form['interval']))
    config.set_config('data_dir','/tmp')

    return render_template('pushconfig.html',message="Configuration Saved to Database")


@app.route('/runperf/<requestedtype>', methods=['GET'])
def runperf(requestedtype):
    r.set("runs_completed","0")
    sched.add_interval_job(
        utils.collect_and_write_data,
        args=[requestedtype],
        seconds=int(config.get_config('interval')),
        max_runs=int(config.get_config('run_count')),
        start_date=datetime.datetime.now(),
        jobstore="redis",
    )

    return redirect(url_for('status'))



def sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
