"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import collections
import datetime
import json
import time

import nsgcli.api
import nsgcli.sub_command

ROLE_MAP = {
    'manager': 'mgr',
    'primary': 'pri',
    'monitor': 'mon',
    'aggregator': 'agg',
    'agent': 'agt',
    'emulator': 'emu'
}

MEMORY_VALUE_FIELDS = ['fsFreeSpace',
                       'jvmMemFree', 'jvmMemMax', 'jvmMemTotal', 'jvmMemUsed',
                       'redisUsedMemory', 'redisMaxMemory']

PERCENTAGE_VALUE_FIELDS = ['cpuUsage', 'systemMemFreePercent']


def score_roles(roles):
    score1 = 0
    if 'manager' in roles:
        score1 += 1
    if 'primary' in roles:
        score1 += 2
    if 'secondary' in roles:
        score1 += 3
    if 'monitor' in roles:
        score1 += 4
    if 'agent' in roles:
        score1 += 100
    return score1


def compare_members(m1, m2):
    """
    Compare cluster member dictionaries by their role. This can be used to put primary and secondary
    servers at the top of the list
    """
    score1 = score_roles(m1['role'])
    score2 = score_roles(m2['role'])
    if score1 == score2:
        return cmp(m1['name'], m2['name'])
    else:
        return cmp(score1, score2)


def transform_roles(roles):
    """
    Server sends roles as a comma-separated string, e.g. "primary,monitor"
    """
    return ','.join([ROLE_MAP.get(role, '?') for role in sorted(roles.split(',')) if role != 'primary'])


def sizeof_fmt(num, suffix='B'):
    if not num:
        return ''
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.3f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return '%.3f %s%s' % (num, 'Y', suffix)


def percentage_fmt(num):
    return '%.2f %%' % num


def parse_table_response(response):
    """
    Example:
        [
          {
            "rows": [
              [
                "PrimaryServer1",
                54.0
              ]
            ],
            "type": "table",
            "id": "a",
            "columns": [
              {
                "text": "device"
              },
              {
                "text": "tslast(metric)"
              }
            ]
          }
        ]

    :param response:   server response as json object
    :return:           a list of dictionaries where the key is column name and the value comes from the row
    """
    columns = response[0]['columns']
    rows = response[0]['rows']
    res = []
    for row in rows:
        rowdict = collections.OrderedDict()
        for (rc, column) in zip(row, columns):
            cn = column['text']
            rowdict[cn] = rc
        res.append(rowdict)
    return res


class SystemCommands(nsgcli.sub_command.SubCommand, object):
    # prompt = "show system # "

    def __init__(self, base_url, token, net_id, region=None):
        super(SystemCommands, self).__init__(base_url, token, net_id, region)
        if region is None:
            self.prompt = 'show system # '
        else:
            self.prompt = 'show system [' + self.current_region + '] # '

    def status_api_call(self):
        """
        makes API call v2/nsg/cluster/net/{0}/status and returns the response. Note that
        the server does not 'json-stream' response for this API call
        """
        try:
            response = nsgcli.api.call(self.base_url, 'GET', 'v2/nsg/cluster/net/{0}/status'.format(self.netid), token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            return response.status_code, json.loads(response.content)

    def help(self):
        print('Show various system parameters and state variables. Arguments: {0}'.format(self.get_args()))

    def do_os(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'cpuUsage', 'fsFreeSpace', 'systemMemFreePercent', 'localTimeMs', 'systemUptime', 'updatedAt'],
                response)

    def do_tsdb(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'tsDbVarCount', 'tsDbErrors', 'tsDbSaveTime', 'tsDbSaveLag', 'tsDbTimeSinceLastSave'],
                response)

    def do_python(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'pythonErrorsRate'],
                response)

    def do_c3p0(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'c3p0NumConnections', 'c3p0NumBusyConnections', 'c3p0NumIdleConnections',
                 'c3p0NumFailedCheckouts', 'c3p0NumFailedIdleTests'],
                response)

    def do_jvm(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'openFdCount',
                 'jvmMemFree', 'jvmMemMax', 'jvmMemTotal', 'jvmMemUsed',
                 'GCCountRate', 'GCTimeRate', 'updatedAt'],
                response)

    def do_redis(self, arg):
        """
        this does not work at the moment because redis metrics are attached to
        devices that represent redis servers rather than nsg servers
        """
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'redisCommandsRate', 'redisDbSize',
                 'redisUsedMemory', 'redisMaxMemory',
                 'redisUsedCpuSysRate', 'redisUsedCpuUserRate',
                 'redisConnectedClients', 'redisCommandsRate',
                 'redisErrorsRate', 'redisOOMErrorsRate'],
                response)

    def do_lag(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'id', 'role', 'region',
                 'lagAgentAllReceived', 'lagAgentAllSent', 'lagServerAllReceived', 'lagTotal',
                 'processUptime', 'updatedAt'],
                response)

    def do_sum(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'deviceRepoSize', 'numDevices', 'dataPoolSize', 'numVars',
                 'metadataSize', 'metadataMissCount',
                 'lagTotal', 'cycleNumber', 'processUptime', 'updatedAt'],
                response)

    def do_version(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'nsgVersion', 'revision', 'processUptime', 'updatedAt'],
                response)

    def do_status(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_status(response)

    def print_cluster_status(self, status_json):
        print()
        print('Server name:          {0}'.format(status_json['name']))
        print('Region:               {0}'.format(status_json['region']))
        print('Roles:                {0}'.format(','.join(status_json['roles'])))
        print('Status:               {0}'.format(status_json['serverStatus']))
        print('zookeeperClientState: {0}'.format(status_json['zookeeperClientState']))
        print()
        print('Cluster members:')

        self.print_cluster_vars(
            ['name', 'hostName', 'hostAddress', 'pid', 'id', 'role', 'region', 'tier',
             'url', 'status', 'processUptime', 'updatedAt'],
            status_json)

    def print_cluster_vars(self, names, status_json):
        field_width = collections.OrderedDict()
        field_names = {}
        for n in names:
            field_width[n] = 0
            field_names[n] = n

        this_server = status_json['name']

        # sort members once, and do it before I mangle their names
        sorted_members = sorted(status_json['members'], cmp=compare_members)
        for member in sorted_members:
            self.update_member(member, this_server)
            for field in names:
                value = str(member.get(field, ''))
                member[field] = self.transform_value(field, value, outdated=True)

        for member in sorted_members:
            for field in field_width.keys():
                value = str(member.get(field, ''))
                if field_width.get(field, 0) < len(value):
                    field_width[field] = len(value)
                if field_width.get(field, 0) < len(field):
                    field_width[field] = len(field)

        format_lst = ['{m[%s]:<%d}' % (field, field_width[field]) for field in field_width.keys()]
        format_str = '    '.join(format_lst)
        total_width = reduce(lambda x, y: x + y, field_width.values())
        total_width += len(field_width) * 4
        # print(format_str)
        print(format_str.format(m=field_names))
        print('-' * total_width)
        for member in sorted_members:
            print(format_str.format(m=member))
        print('-' * total_width)

    def update_member(self, member, this_server):
        roles = transform_roles(member['role'])
        member['role'] = roles
        name = member['name']
        if this_server == name:
            member['name'] = '*' + name
        else:
            member['name'] = ' ' + name

    # def is_error(self, response):
    #     return isinstance(response, types.DictionaryType) and response.get('status', '').lower() == 'error'

    # def get_error(self, response):
    #     if isinstance(response, types.ListType):
    #         return self.get_error(response[0])
    #     if isinstance(response, types.UnicodeType) or isinstance(response, types.StringType):
    #         return response
    #     return response.get('error', '')

    def transform_value(self, field_name, value, outdated=False):
        if field_name in ['updatedAt', 'localTimeMs']:
            updated_at_sec = float(value) / 1000
            value = datetime.datetime.fromtimestamp(updated_at_sec)
            suffix = ''
            if outdated and time.time() - updated_at_sec > 15:
                suffix = ' outdated'
            return value.strftime('%Y-%m-%d %H:%M:%S') + suffix

        if field_name in ['systemUptime', 'processUptime']:
            td = datetime.timedelta(0, float(value))
            return str(td)

        # if field_name == 'cpuUsage':
        #     return value + ' %'

        if field_name in MEMORY_VALUE_FIELDS and value:
            return sizeof_fmt(float(value))

        if field_name in PERCENTAGE_VALUE_FIELDS and value:
            return percentage_fmt(float(value))
        return value
