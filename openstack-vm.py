#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
from optparse import OptionParser

from ceilometerclient import client as cmclient
from novaclient import client as noclient


#getting the credentials
keystone = {}
keystone['os_username']='admin'
keystone['os_password']='keystone'
keystone['os_auth_url']='http://lb-vip:5000/v2.0/'
keystone['os_tenant_name']='admin'

#creating an authenticated client
ceilometer_client = cmclient.get_client(2,**keystone)
nova_client = noclient.Client(2, keystone['os_username'], keystone['os_password'], keystone['os_tenant_name'], keystone['os_auth_url'])

def main():
    options = parse_args()
    if options.item=="discovery":
        vm_list()
    elif options.item=="net_discovery":
        net_list()
    else:
        ceilometer_query(options)

#判断入参合法性
def parse_args():
    parser = OptionParser()
    valid_item = ["discovery", "cpu", "net_discovery", "cpu_util", "disk.allocation", "disk.capacity", "disk.read.bytes", "disk.read.bytes.rate", 
    "disk.read.requests", "disk.read.requests.rate", "disk.total.size", "disk.usage", "disk.write.bytes", "disk.write.bytes.rate", 
    "disk.write.requests", "disk.write.requests.rate", "instance", "memory", "memory.usage", "poweron", "vcpus", 
    "network.incoming.bytes", "network.incoming.bytes.rate", "network.outgoing.bytes", "network.outgoing.bytes.rate", 
    "network.incoming.packets", "network.incoming.packets.rate", "network.outgoing.packets", "network.outgoing.packets.rate", 
    "network.incoming.packets.drop", "network.incoming.packets.error", "network.outgoing.packets.drop", "network.outgoing.packets.error"]
    parser.add_option("", "--item", dest="item", help="", action="store", type="string", default=None)
    parser.add_option("", "--uuid", dest="uuid", help="", action="store", type="string", default=None)
    (options, args) = parser.parse_args()
    if options.item not in valid_item:
        parser.error("Item has to be one of: "+", ".join(valid_item))
    return options
  
#使用nova api获取虚机列表
def vm_list():
    r = {"data":[]}

    novas = nova_client.servers.list(detailed='detailed', search_opts={'all_tenants': 1})
    for nova in novas:
        r['data'].append( {"{#VMNAME}":nova.name, "{#VMID}":nova.id} )
    print(json.dumps(r, indent=2, sort_keys=True, encoding="utf-8"))

#使用nova api获取虚机网络，组合为网卡ceilometer查询ID
def net_list():
    r = {"data":[]}
    novas = nova_client.servers.list(detailed='detailed', search_opts={'all_tenants': 1})
    for nova in novas:
        nova_info = nova._info.copy()
        nets = nova.interface_list()
        for net in nets:
            net_info = net._info.copy()
            resource_id = nova_info["OS-EXT-SRV-ATTR:instance_name"] + "-" + nova_info["id"] + "-"  + "ovk"  + net_info["port_id"][0:11]
            if net_info["fixed_ips"]:
                ip_address = net_info["fixed_ips"][0]["ip_address"]
                r['data'].append( {"{#VMNAME}":nova.name, "{#NETID}":resource_id, "{#IPADDRESS}":ip_address} )
            else:
                r['data'].append( {"{#VMNAME}":nova.name, "{#NETID}":resource_id, "{#IPADDRESS}":"no ip"} )
    print(json.dumps(r, indent=2, sort_keys=True, encoding="utf-8"))

#获取对应监控项的监控值
def ceilometer_query(options):
    fields = {'meter_name': options.item,
              'q': [{"field": "resource_id", "op": "eq", "value": options.uuid}],
              'limit': 1}
    samples = ceilometer_client.samples.list(**fields)

    print samples[0].counter_volume

if __name__ == "__main__":
    main()
