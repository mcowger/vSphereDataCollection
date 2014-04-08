

import utils
import logging, logging.config
import os

from pprint import pprint
import time
from RedisConfigHelper import RedisConfigHelper
from redis import StrictRedis
from rq import Queue

q = Queue(connection=StrictRedis())

logging.config.fileConfig("%s/%s" % (os.getcwd(), "logcfg.cfg"))
logger = logging.getLogger()

config = RedisConfigHelper()
config.clear()
config.set_config('vcenter_host','172.16.59.128')
config.set_config('vcenter_user', 'root')
config.set_config('vcenter_pwd', 'vmware')
config.set_config('data_dir',"/tmp")
config.set_config('interval',60)
config.set_config('run_count',5)


logger.info("Starting")

q.enqueue(utils.collect_and_write_data,"VirtualMachine")
