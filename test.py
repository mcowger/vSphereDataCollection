

import utils
import logging, logging.config
import os
import atexit
from pprint import pprint

hostname="10.5.132.109"
username="AWESOMESAUCE\\mcowger"
password="Habloo12"

logging.config.fileConfig("%s/%s" % (os.getcwd(), "logcfg.cfg"))
logger = logging.getLogger()

logger.info("Starting")

utils.connect(
    host='172.16.142.143',
    user='root',
    pwd='vmware'
)

data_dir = "/tmp/perf_data"

query_specs = utils.build_perf_request_for_type("VirtualMachine",limit=None)
results = utils.get_perf(query_specs)
datadict = utils.build_datasets_from_results(results)
utils.writedata(datadict,data_dir)

#pprint(datadict)

#print pprint(datadict)


utils.disconnect()






# print len(utils._all_objects["vim." + 'VirtualMachine'])
# for vm in utils._all_objects["vim." + 'VirtualMachine']:
#     #print vm.name
#     #for everyVM, get its available counters:
#     available_metrics = pm.QueryAvailablePerfMetric(entity=vm, intervalId=20, endTime=utils._si.serverClock, beginTime=utils._si.serverClock - datetime.timedelta(minutes=5))
#
#     #and get the extended info for the available metrics
#
#
#     if len(available_metrics) < 1:
#         print "VM %s had 0 available metrics - not including in requests" % vm.name
#         continue
#
#     counterInfos = pm.QueryPerfCounter([metric.counterId for metric in available_metrics])
#
#     relevant_metric_ids = [counterinfo.key for counterinfo in counterInfos if counterinfo.groupInfo.key in ['datastore','virtualDisk','disk']]
#     metrics_to_get = [metric for metric in available_metrics if metric.counterId in relevant_metric_ids]
#
#     print "VM %s had %d relevant metrics of %d total" % (vm.name, len(metrics_to_get), len(available_metrics))
#
#     query_spec = vim.PerfQuerySpec()
#     query_spec.entity = vm
#     query_spec.endTime = utils._si.serverClock
#     query_spec.startTime = (utils._si.serverClock - datetime.timedelta(minutes=5))
#     query_spec.intervalId = 300
#     query_spec.maxSample = 10
#     query_spec.metricId = metrics_to_get
#     query_specs.append(query_spec)
#
# results = []
# print "Submitting %s requests" % len(query_specs)
# for group in grouper(10, query_specs, None):
#     print "Submitting group starting with VM: %s" % group[0].entity
#     results += pm.QueryPerf([x for x in list(group) if x != None])
#
# print results
#
#
#
#
#
#


# allCountersDict = {}
# allQuerySpecs = []

#create a dictionary keyd by counterID, because we'll need it later
# for counterinfo in pm.perfCounter:
#     allCountersDict[counterinfo.nameinfo.key] = counterinfo


#first enumerate the available metrics for a given host:

# for host in hosts:
#         hbanames = [{'name':hba.device} for hba in host.config.storageDevice.hostBusAdapter]
#         luns = [{'name':lun.canonicalName,'pretty':lun.displayName} for lun in host.config.storageDevice.scsiLun] 
#         metrics = pm.QueryAvailablePerfMetric(host,intervalId=20) #use interval 300 (5 mins) to get the realtime stats only
#         print metrics
#         metricId = []
#         for metric in metrics:
#             #For each one of these metrics (given by a counterID), we want to get its reasonable description from the CounterInfo object
#             counterinfo = allCountersDict[metric.counterId]
#             #create a MetricId for this run, looking for all instances.
#             pmi = vim.PerformanceManager.MetricId()
#             pmi.instance='*'
#             pmi.counterId=counterinfo.key
#             #and add it to the list of metricId
#             metricId.append(pmi)
#         perfQuerySpec = vim.PerformanceManager.QuerySpec()
#         perfQuerySpec.entity = host
#         perfQuerySpec.maxSample=1
#         perfQuerySpec.metricId = metricId
#         perfQuerySpec.intervalId = 300
#         
#         #perfQuerySpec.startTime = utils._si.serverClock - datetime.timedelta(minutes=29) #specify a startTime of 29 minutes prior to now to use the realtime workarund specified in the SDK
#         #perfQuerySpec.endTime = utils._si.serverClock #see above
#         allQuerySpecs.append(perfQuerySpec)
#         #print perfQuerySpec,perfQuerySpec.metricId
#         #print luns
# allStats = pm.QueryPerf(allQuerySpecs)
#print allStats
        
        
            
            
            
             