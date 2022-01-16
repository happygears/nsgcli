"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2022 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import api
import json
import sub_command

import nsgcli.api
import nsgcli.sub_command
import response_formatter

DISCOVERY_STATUS_FIELDS = ['deviceId', 'address', 'reportName', 'generation',
                           'discoveryStartTime', 'discoveryFinishTime', 'processingFinishTime', 'lagSec',
                           'discoveryPingStatus', 'discoverySnmpStatus', 'discoveryStatus']

FIELD_NAME_MAPPING = {
    'reportName': 'device',
    'lagSec': 'total lag (sec)',
    'discoveryPingStatus': 'ping',
    'discoverySnmpStatus': 'snmp',
    'discoveryStatus': 'status'
}


class DiscoveryCommands(sub_command.SubCommand, object):
    """
    Manage discovery process. Supported commands:

    discovery start      --  deprecated, supported for backward compatibility with NSG clusters
                             that do not implement incremental discovery
    discovery pause
    discovery resume
    discovery schedule device1 device2 device3   where each device is identified by device ID, name, sysName or address

    :param arg: command, possibly with argument (separated by space)
    """

    def __init__(self, base_url, token, net_id, time_format):
        super(DiscoveryCommands, self).__init__(base_url, token, net_id, region=None)
        self.time_format = time_format

    def help(self):
        print("""Operations with network discovery:
        
discovery queue                       shows current state of discovery queue
        
discovery submit dev1 dev2 dev3       put devices in front of the queue. Devices can be
                                      identified by deviceID, name, sysName or address

discovery status dev                  print status of last 5 discovery attempts for the device 
                                      identified by deviceID, name or address

discovery pause                       pause discovery. In-progress discovery processes will finish
                                      but new devices already in the queue are not going to be scheduled
                                              
discovery resume                      resume discovery
""")

    def do_queue(self, arg):
        """
            show discovery status
        """
        request = 'v2/nsg/discovery/net/{0}/queue'.format(self.netid)
        try:
            response = nsgcli.api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            status = response.status_code
            if status != 200:
                print('ERROR: {0}'.format(self.get_error(response)))
            else:
                resp_dict = json.loads(response.content)
                if not resp_dict['enabled']:
                    print('Discovery is disabled by configuration')
                if resp_dict['paused']:
                    print('Discovery is paused')
                    print()
                # both 'in progress' and 'queue' are lists of dictionaries. Order matters.
                in_progress = resp_dict['inProgress']
                discovery_queue_format = '    {0:10}  {1:32}  {2:16}  {3}'
                if in_progress:
                    print('Discovery tasks in progress:')
                    print(discovery_queue_format.format('device ID', 'name', 'address', 'duration, sec'))
                    for task in in_progress:
                        print(discovery_queue_format.format(task['deviceID'], task['name'], task['address'],
                                                            task['duration']))
                    print()
                queue = resp_dict['queue']
                if queue:
                    print('Queue:')
                    print(discovery_queue_format.format('device ID', 'name', 'address', 'duration, sec'))
                    for task in queue:
                        print(discovery_queue_format.format(task['deviceID'], task['name'], task['address'],
                                                            task['duration']))
                else:
                    print('Discovery queue is empty')

    def do_submit(self, arg):
        comps = arg.split(' ')
        for d in comps:
            request = 'v2/nsg/discovery/net/{0}/schedule/{1}'.format(self.netid, d)
            response = self.basic_command(request)
            self.print_response(response)

    def do_pause(self, arg):
        request = 'v2/nsg/discovery/net/{0}/pause'.format(self.netid)
        response = self.basic_command(request)
        self.print_response(response)

    def do_resume(self, arg):
        request = 'v2/nsg/discovery/net/{0}/resume'.format(self.netid)
        response = self.basic_command(request)
        self.print_response(response)

    def do_start(self, arg):
        print('WARNING: command "discovery start" has been deprecated and is supported only for backward '
              'compatibility with NSG clusters that do not support incremental discovery')
        request = 'v2/nsg/discovery/net/{0}/start'.format(self.netid)
        response = self.basic_command(request)
        if response is not None:
            self.print_response(response)

    def do_status(self, arg):
        comps = arg.split(' ')
        request = 'v2/ui/net/{0}/reports/discovery/list?limit=10&q={1}&most_recent=false&s=createdAt&desc&fields={2}'.format(
            self.netid, comps[0], ','.join(DISCOVERY_STATUS_FIELDS))
        response = self.basic_command(request)
        self.print_status(response, DISCOVERY_STATUS_FIELDS)

    def print_status(self, response, fields):
        table_formatter = \
            response_formatter.ResponseFormatter(column_title_mapping=FIELD_NAME_MAPPING, time_format=self.time_format)
        statuses = response['reports']
        # repackage response
        resp = {'columns': [{'text': f} for f in fields], 'rows': []}
        for status in statuses:
            row = [status[f] for f in fields]
            resp['rows'].append(row)
        table_formatter.print_result_as_table(resp)

    def basic_command(self, request, data=None):
        """
        execute simple command via API call and return deserialized response
        """
        try:
            response = api.call(self.base_url, 'GET', request, data=data, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            with response:
                status = response.status_code
                if status != 200:
                    for line in response.iter_lines():
                        err = self.get_error(json.loads(line))
                        print('ERROR: {0}'.format(err))
                        return None
                return json.loads(response.content)
