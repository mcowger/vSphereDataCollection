__author__ = 'mcowger'


import pyVim
from pyVmomi import vmodl
from itertools import chain
import pyVmomi



allObjects = {}


def connect(*args, **kwargs):
    global si
    si = pyVim.connect.SmartConnect(*args, **kwargs)


def getSubs(thething):
    if type(thething).__name__ not in allObjects.keys():
        allObjects[type(thething).__name__] = []

    # if we have a datacenter object, there are specific subobjects
    if type(thething) is pyVmomi.types.vim.Datacenter:

        allObjects[type(thething).__name__].append(thething)
        for sub in [thething.hostFolder, thething.networkFolder, thething.vmFolder]:
            getSubs(sub)

    #If we have any kind of object that can contain others (Folders and ResourcePools), lets recurse on ourseves.
    elif type(thething) in [pyVmomi.types.vim.Folder, pyVmomi.types.vim.ResourcePool]:

        allObjects[type(thething).__name__].append(thething)
        for sub in thething.childEntity:
            getSubs(sub)
    #If we have a compute resource (either a DRS cluster or a single host), lets get its bits:
    elif type(thething) in [pyVmomi.types.vim.ComputeResource, pyVmomi.types.vim.ClusterComputeResource]:

        allObjects[type(thething).__name__].append(thething)
        for elem in chain.from_iterable([thething.host, thething.network, thething.datastore]):
            getSubs(elem)

    elif type(thething) in [pyVmomi.types.vim.ResourcePool]:

        allObjects[type(thething).__name__].append(thething)
        for elem in chain.from_iterable([thething.resourcePool, thething.vm]):
            getSubs(elem)

    else:
        allObjects[type(thething).__name__].append(thething)

    return allObjects
