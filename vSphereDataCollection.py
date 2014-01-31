from flask import Flask, render_template, request, jsonify
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl
import pyVmomi
import utils
from pprint import pformat
import json
from urllib import unquote
import traceback

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/collection', methods=['GET'])
def collectionsetup():
    return render_template('collectionsetup.html')




@app.route('/getentities/<requestedtype>', methods=['GET'])
def getentities(requestedtype):




    try:
        print request.cookies.get('vspheredatacollection')
        userinfo = json.loads(unquote(request.cookies.get('vspheredatacollection')));
        print userinfo
        utils.connect(
            host=userinfo['host'],
            user=userinfo['user'],
            pwd=userinfo['password'],
        )
        #get_subs(utils._si.content.rootFolder)
        #print pformat(utils._all_objects, indent=4)
        entities = utils._all_objects["vim." + requestedtype]
        #print entities

        #print jsonify(result=[entity.name for entity in entities]).data

        #return jsonify(result=[entity.name for entity in entities])
        return ""

    except Exception, e:
        print e.message
        traceback.print_stack()
        return e.message



if __name__ == '__main__':
    app.run(debug=True)
