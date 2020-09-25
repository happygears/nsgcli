"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import collections
import click
from functools import reduce
from nsgcli.api import API


@click.group()
@click.pass_context
def system(_: click.Context) -> None:
    """
    Root of a family of system inspection commands
    """
    pass


@system.command()
@click.pass_context
def filesystem(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    print_cluster_vars(
        api.response_formatter,
        ['name', 'fsFreeSpace', 'fsTotalSpace', 'role', 'cycleNumber', 'processUptime', 'updatedAt'],
        api.get_cluster_status())


@system.command()
@click.pass_context
def lag(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    print_cluster_vars(
        api.response_formatter,
        ['name', 'id', 'role', 'region',
         'lagAgentAllReceived', 'lagAgentAllSent', 'lagServerAllReceived', 'lagTotal',
         'processUptime', 'updatedAt'],
        api.get_cluster_status())


@system.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    print_cluster_vars(
        api.response_formatter,
        ['name', 'hostName', 'hostAddress', 'pid', 'id', 'role', 'region', 'tier',
         'status', 'processUptime', 'updatedAt'],
        api.get_cluster_status())


@system.command(name='sum')
@click.pass_context
def summary(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    print_cluster_vars(
        api.response_formatter,
        ['name', 'deviceRepoSize', 'monitoredDevices', 'dataPoolSize', 'numVars',
         'metadataSize', 'metadataMissCount',
         'lagTotal', 'cycleNumber', 'processUptime', 'updatedAt'],
        api.get_cluster_status())


@system.command()
@click.pass_context
def devices(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    print_cluster_vars(
        api.response_formatter,
        ['name', 'deviceRepoSize', 'physicalDevices', 'cachedDevices', 'monitoredDevices',
         'processUptime', 'updatedAt'],
        api.get_cluster_status())


@system.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    print_cluster_vars(
        api.response_formatter,
        ['name', 'nsgVersion', 'revision', 'processUptime', 'updatedAt'],
        api.get_cluster_status())


@system.command()
@click.pass_context
def cpu(ctx: click.Context):
    api: API = ctx.obj['api']
    print_cluster_vars(
        api.response_formatter,
        ['name', 'cpuUsage', 'role', 'cycleNumber', 'processUptime', 'updatedAt'],
        api.get_cluster_status())


@system.command()
@click.pass_context
def memory(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    response = api.nsgql_call(
            'SELECT device as server,component,NsgRegion,systemMemFreePercent,systemMemTotal FROM systemMemTotal '
            'WHERE systemMemFreePercent NOT NULL AND systemMemTotal NOT NULL ORDER BY device')
    api.response_formatter.print_result_as_table(response)


@system.command()
@click.pass_context
def jvm(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    response = api.nsgql_call(
        'SELECT device as server,NsgRegion,jvmMemFree,jvmMemMax,jvmMemTotal,jvmMemUsed,GCCountRate,GCTimeRate '
        'FROM jvmMemTotal ORDER BY device')
    api.response_formatter.print_result_as_table(response)


@system.command()
@click.pass_context
def python(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    response = api.nsgql_call(
        'SELECT device as server,NsgRegion,pythonErrorsRate FROM pythonErrorsRate ORDER BY device')
    api.response_formatter.print_result_as_table(response)


@system.command()
@click.pass_context
def tsdb(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    response = api.nsgql_call(
        'SELECT device as server,component,NsgRegion,'
        'tsDbVarCount,tsDbErrors,tsDbSaveTime,tsDbSaveLag,tsDbTimeSinceLastSave '
        'FROM tsDbVarCount '
        'WHERE tsDbVarCount NOT NULL AND tsDbErrors NOT NULL AND '
        'tsDbSaveTime NOT NULL AND tsDbSaveLag NOT NULL AND tsDbTimeSinceLastSave  NOT NULL ORDER BY device')
    api.response_formatter.print_result_as_table(response)


@system.command()
@click.pass_context
def c3p0(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    response = api.nsgql_call(
        'SELECT device as server,c3p0NumConnections, c3p0NumBusyConnections, c3p0NumIdleConnections,'
        'c3p0NumFailedCheckouts, c3p0NumFailedIdleTests FROM c3p0NumConnections ORDER BY device')
    api.response_formatter.print_result_as_table(response)


@system.command()
@click.pass_context
def redis(ctx: click.Context):
    api: API = ctx.obj['api']
    response = api.nsgql_call(
        'SELECT device as node,RedisRole,redisCommandsRate,redisDbSize,redisUsedMemory,redisMaxMemory,'
        'redisUsedCpuSysRate,redisUsedCpuUserRate,redisConnectedClients,redisCommandsRate '
        'FROM redisDbSize '
        'ORDER BY device')
    api.response_formatter.print_result_as_table(response)

    response = api.nsgql_call(
        'SELECT device as server,redisErrorsRate,redisOOMErrorsRate FROM redisErrorsRate ORDER BY device')
    api.response_formatter.print_result_as_table(response)


@system.command()
@click.pass_context
def agent_command_executor(ctx: click.Context) -> None:
    api: API = ctx.obj['api']
    response = api.nsgql_call(
        'SELECT device as server,component,NsgRegion,poolSize,poolQueueSize,activeCount,completedCount '
        'FROM poolSize ORDER BY device')
    api.response_formatter.print_result_as_table(response)


def print_cluster_vars(formatter, names, cluster_status):
    field_width = collections.OrderedDict()
    field_names = {}
    for n in names:
        field_width[n] = 0
        field_names[n] = n

    this_server = cluster_status['name']

    # sort members once, and do it before I mangle their names
    sorted_members = sorted(cluster_status['members'], key=member_compare_key)
    for member in sorted_members:
        update_member(member, this_server)
        for field in names:
            value = str(member.get(field, ''))
            member[field] = formatter.transform_value(field, value)

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

    print(format_str.format(m=field_names))
    print('-' * total_width)
    for member in sorted_members:
        print(format_str.format(m=member))
    print('-' * total_width)


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


def member_compare_key(m):
    """
    Compare cluster member dictionaries by their role. This can be used to put primary and secondary
    servers at the top of the list
    """
    return score_roles(m['role']), m['name']


def transform_roles(roles):
    """
    Server sends roles as a comma-separated string, e.g. "primary,monitor"
    """
    return ','.join([ROLE_MAP.get(role, role) for role in sorted(roles.split(',')) if role != 'primary'])


def update_member(member, this_server):
    roles = transform_roles(member['role'])
    member['role'] = roles
    name = member['name']
    if this_server == name:
        member['name'] = '*' + name
    else:
        member['name'] = ' ' + name



