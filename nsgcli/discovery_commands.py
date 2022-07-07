"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2022 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import json

from . import api
from . import response_formatter
from . import sub_command

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

discovery status dev                  print status of last 10 discovery attempts for the device 
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
        resp_dict = self.get_command(request)  # nsgcli.api.call(self.base_url, 'GET', request, token=self.token)
        if resp_dict is None:
            return
        if not resp_dict.get('enabled', None):
            print('Discovery is disabled by configuration')
            return
        if resp_dict.get('paused', None):
            print('Discovery is paused')
        # both 'in progress' and 'queue' are lists of dictionaries. Order matters.
        queue = resp_dict.get('queue', [])
        communicating = resp_dict.get('inProgress', []) or resp_dict.get('communicating', [])
        pending_processing = resp_dict.get('pendingProcessing', [])
        currently_processing = resp_dict.get('currentlyProcessing', [])
        if queue:
            print('Queue:')
            self.print_queue_contents(queue, headers=['device ID', 'name', 'address', 'duration, sec'],
                                      columns=['deviceID', 'name', 'address', 'duration'])
        else:
            print('Discovery queue is empty')
        print()
        if communicating:
            print('Discovery tasks in progress (unordered because tasks are executed in parallel):')
            self.print_queue_contents(communicating, headers=['device ID', 'name', 'address', 'duration, sec'],
                                      columns=['deviceID', 'name', 'address', 'duration'])
        else:
            print('Discovery servers are idle')
        print()
        if pending_processing:
            print('Pending processing (the last device is the next up): {0}'.format(len(pending_processing)))
            self.print_queue_contents(pending_processing,
                                      headers=['device ID', 'name', 'address', 'duration, sec'],
                                      columns=['id', 'name', 'address', 'duration'])
            print()
        if currently_processing:
            print('Currently processing device: {}'.format(currently_processing))
            print()

    def print_queue_contents(self, input_list, headers, columns, sort_column=None):
        discovery_queue_format = '    {0:10}  {1:32}  {2:16}  {3}'
        print(discovery_queue_format.format(*headers))
        if sort_column is not None:
            sorted_list = sorted(input_list, key=lambda t: t[sort_column])
        else:
            sorted_list = input_list
        for task in sorted_list:
            column_values = [task[c] for c in columns]
            print(discovery_queue_format.format(*column_values))

    def do_submit(self, arg):
        comps = arg.split(' ')
        for d in comps:
            request = 'v2/nsg/discovery/net/{0}/submit/{1}'.format(self.netid, d)
            response = self.post_command(request)
            if response is not None:
                self.print_response(response)

    def do_pause(self, arg):
        request = 'v2/nsg/discovery/net/{0}/pause'.format(self.netid)
        response = self.post_command(request)
        if response is not None:
            self.print_response(response)

    def do_resume(self, arg):
        request = 'v2/nsg/discovery/net/{0}/resume'.format(self.netid)
        response = self.post_command(request)
        if response is not None:
            self.print_response(response)

    def do_start(self, arg):
        print('command "discovery start" has been deprecated')

    def do_status(self, arg):
        comps = arg.split(' ')
        # query must sort by createdAt in descending order because we take 10 entries with offset 0, so to get
        # 10 most recent ones, we have to sort in descending order
        request = 'v2/ui/net/{0}/reports/discovery/list?limit=10&q={1}&most_recent=false&s=createdAt&desc&fields={2}'.format(
            self.netid, comps[0], ','.join(DISCOVERY_STATUS_FIELDS))
        response = self.get_command(request)
        if response is not None:
            self.print_status(response, DISCOVERY_STATUS_FIELDS)

    def print_status(self, response, fields):
        table_formatter = \
            response_formatter.ResponseFormatter(column_title_mapping=FIELD_NAME_MAPPING, time_format=self.time_format)
        statuses = response['reports']
        # repackage response
        resp = {'columns': [{'text': f} for f in fields], 'rows': []}
        rows = []
        for status in statuses:
            row = [status[f] for f in fields]
            rows.append(row)
        # reverse list of rows to make the most recent report appear at the bottom
        resp['rows'] = list(reversed(rows))
        table_formatter.print_result_as_table(resp)

    def get_command(self, request, data=None):
        """
        execute simple command via API call and return deserialized response
        """
        try:
            response = api.call(self.base_url, 'GET', request, data=data, token=self.token)
        except Exception as ex:
            print('ERROR: {0}'.format(ex))
            return None
        else:
            return self.deserialize_response(response)

    def post_command(self, request, data=None):
        """
        execute simple command via API call and return deserialized response
        """
        try:
            response = api.call(self.base_url, 'POST', request, data=data, token=self.token)
        except Exception as ex:
            print('ERROR: {0}'.format(ex))
            return None
        else:
            return self.deserialize_response(response)

    def deserialize_response(self, response):
        with response:
            status = response.status_code
            if status != 200:
                for line in response.iter_lines():
                    err = self.get_error(json.loads(line))
                    print('ERROR: {0}'.format(err))
                    return None
            return json.loads(response.content)
