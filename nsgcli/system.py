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

import api
import sub_command
import response_formatter

ROLE_MAP = {
    'manager': 'mgr',
    'primary': 'pri',
    'monitor': 'mon',
    'aggregator': 'agg',
    'agent': 'agent',
    'emulator': 'emu',
    'indexer': 'idx',
    'discovery': 'disc'
}


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
    return ','.join([ROLE_MAP.get(role, role) for role in sorted(roles.split(',')) if role != 'primary'])


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


def update_member(member, this_server):
    roles = transform_roles(member['role'])
    member['role'] = roles
    name = member['name']
    if this_server == name:
        member['name'] = '*' + name
    else:
        member['name'] = ' ' + name


# noinspection SqlNoDataSourceInspection
class SystemCommands(sub_command.SubCommand, object):
    # prompt = "show system # "

    def __init__(self, base_url, token, net_id, time_format=response_formatter.TIME_FORMAT_MS, region=None):
        super(SystemCommands, self).__init__(base_url, token, net_id, region)
        self.current_region = region
        self.table_formatter = response_formatter.ResponseFormatter(time_format=time_format)
        if region is None:
            self.prompt = 'show system # '
        else:
            self.prompt = '[{0}] show system # '.format(self.current_region)

    def status_api_call(self):
        """
        makes API call v2/nsg/cluster/net/{0}/status and returns the response. Note that
        the server does not 'json-stream' response for this API call
        """
        try:
            response = api.call(self.base_url, 'GET', 'v2/nsg/cluster/net/{0}/status'.format(self.netid),
                                       token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            return response.status_code, json.loads(response.content)

    def nsgql_call(self, query):
        """
        makes API call v2/nsg/cluster/net/{0}/status and returns the response. Note that
        the server does not 'json-stream' response for this API call
        """
        path = "/v2/query/net/{0}/data/".format(self.netid)
        nsgql = {
            'targets': []
        }

        if query:
            nsgql['targets'].append(
                {
                    'nsgql': query,
                    'format': 'table'
                }
            )
        try:
            response = api.call(self.base_url, 'POST', path, data=nsgql, token=self.token, stream=True)
        except Exception as ex:
            return 503, ex
        else:
            return response.status_code, json.loads(response.content)

    def help(self):
        print('Show various system parameters and state variables. Arguments: {0}'.format(self.get_args()))

    def do_filesystem(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'fsFreeSpace', 'fsTotalSpace', 'role', 'cycleNumber', 'processUptime', 'updatedAt'],
                response)

        # status, response = self.nsgql_call(
        #     'SELECT device as server,component,NsgRegion,fsUtil,fsFreeSpace,fsTotalSpace FROM fsFreeSpace '
        #     'WHERE fsUtil NOT NULL AND fsFreeSpace NOT NULL AND fsTotalSpace NOT NULL ORDER BY device')
        # if status != 200 or self.is_error(response):
        #     print('ERROR: {0}'.format(self.get_error(response)))
        # else:
        #     response = response[0]
        #     self.table_formatter.print_result_as_table(response)

    def do_memory(self, arg):
        status, response = self.nsgql_call(
            'SELECT device as server,component,NsgRegion,systemMemFreePercent,systemMemTotal FROM systemMemTotal '
            'WHERE systemMemFreePercent NOT NULL AND systemMemTotal NOT NULL ORDER BY device')
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            response = response[0]
            self.table_formatter.print_result_as_table(response)

    def do_cpu(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'cpuUsage', 'role', 'cycleNumber', 'processUptime', 'updatedAt'],
                response)
        # status, response = self.nsgql_call(
        #     'SELECT device as server,component,NsgRegion,cpuUsage FROM cpuUsage WHERE cpuUsage NOT NULL ORDER BY device')
        # if status != 200 or self.is_error(response):
        #     print('ERROR: {0}'.format(self.get_error(response)))
        # else:
        #     response = response[0]
        #     self.table_formatter.print_result_as_table(response)

    def do_tsdb(self, arg):
        status, response = self.nsgql_call(
            'SELECT device as server,component,NsgRegion,'
            'tsDbVarCount,tsDbErrors,tsDbSaveTime,tsDbSaveLag,tsDbTimeSinceLastSave '
            'FROM tsDbVarCount '
            'WHERE tsDbVarCount NOT NULL AND tsDbErrors NOT NULL AND '
            'tsDbSaveTime NOT NULL AND tsDbSaveLag NOT NULL AND tsDbTimeSinceLastSave  NOT NULL ORDER BY device')
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            response = response[0]
            self.table_formatter.print_result_as_table(response)

    def do_python(self, arg):
        status, response = self.nsgql_call(
            'SELECT device as server,NsgRegion,pythonErrorsRate FROM pythonErrorsRate ORDER BY device')
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            response = response[0]
            self.table_formatter.print_result_as_table(response)

    def do_c3p0(self, arg):
        status, response = self.nsgql_call(
            'SELECT device as server,c3p0NumConnections, c3p0NumBusyConnections, c3p0NumIdleConnections,'
            'c3p0NumFailedCheckouts, c3p0NumFailedIdleTests FROM c3p0NumConnections ORDER BY device')
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            response = response[0]
            self.table_formatter.print_result_as_table(response)

    def do_jvm(self, arg):
        status, response = self.nsgql_call(
            'SELECT device as server,NsgRegion,jvmMemFree,jvmMemMax,jvmMemTotal,jvmMemUsed,GCCountRate,GCTimeRate '
            'FROM jvmMemTotal ORDER BY device')
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            response = response[0]
            self.table_formatter.print_result_as_table(response)

    def do_agent_command_executor(self, arg):
        status, response = self.nsgql_call(
            'SELECT device as server,component,NsgRegion,poolSize,poolQueueSize,activeCount,completedCount '
            'FROM poolSize ORDER BY device')
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            response = response[0]
            self.table_formatter.print_result_as_table(response)

    def do_redis(self, arg):
        status, response = self.nsgql_call(
            'SELECT device as node,RedisRole,redisCommandsRate,redisDbSize,redisUsedMemory,redisMaxMemory,'
            'redisUsedCpuSysRate,redisUsedCpuUserRate,redisConnectedClients,redisCommandsRate '
            'FROM redisDbSize '
            'ORDER BY device')
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            response = response[0]
            self.table_formatter.print_result_as_table(response)

        status, response = self.nsgql_call(
            'SELECT device as server,redisErrorsRate,redisOOMErrorsRate FROM redisErrorsRate ORDER BY device')
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            response = response[0]
            self.table_formatter.print_result_as_table(response)

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
                ['name', 'deviceRepoSize', 'monitoredDevices', 'dataPoolSize', 'numVars',
                 'metadataSize', 'metadataMissCount',
                 'lagTotal', 'cycleNumber', 'processUptime', 'updatedAt'],
                response)

    def do_devices(self, arg):
        status, response = self.status_api_call()
        if status != 200 or self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_cluster_vars(
                ['name', 'deviceRepoSize', 'physicalDevices', 'cachedDevices', 'monitoredDevices',
                 'processUptime', 'updatedAt'],
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
        # print()
        # print('Server name:          {0}'.format(status_json['name']))
        # print('Region:               {0}'.format(status_json['region']))
        # print('Roles:                {0}'.format(','.join(status_json['roles'])))
        # print('Status:               {0}'.format(status_json['serverStatus']))
        # print('zookeeperClientState: {0}'.format(status_json['zookeeperClientState']))
        # print()
        # print('Cluster members:')

        self.print_cluster_vars(
            ['name', 'hostName', 'id', 'role', 'region', 'url', 'processUptime', 'updatedAt'], status_json)

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
            update_member(member, this_server)
            for field in names:
                value = str(member.get(field, ''))
                member[field] = self.table_formatter.transform_value(field, value)

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

    # def is_error(self, response):
    #     return isinstance(response, types.DictionaryType) and response.get('status', '').lower() == 'error'

    # def get_error(self, response):
    #     if isinstance(response, types.ListType):
    #         return self.get_error(response[0])
    #     if isinstance(response, types.UnicodeType) or isinstance(response, types.StringType):
    #         return response
    #     return response.get('error', '')
