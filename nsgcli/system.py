"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import collections
from functools import cmp_to_key
from functools import reduce

from . import api
from . import response_formatter
from . import sub_command
from tabulate import tabulate

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


def cmp(a, b):
    return (a > b) - (a < b)


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
        return api.call(self.base_url, 'GET', 'v2/nsg/cluster/net/{0}/status'.format(self.netid),
                                               token=self.token, response_format='json')

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

        return api.call(self.base_url, 'POST', path, data=nsgql, token=self.token, stream=True, response_format='json')

    def help(self):
        print('Show various system parameters and state variables. Arguments: {0}'.format(self.get_args()))

    def do_filesystem(self, arg):
        response, error = self.status_api_call()
        if error is None:
            self.print_cluster_vars(
                ['name', 'fsFreeSpace', 'fsTotalSpace', 'role', 'cycleNumber', 'processUptime', 'updatedAt'],
                response)

    def do_agent_command_executor(self, arg):
        response, error = self.nsgql_call(
            'SELECT device as server,component,NsgRegion,poolSize,poolQueueSize,activeCount,completedCount '
            'FROM poolSize ORDER BY device')
        if error is None:
            response = response[0]
            self.table_formatter.print_result_as_table(response)

    def do_version(self, arg):
        response, error = self.status_api_call()
        if error is None:
            self.print_cluster_vars(
                ['name', 'nsgVersion', 'revision', 'processUptime', 'updatedAt'],
                response)

    def do_status(self, arg):
        response, error = self.status_api_call()
        if error is None:
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
        field_names = {}
        for n in names:
            field_names[n] = n

        this_server = status_json['name']

        # sort members once, and do it before I mangle their names
        sorted_members = sorted(status_json['members'], key=cmp_to_key(compare_members))
        for member in sorted_members:
            update_member(member, this_server)
            for field in names:
                value = str(member.get(field, ''))
                member[field] = self.table_formatter.transform_value(field, value)

        row_list = []
        for member in sorted_members:
            column_values = [member[n] for n in names]
            row_list.append(column_values)

        print(tabulate(row_list, names, tablefmt='fancy_outline'))