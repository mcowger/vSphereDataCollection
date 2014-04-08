__author__ = 'mcowger'
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

#logging.config.fileConfig("%s/%s" % (os.getcwd(), "logcfg.cfg"))
logging.basicConfig(filename='debug.log', level=logging.DEBUG, format="%(asctime)s|%(name)s|%(levelname)s|%(module)s:%(lineno)d|%(message)s")
logger = logging.getLogger()

r = StrictRedis()

utils.collect_and_write_data("VirtualMachine")