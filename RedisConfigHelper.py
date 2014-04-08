__author__ = 'mcowger'
from redis import StrictRedis
import logging
import os


class RedisConfigHelper(object):
    """Reads Configuration Data from a Redis DB"""

    def __init__(self):
        super(RedisConfigHelper, self).__init__()
        self.r = StrictRedis()

        self.logger = logging.getLogger(__name__)
        self.logger.debug("%s initialized" % __name__ )

    def get_config(self, keyName):
        keyName = "config." + keyName.lower()
        if self.r.exists(keyName.lower()):
            value = self.r.get(keyName)
            self.logger.debug("returning %s for key %s" % (value,keyName))
            return value
        else:
            self.logger.critical("Requested key (%s) not found, returning None" % keyName)
            return None

    def set_config(self,keyName,value):
        keyName = "config." + keyName.lower()
        self.r.set(keyName,value)
        self.logger.debug("Set key %s to value %s" % (keyName,value))

    def clear(self):
        [self.r.delete(key) for key in self.r.keys('config.*')]

