__author__ = 'mcowger'

from itertools import chain
from itertools import izip_longest
import datetime
import json
import gzip

from pyVim.connect import SmartConnect, Disconnect
import pyVmomi
from pyVmomi import vim

import logging
import shelve
import config

si = None
pm = None
r = None
allCounters = None


logger = logging.getLogger(__name__)
relevant_metrics = ['datastore', 'virtualDisk', 'disk', 'cpu', 'mem']
_all_objects = {}

class MyJSONEncoder(json.JSONEncoder):
    """A custom JSONEncoder class that knows how to encode core custom
    objects.

    Custom objects are encoded as JSON object literals (ie, dicts) with
    one key, '__TypeName__' where 'TypeName' is the actual name of the
    type to which the object belongs.  That single key maps to another
    object literal which is just the __dict__ of the object encoded."""

    def default(self, obj):
        try:
            # Check for basic type
            return super(MyJSONEncoder, self).default(obj)

        except TypeError:


            if type(obj) in (vim.Network.Summary,
                vim.Datastore.Summary,
                vim.ClusterComputeResource.Summary,
                vim.host.Summary,
                vim.host.Summary.HardwareSummary,
                vim.host.Summary.ConfigSummary,
                vim.Network,
                vim.AboutInfo,
                vim.vm.Summary,
                vim.vm.Summary.ConfigSummary,
                vim.vm.Summary.StorageSummary,
                vim.vm.Summary.GuestSummary,
                vim.Datastore,
                vim.vm.RuntimeInfo,
                vim.vm.DeviceRuntimeInfo):
                return obj.__dict__
            # For anything else
            return "__{}__".format(obj.__class__.__name__)

def json2xml(json_obj, line_padding=""):
    result_list = list()

    json_obj_type = type(json_obj)

    if json_obj_type is list:
        for sub_elem in json_obj:
            result_list.append(json2xml(sub_elem, line_padding))

        return "\n".join(result_list)

    if json_obj_type is dict:
        for tag_name in json_obj:
            sub_obj = json_obj[tag_name]
            result_list.append("%s<%s>" % (line_padding, tag_name))
            result_list.append(json2xml(sub_obj, "\t" + line_padding))
            result_list.append("%s</%s>" % (line_padding, tag_name))

        return "\n".join(result_list)

    return "%s%s" % (line_padding, json_obj)

def collect_and_write_inventory():
    import config
    liveconfig = shelve.open(config.systemconfig['live_config_file'], writeback=True)
    connect(
        host=liveconfig['vcenter_host'],
        user=liveconfig['vcenter_user'],
        pwd=liveconfig['vcenter_pwd'],
    )


    inventory = {}
    inventory['vm'] = [item.summary for item in _all_objects['vim.VirtualMachine']]
    inventory['host'] = [item.summary for item in _all_objects['vim.HostSystem']]
    inventory['cluster'] = [item.summary for item in _all_objects['vim.ClusterComputeResource']]
    #inventory['datacenter'] = [item.summary for item in _all_objects['vim.Datacenter']]
    #inventory['folder'] = [item.summary for item in _all_objects['vim.Folder']]
    inventory['network'] = [item.summary for item in _all_objects['vim.Network']]
    inventory['datastore'] = [item.summary for item in _all_objects['vim.Datastore']]


    with gzip.open(liveconfig['data_dir']+ '/vsphereinventory.gz','w') as output:
        jsondata = json.loads(
            json.dumps(inventory, cls=MyJSONEncoder, indent=4)
        )
        #output.write(json.dumps(inventory, cls=MyJSONEncoder, indent=4))
        #print json2xml(jsondata)
        #output.write(json.dumps(inventory,cls=MyJSONEncoder,indent=4))
        #print json2xml(json.dumps(inventory, cls=MyJSONEncoder, indent=4))
        output.write(json2xml(jsondata).encode('ascii','ignore'))

    liveconfig.close()
    si = None
    pm = None

    allCounters = None

def collect_and_write_data(objtype,limit=None):
    liveconfig = shelve.open(config.systemconfig['live_config_file'], writeback=True)
    connect(
        host=liveconfig['vcenter_host'],
        user=liveconfig['vcenter_user'],
        pwd=liveconfig['vcenter_pwd']
    )
    query_specs = build_perf_request_for_type(objtype, limit)
    results = get_perf(query_specs)
    datadict = build_datasets_from_results(results)
    writedata(datadict, liveconfig['data_dir'])
    liveconfig["runs_completed"] += 1
    si = None
    pm = None
    allCounters = None

    #return "Task %s completed" % task_id

def get_perf(query_specs,group_size=10):


    logger.info("Submitting %s requests in groups of %d" % (len(query_specs),group_size))
    results = []
    group_count = 0


    for group in grouper(10, query_specs, None):

        group_count += 1
        logger.debug("Submitting group: %d" % group_count)
        results += pm.QueryPerf([x for x in list(group) if x != None])


    return results

def build_perf_request_for_type(obj_type,limit=None):
    query_specs = []
    entities = get_objects_by_type(obj_type)


    runcount = 0
    for entity in entities:
        runcount += 1
        if limit is not None and runcount > limit:
            return query_specs

        query_specs.append(build_query_spec_for_entity(entity))

    return query_specs

def build_datasets_from_results(results):
    all_data = {}

    for entity_result in results:

        logger.debug("Processing result from entity: %s" % entity_result.entity.name)

        trash,timestamp = entity_result.sampleInfoCSV.split(',')
        if not all_data.has_key(timestamp): all_data[timestamp] = []

        for result in entity_result.value:
            counterId = result.id.counterId
            counterInfo = [x for x in allCounters if x.key == counterId][0]
            combined_name = ".".join([counterInfo.groupInfo.key, counterInfo.nameInfo.key, result.id.instance]).rstrip('.')
            value = result.value
            all_data[timestamp].append({'entity':entity_result.entity.name, 'metric':combined_name,'value':value})


            #logger.debug("%s = %s" % (combined_name,value))
            #logger.debug(value)
            logger.debug("Entity %s:%s = %s" % (entity_result.entity.name,combined_name, value) )



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
    query_spec.startTime = (si.serverClock - datetime.timedelta(minutes=10))
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

    with gzip.open(data_dir+ '/vspheredatacollection.data.gz','w') as output:
        for timestamp in datadict.keys():
            bar = Bar("Compressing\t", max=len(datadict[timestamp]))
            for line in datadict[timestamp]:
                output.write("\"%s\",\"%s\",\"%s\",%s\n" % (timestamp,line['entity'],line['metric'],line['value']))
                bar.next()
            bar.finish()

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
    global r
    if si is None:
        si = SmartConnect(*args, **kwargs)
    if pm is None:
        pm = si.content.perfManager
    logger.info("Evaluating object tree")
    logger.debug(si.content.rootFolder)
    get_subs(si.content.rootFolder)
    allCounters = pm.perfCounter

def disconnect():
    logger.info("Disconnecting from vCenter host")
    Disconnect(si)

def get_subs(thething, level=0):
    if level == 0:
        _all_objects.clear()
        logger.debug("Cleared all objects at level: %d" % level)
        #print "cleared all objects"
    if type(thething).__name__ not in _all_objects.keys():
        _all_objects[type(thething).__name__] = []
        logger.debug("Created new key in all objects called %s" % type(thething).__name__)
        #print "added key " + type(thething).__name__

    # if we have a datacenter object, there are specific subobjects
    if type(thething) is pyVmomi.types.vim.Datacenter:
        #print "added datacenter"
        _all_objects[type(thething).__name__].append(thething)
        logger.debug("Added datacenter %s" % thething)
        for sub in [thething.hostFolder, thething.networkFolder, thething.vmFolder]:
            get_subs(sub, level=level + 1)

    #If we have any kind of object that can contain others (Folders and ResourcePools), lets recurse on ourseves.
    elif type(thething) in [pyVmomi.types.vim.Folder, pyVmomi.types.vim.ResourcePool]:
        #print "added folder or RP " + thething.name
        _all_objects[type(thething).__name__].append(thething)
        logger.debug("Added object: %s" % thething)
        for sub in thething.childEntity:
            get_subs(sub, level=level + 1)
    #If we have a compute resource (either a DRS cluster or a single host), lets get its bits:
    elif type(thething) in [pyVmomi.types.vim.ComputeResource, pyVmomi.types.vim.ClusterComputeResource]:
        #print "added cluster or host " + thething.name
        _all_objects[type(thething).__name__].append(thething)
        logger.debug("Added object %s" % thething)
        for elem in chain.from_iterable([thething.host, thething.network, thething.datastore]):
            get_subs(elem, level=level + 1)

    elif type(thething) in [pyVmomi.types.vim.ResourcePool]:
        #print "added RP " + thething.name
        _all_objects[type(thething).__name__].append(thething)
        logger.debug("Added object %s" % thething)
        for elem in chain.from_iterable([thething.resourcePool, thething.vm]):
            get_subs(elem, level=level + 1)

    else:
        #print "added entity " + thething.name
        _all_objects[type(thething).__name__].append(thething)
        logger.debug("Added object %s" % thething)

    return _all_objects
