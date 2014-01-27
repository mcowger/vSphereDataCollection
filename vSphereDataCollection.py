from flask import Flask, render_template, request, jsonify
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl
import pyVmomi
from utils import *
import utils
from pprint import pformat
import json
from urllib import unquote

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

        userinfo = json.loads(unquote(request.cookies.get('vspheredatacollection')));
        print userinfo
        connect(
            host=userinfo['host'],
            user=userinfo['user'],
            pwd=userinfo['password'],
        )
        getSubs(utils.si.content.rootFolder)
        #print pformat(utils.allObjects, indent=4)
        entities = utils.allObjects["vim." + requestedtype]
        #print entities

        print jsonify(result=[vm.name for vm in entities]).data

        return jsonify(result=[vm.name for vm in entities])


    except Exception, e:
        print e.message
        return e.message



if __name__ == '__main__':
    app.run(debug=True)
