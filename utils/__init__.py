__author__ = 'mcowger'

from itertools import chain
from itertools import izip_longest

from pyVim.connect import SmartConnect, Disconnect

import pyVmomi
from pyVmomi import vim
import logging
import os
import datetime
from progress.bar import Bar
import json
from pprint import pprint, pformat

si = None
pm = None

allCounters = None


logger = logging.getLogger(__name__)

relevant_metrics = ['datastore', 'virtualDisk', 'disk', 'cpu', 'mem']

_all_objects = {}





def get_perf(query_specs,group_size=10):


    bar = Bar('Collecting\t', suffix='%(percent)d%% ETA: %(eta)ds ', max=len(query_specs) / group_size)
    logger.info("Submitting %s requests in groups of %d" % (len(query_specs),group_size))
    results = []
    group_count = 0


    for group in grouper(10, query_specs, None):

        group_count += 1
        logger.debug("Submitting group: %d" % group_count)
        results += pm.QueryPerf([x for x in list(group) if x != None])
        bar.next()

    bar.finish()
    return results

def build_perf_request_for_type(obj_type,limit=None):
    query_specs = []
    entities = get_objects_by_type(obj_type)
    bar = Bar('Inventory\t', suffix='%(percent)d%% ETA: %(eta)ds ', max=len(entities))

    runcount = 0
    for entity in entities:
        runcount += 1
        if limit is not None and runcount > limit:
            return query_specs
        bar.next()
        query_specs.append(build_query_spec_for_entity(entity))
    bar.finish()
    return query_specs

def build_datasets_from_results(results):
    all_data = {}
    bar = Bar('Processing Data\t', suffix='%(percent)d%% ETA: %(eta)ds ', max=len(results))
    for entity_result in results:
        #The 'entity_result' in this case is a EntityMetricCSV object
        #logger.debug(entity_result)
        #requestintervalstart, start, requestintervalend, end = entity_result.sampleInfoCSV.split(",")
        logger.debug("Processng result from entity: %s" % entity_result.entity.name)

        trash,timestamp = entity_result.sampleInfoCSV.split(',')
        if not all_data.has_key(timestamp): all_data[timestamp] = []
        bar.next()

        for result in entity_result.value:


            counterId = result.id.counterId
            counterInfo = [x for x in allCounters if x.key == counterId][0]
            combined_name = ".".join([counterInfo.groupInfo.key, counterInfo.nameInfo.key, result.id.instance]).rstrip('.')
            value = result.value
            all_data[timestamp].append({'entity':entity_result.entity.name, 'metric':combined_name,'value':value})


            #logger.debug("%s = %s" % (combined_name,value))
            #logger.debug(value)
            #logger.debug("Entity %s:counterId:%d:%s.%s.%s = %s" % (entity_result.entity.name, counterId,counterInfo.groupInfo.key,counterInfo.nameInfo.key, instance, value) )


    bar.finish()
    return all_data

def build_query_spec_for_entity(entity):

    available_metrics = pm.QueryAvailablePerfMetric(entity=entity,intervalId=20)
    if len(available_metrics) < 1:
        logger.debug("Entity %s had 0 available metrics - not including in requests" % entity.name)
        return None
    counterInfos = pm.QueryPerfCounter([metric.counterId for metric in available_metrics])
    relevant_metric_ids = [counterinfo.key for counterinfo in counterInfos if counterinfo.groupInfo.key in relevant_metrics]
    metrics_to_get = [metric for metric in available_metrics if metric.counterId in relevant_metric_ids]
    logger.debug("Entity %s had %d/%d relevant metrics" % (entity.name, len(metrics_to_get), len(available_metrics)))
    #logger.debug("Request metrid IDs: %s" % relevant_metric_ids)
    query_spec = vim.PerfQuerySpec()
    query_spec.entity = entity
    #query_spec.endTime = si.serverClock
    #query_spec.startTime = (si.serverClock - datetime.timedelta(minutes=60))
    query_spec.intervalId = 20
    query_spec.maxSample = 1
    query_spec.format = "csv"
    query_spec.metricId = metrics_to_get
    return query_spec


def get_objects_by_type(obj_type):
    """


    :rtype : list
    :param obj_type: The object type to get (VirtualMachine,HostSystem, etc) 
    :return: [obj_type]
    """
    return _all_objects["vim." + obj_type]



def grouper(n, iterable, fillvalue=None):
    """grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"""
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

def get_metrics_for_entity(entity, intervalId=20, endTime=None, beginTime=5):
    beginTime = si.serverClock - datetime.timedelta(beginTime=5)
    endTime = si.serverClock
    return pm.QueryAvailablePerfMetric(entity=entity, intervalId=intervalId, endTime=endTime, beginTime=beginTime)

def writedata(datadict,data_dir):
    with open(data_dir+ '/' + '.csv','wb') as output:
        json.dump(datadict, output,
            sort_keys = True,
            indent = 4,
            separators = (',', ': '),
        )
        #write.writerows(datadict)

def extract_headers(datadict):
    headers = ['timestamp']
    headers += (list(set([metricrecord['metric'] for timestamp in datadict.keys() for metricrecord in datadict[timestamp]])))
    logger.info(headers)
    return headers



def connect(*args, **kwargs):
    logger.info("Connecting to vCenter")
    global si
    global pm
    global allCounters

    if si is None:
        si = SmartConnect(*args, **kwargs)
    if pm is None:
        pm = si.content.perfManager
    logger.info("Evaluating object tree")
    get_subs(si.content.rootFolder)
    allCounters = pm.perfCounter

def disconnect():
    logger.info("Disconnecting from vCenter host")
    Disconnect(si)




def get_subs(thething, level=0):
    if level == 0:
        _all_objects.clear()
        #print "cleared all objects"
    if type(thething).__name__ not in _all_objects.keys():
        _all_objects[type(thething).__name__] = []
        #print "added key " + type(thething).__name__

    # if we have a datacenter object, there are specific subobjects
    if type(thething) is pyVmomi.types.vim.Datacenter:
        #print "added datacenter"
        _all_objects[type(thething).__name__].append(thething)
        for sub in [thething.hostFolder, thething.networkFolder, thething.vmFolder]:
            get_subs(sub, level=level + 1)

    #If we have any kind of object that can contain others (Folders and ResourcePools), lets recurse on ourseves.
    elif type(thething) in [pyVmomi.types.vim.Folder, pyVmomi.types.vim.ResourcePool]:
        #print "added folder or RP " + thething.name
        _all_objects[type(thething).__name__].append(thething)
        for sub in thething.childEntity:
            get_subs(sub, level=level + 1)
    #If we have a compute resource (either a DRS cluster or a single host), lets get its bits:
    elif type(thething) in [pyVmomi.types.vim.ComputeResource, pyVmomi.types.vim.ClusterComputeResource]:
        #print "added cluster or host " + thething.name
        _all_objects[type(thething).__name__].append(thething)
        for elem in chain.from_iterable([thething.host, thething.network, thething.datastore]):
            get_subs(elem, level=level + 1)

    elif type(thething) in [pyVmomi.types.vim.ResourcePool]:
        #print "added RP " + thething.name
        _all_objects[type(thething).__name__].append(thething)
        for elem in chain.from_iterable([thething.resourcePool, thething.vm]):
            get_subs(elem, level=level + 1)

    else:
        #print "added entity " + thething.name
        _all_objects[type(thething).__name__].append(thething)

    return _all_objects


