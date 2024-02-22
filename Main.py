import fmcapi
from Models.AccessPolicy import AccessPolicy
from Models.AccessRule import AccessRule
from Models.Port import Port
from Models.PortGroup import PortGroup
import pandas as pd
import os
import math
from pprint import pprint
from netaddr import IPNetwork, IPRange

def fmc_init():
    with fmcapi.FMC(
        host='192.168.33.193',
        username='admin',#input('Enter the username: '),
        password='GetCon135!!',#input('Enter the password: '),
        autodeploy=False,
    ) as fmc:
        obj = get_network_object(fmc)
        
        print(obj)
        """
        acp = fmcapi.AccessPolicies(fmc).get()
        policies = get_access_policies(acp)

        access_rule_header = ['Access Policy', 'Access Rule', 'Action', 'Enabled', 'Source Networks', 'Source Zones', 'Source Ports', 'Destination Networks', 'Destination Zones', 'Destination Ports']
        rules = []
        for policy in policies:
              accessrules = fmcapi.AccessRules(fmc, acp_id=policy.id).get()
              rules.extend(get_access_rules(fmc, accessrules['items'], policy.name))
        access_rule_data = [(rule.access_policy, rule.name, rule.action, rule.enabled, rule.source_networks, rule.source_zones, rule.source_ports, rule.destination_networks, rule.destination_zones, rule.destination_ports) for rule in rules]
        export_to_excel(access_rule_data, access_rule_header, 'access_rules_v1')"""

        ports_header = ['Group Name', 'Name', 'Protocol', 'Port', 'Size', 'Risky']
        ports = []
        port_groups = []
        protocol_port_objs = fmcapi.ProtocolPortObjects(fmc).get()
        ports.extend(get_ports(fmc, protocol_port_objs['items']))
        port_obj_groups = fmcapi.PortObjectGroups(fmc).get()
        port_groups.extend(get_ports(fmc, port_obj_groups['items']))
        ports_data = [(None, port.name, port.protocol, port.port, port.size, port.is_risky) for port in ports]
        for port_group in port_groups:
                for port in port_group.ports:
                        ports_data.append((port_group.name, port.name, port.protocol, port.port, port.size, port.is_risky))
        export_to_excel(ports_data, ports_header, 'ports')

        equal_ports_header = ['Name', 'Name']
        equal_ports = []
        equal_ports.extend(equal_port_object_finder(ports))
        equal_ports.extend(equal_port_object_finder(port_groups))
        export_to_excel(equal_ports, equal_ports_header, 'equal_ports')

        """equal_network_header = ['Name', 'Value', 'Name', 'Value']
        hosts = fmcapi.Hosts(fmc).get()
        networks = fmcapi.Networks(fmc).get()
        ranges = fmcapi.Ranges(fmc).get()
        calculate_network_size(networks)
        equal_networks = []
        equal_networks.extend(equal_network_object_finder(hosts))
        equal_networks.extend(equal_network_object_finder(networks))
        equal_networks.extend(equal_network_object_finder(ranges))
        equal_networks_data = [(network.split(';')[0], network.split(';')[1], network.split(';')[2], network.split(';')[3]) for network in equal_networks]
        export_to_excel(equal_networks_data, equal_network_header, 'equal_networks')"""

        print('Done')

def get_network_object(fmc):
        netObj = fmcapi.Networks(fmc).get()
        groupObj = fmcapi.NetworkGroups(fmc).get()
        hostObj = fmcapi.Hosts(fmc).get()
        rangeObj = fmcapi.Ranges(fmc).get()
        obj = {}
        for x in netObj['items']:
                obj[x['name']] = 0
        for x in groupObj['items']:
                obj[x['name']] = 0
        for x in hostObj['items']:
                obj[x['name']] = 0
        for x in rangeObj['items']:
                obj[x['name']] = 0
        
        return obj


def get_access_policies(acp):
        policies = []
        for acp in acp['items']:
            id = acp.get('id', None)
            name = acp.get('name', None)
            policies.append(AccessPolicy(id, name))
        
        return policies

def get_access_rules(fmc, accessrules, acp_name):
        rules = []
        for rule in accessrules:
                access_policy = acp_name
                id = rule.get('id', None)
                name = rule.get('name', None)
                action = rule.get('action', None)
                enabled = rule.get('enabled', None)
                source_network, destination_networks, source_depth, dest_depth = get_networks_by_rule(fmc, rule)
                source_zones, destination_zones = get_zones_by_rule(rule)
                source_ports, destination_ports = get_ports_by_rule(fmc, rule)
                rules.append(AccessRule(access_policy, id, name, action, enabled, source_network, source_zones, source_ports, destination_networks, destination_zones, destination_ports))
        return rules

def get_zones_by_rule(rule):
        s_zones = rule.get('sourceZones', None)
        d_zones = rule.get('destinationZones', None)
        if s_zones is not None:
                s_zones =  s_zones['objects'][0]['name']
        if d_zones is not None:
                d_zones =  d_zones['objects'][0]['name']
        return s_zones, d_zones

def get_ports_by_rule(fmc, rule):
        s_ports = rule.get('sourcePorts', None)
        d_ports = rule.get('destinationPorts', None)
        s_ports_list = []
        d_ports_list = []
        if s_ports is not None:
                s_objects = s_ports.get('objects', None)
                s_literals = s_ports.get('literals', None)
                if s_objects is not None:
                        s_ports_list.extend(get_ports(fmc, s_objects))
                elif s_literals is not None:
                        s_ports_list.extend(get_ports(fmc, s_literals))
        if d_ports is not None:
                d_objects = d_ports.get('objects', None)
                d_literals = d_ports.get('literals', None)
                if d_objects is not None:
                        d_ports_list.extend(get_ports(fmc, d_objects))
                elif d_literals is not None:
                        d_ports_list.extend(get_ports(fmc, d_literals))

        return [(port.name, port.protocol, port.port) for port in s_ports_list], [(port.name, port.protocol, port.port) for port in d_ports_list]

def get_ports(fmc, ports):
        port_objs = []
        for port in ports:
                port_id = port.get('id', None)
                port_type = port.get('type', None)
                if port_type == 'ProtocolPortObject':
                        protocol_port_obj = fmcapi.ProtocolPortObjects(fmc, id=port_id).get()
                        port_objs.append(_create_port(port_id, protocol_port_obj))
                elif port_type == 'PortObjectGroup':
                        port_grp = []
                        port_obj_grp = fmcapi.PortObjectGroups(fmc, id=port_id).get()
                        group_name = port_obj_grp['name']
                        flattened_port_obj_grp = flat_port_object_grp(fmc, port_obj_grp)
                        for protocol_port_obj in flattened_port_obj_grp:
                                port_grp.append(_create_port(port_id, protocol_port_obj))
                        port_objs.append(PortGroup(port_id, group_name, port_grp))
                elif port_type == 'ICMPv4PortLiteral':
                        port_objs.append(Port(port_id, None, port_type, port.get('protocol', None), port.get('icmpType', None), '1', True ))
        return port_objs

def flat_port_object_grp(fmc, port_obj_group):
        port_obj = []
        for port in port_obj_group['objects']:
                port_id = port['id']
                port_obj.append(fmcapi.ProtocolPortObjects(fmc, id=port_id).get())
        return port_obj

def _create_port(port_id, port_obj):
        port_name, port_port, port_protocol = _get_ports_info(port_obj)
        port_size = calculate_protocol_port_object_size(port_port)
        is_risky = _is_risky_port([], port_port)
        return Port(port_id, port_name, port_protocol, port_port, port_size, is_risky)

def equal_port_object_finder(ports):
        final = []
        for i in range(len(ports) - 1):
                for j in range(i + 1, len(ports)):
                        if ports[i].__eq__(ports[j]):
                                final.append((ports[i].name, ports[j].name))
        return final

def calculate_protocol_port_object_size(port_port):
        port_size = 1
        if "-" in port_port:
                port_size = int(port_port.split("-")[1]) - int(port_port.split("-")[0])
        return port_size

def _get_ports_info(protocol_port_obj):
        port_name = protocol_port_obj.get('name', None)
        port_port = protocol_port_obj.get('port', None)
        port_protocol = protocol_port_obj.get('protocol', None)
        return port_name, port_port, port_protocol

def _is_risky_port(risky_ports, current_port):
        return True

def get_networks_by_rule(fmc, rule):
        s_networks = rule.get('sourceNetworks', None)
        d_networks = rule.get('destinationNetworks', None)
        s_networks_list = []
        d_networks_list = []
        source_depth = 0
        dest_depth = 0
        if s_networks is not None:
                for s_network in s_networks['objects']:
                        recursive_collector_source = []
                        source_collector, source_depth = recursive(fmc, s_network, recursive_collector_source, source_depth)
                        s_networks_list.extend(source_collector)
        if d_networks is not None:
                for d_network in d_networks['objects']:
                        recursive_collector_destination = []
                        dest_collector, dest_depth = recursive(fmc, d_network, recursive_collector_destination, dest_depth)
                        d_networks_list.extend(dest_collector)
        
        return s_networks_list, d_networks_list, source_depth, dest_depth

def recursive(fmc, network, recursive_collector, depth):
        networks = []
        networks_grp = None

        network_name = network['name']
        network_id = network['id']
        network_type = network['type']

        if network_type == 'Host':
                networks.append(fmcapi.Hosts(fmc, id=network_id).get())
        elif network_type == 'Network':
                networks.append(fmcapi.Networks(fmc, id=network_id).get())
        elif network_type == 'Range':
                networks.append(fmcapi.Ranges(fmc, id=network_id).get())
        elif network_type == 'NetworkGroup':
                networks_grp = fmcapi.NetworkGroups(fmc, id=network_id).get()

                if networks_grp.get('objects', None) is not None:
                        for network_obj in networks_grp['objects']:
                                depth += 1
                                recursive(fmc, network_obj, recursive_collector, depth)

                if networks_grp.get('literals', None) is not None:
                        networks = networks_grp['literals']

        for network in networks:
                network_value = network.get('value', None)
                recursive_collector.append('{} - {}'.format(network_name, network_value))

        return recursive_collector, depth

def equal_network_object_finder(objs):
        final = []
        for i in range(len(objs['items']) - 1):
                for j in range(i + 1, len(objs['items'])):
                        if objs['items'][i]['value'] == objs['items'][j]['value']:
                                final.append('{};{};{};{}'.format(objs['items'][i]['name'], objs['items'][i]['value'], objs['items'][j]['name'], objs['items'][j]['value']))
        return final

def calculate_network_size(objs):
        for obj in objs['items']:
                network = obj['value'].split('/')[0]
                mask = int(obj['value'].split('/')[1])
                if mask > 0:
                        available_clients = int(math.pow(2, 32 - mask) - 2)
        return network, mask, available_clients

def export_to_excel(data, header, excel_name):
        df = pd.DataFrame(data, columns=header)
        export_dir = os.getcwd() + '/Exports'
        df.to_excel('{}/{}.xlsx'.format(export_dir, excel_name))

def get_data_by_name(data, name):
        for item in data['items']:
                 if item['name'] == name:
                        return item
        return None


def process_network_literals(literal):
        resultlist = []
        for item in literal:
                if item['type'] == 'Network': 
                        result = item['value']

                elif item['type'] == 'Host': 
                        result = item['value']
                else: 
                      raise TypeError('Only Network and Host type supported')
                resultlist.append(result)
        return resultlist


def process_network_objects(object, network_groups, networks, ranges, hosts, flattened_groups: dict ):
        resultlist = []
        for item in object:
                result = None
                if item['type'] == 'Network': 
                        network = get_data_by_name(networks,item['name'])
                        if network:
                                result = network['value']
                elif item['type'] == 'Host': 
                        host = get_data_by_name(hosts,item['name'])
                        if host:
                                result = host['value']
                elif item['type'] == 'Range': 
                        range = get_data_by_name(ranges,item['name'])
                        if range:
                                result = range['value']
                elif item['type'] == 'NetworkGroup': 
                        if flattened_groups and item['name'] in flattened_groups: # get from already flattened group
                                group_result = flattened_groups[item['name']]
                        else: #group not processed yet
                                network_group = get_data_by_name(network_groups, item['name'])
                                if network_group:
                                        group_result = process_network_objects(network_group['objects'],network_groups,networks,ranges,hosts,flattened_groups)
                        resultlist.extend(group_result)
                else:
                        raise TypeError('Only NetworkGroup, Range, Network and Host type supported')
                if result:
                        resultlist.append(result)
        return resultlist

def flatten_networks(network_groups,networks,ranges,hosts):
        result = {}
        depth_counter = 0
        for network_group in network_groups['items']:
            objects = network_group.get('objects', None)
            literals = network_group.get('literals', None)
            depth_counter += 1
            if objects: 
                value_1 = process_network_objects(objects,network_groups,networks,ranges,hosts,result)
                result[network_group['name']] = value_1
            if literals:
                value_2 = process_network_literals(literals)
                result[network_group['name']] = value_2
        for network in networks['items']:
                ips = []
                ips.append(network['value'])
                result[network['name']] = ips
        for range in ranges['items']:
                ips = []
                ips.append(range['value'])
                result[range['name']] = ips
        for host in hosts['items']:
                ips = []
                ips.append(host['value'])
                result[host['name']] = ips
        return result

def str_to_ip(list: list):
        result = []
        for item in list:
                if '-' in item:
                        ipr = item.split('-')
                        net = IPRange(ipr[0],ipr[-1])
                else: 
                        net = IPNetwork(item)
                result.append(net)
        return result


def get_network_size(network: list[IPNetwork]):
        size = 0
        for item in network[1]:
                if item.version == 4:
                        size += item.size
        return network[0], size


def get_network_size_from_clients(n):
   
    # Initialize a mask
    mask = 0x80000000  # 0b10000000000000000000000000000000

    # Find the leftmost set bit
    position = 32
    while position > 0:
        if n-mask > 0:
            half_mask = mask >> 1
            if n-mask-half_mask > 0:
                return position
            else:
                   return position - 1
        mask >>= 1
        position -= 1
    
    return 0  # Should not reach here, but just in case


def get_network_size_mask(network: list[IPNetwork]):
        return network[0], (32 - get_network_size_from_clients(get_network_size(network)[1]-1))

def get_equal_networks(networks: dict):
        reverse_dict = {}
        for key, value in networks.items():
                value_tuple = tuple(value)
                reverse_dict.setdefault(value_tuple, set()).add(key)

        result = [values for values in reverse_dict.values() if len(values) > 1]
        
        return result

def test01():
    with fmcapi.FMC(
        host='192.168.33.193',
        username='admin',#input('Enter the username: '),
        password='GetCon135!!',#input('Enter the password: '),
        autodeploy=False,
    ) as fmc:
        hosts = fmcapi.Hosts(fmc=fmc).get()
        networks = fmcapi.Networks(fmc=fmc).get()
        network_ranges = fmcapi.Ranges(fmc=fmc).get()
        network_groups = fmcapi.NetworkGroups(fmc=fmc).get()
        result01 = flatten_networks(network_groups, networks, network_ranges, hosts)
        get_equal_networks(result01)
        result02 = {}

        for key,value in result01.items():
                net_list = str_to_ip(value)
                result02[key] = net_list



        #print(hosts)
        #print(networks)
        #print(network_groups)
        pprint(result01)
        pprint(result02)

        network_size = dict(map(get_network_size, result02.items()))
        network_size_mask = dict(map(get_network_size_mask, result02.items()))

        pprint(network_size)
        pprint(network_size_mask)


#test01()
fmc_init()
