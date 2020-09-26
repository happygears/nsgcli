"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import click
import os
import sys

from nsgcli import index, agent, show, search, execute
from nsgcli.api import API
from nsgcli.response_formatter import TIME_FORMAT_ISO_LOCAL, TIME_FORMAT_ISO_UTC


@click.group(context_settings={})
@click.pass_context
@click.option('--base-url',
              help="http://HOST:PORT of your NSG cluster API endpoint (defaults to $NSG_SERVICE_URL)")
@click.option('--token', help="API token for access to NSG cluster")
@click.option('-L', '--local', 'time_format', flag_value=TIME_FORMAT_ISO_LOCAL, default=True,
              help="Report timestamps in local timezone")
@click.option('-U', '--utc', 'time_format', flag_value=TIME_FORMAT_ISO_UTC,
              help="Report timestamps in UTC")
@click.option('--region', help="Select region for agent commands")
@click.option('--network', default='1', help="Network ID. 1 is usually correct")
def cli(ctx, base_url, token, time_format, region, network):
    if not base_url:
        base_url = os.getenv('NSG_SERVICE_URL')
    if not base_url:
        print('Must specify --base-url or set $NSG_SERVICE_URL', sys.stderr)
        sys.exit(1)

    base_url = base_url.rstrip('/ ')
    ctx.obj = {'api': API(base_url=base_url, token=token, network=network, time_format=time_format, region=region)}


cli.add_command(show.show)
cli.add_command(agent.agent)
cli.add_command(index.index)
cli.add_command(search.search)
cli.add_command(execute.execute)


@cli.command()
@click.pass_context
@click.argument('thing', type=click.Choice(['config', 'devices', 'clusters']))
def reload(ctx: click.Context, thing: click.STRING):
    """
    Send a request to NSG to reload something
    """
    api: API = ctx.obj['api']
    api.print_response(api.reload(thing))


@cli.command()
@click.pass_context
def ping(ctx: click.Context):
    """
    Test server status with '/ping' API call

    "ping" NetSpyGlass server this cli client connects to. This returns "ok" if the server is up and running
    """
    api: API = ctx.obj['api']
    print(api.ping_server().content.decode(), end='')


@cli.command()
@click.pass_context
@click.argument('op', type=click.Choice(['clear', 'refresh']))
def cache(ctx: click.Context, op: str) -> None:
    """
    Operations with cache.
    """
    api: API = ctx.obj['api']
    api.print_response(api.cache(op))


@cli.command()
@click.pass_context
@click.argument('thing', type=click.Choice(['views', 'variables', 'maps', 'tags']))
def make(ctx: click.Context, thing: str) -> None:
    """
    Make things.
    """
    api: API = ctx.obj['api']
    api.print_response(api.make(thing))


@cli.command()
@click.pass_context
@click.argument('op', type=click.Choice(['start']))
def discovery(ctx: click.Context, op: str) -> None:
    """
    Discover.
    """
    api: API = ctx.obj['api']
    api.print_response(api.discover(op))


@cli.command()
@click.pass_context
@click.argument('op', type=click.Choice(['reset']))
def hud(ctx: click.Context, op: str) -> None:
    """
    Operations with HUD in UI.
    """
    api: API = ctx.obj['api']
    api.print_response(api.hud(op))


@cli.command()
@click.pass_context
@click.argument('op', type=click.Choice(['rebuild']))
def nsgql(ctx: click.Context, op: str) -> None:
    """
    Operations with NsgQL schema.
    """
    api: API = ctx.obj['api']
    api.print_response(api.nsgql_schema(op))


@cli.command()
@click.pass_context
@click.argument('what', type=click.Choice(['tsdb', 'monitor']))
def restart(ctx: click.Context, what: str) -> None:
    """
    restart various components:

    restart tsdb         - restarts tsdb connector
    restart monitor      - restarts monitor (the component that communicates with NetSpyGlass agents)

    TODO: add 'restart server <server_name>'
    """
    api: API = ctx.obj['api']
    api.print_response(api.restart(what))


@cli.command()
@click.pass_context
@click.argument('retention', type=click.FLOAT)
def expire(ctx: click.Context, retention: float) -> None:
    """
    Force expiration of variables in the data pool of all servers. Syntax:

    expire retention_hrs

    Retention is in hours and can be fractional (e.g.  "expire 0.1" for 0.1 hours)
    """
    api: API = ctx.obj['api']
    api.print_response(api.expire(retention))


@cli.command()
@click.pass_context
@click.argument('level', type=click.INT)
@click.argument('arg', type=click.STRING, required=False)
@click.argument('time_min', type=click.INT, required=False, default=10)
def debug(ctx: click.Context, level: int, arg: str, time_min: int) -> None:
    """
    Set debug level and optional argument with optional timeout:

    debug level [arg [time_min]]

    If only one argument is given, it is assumed to be the debug level and it will be set for 10 min.
    If three arguments are given, they are interpreted as debug level, debug argument and the time in
    minutes.

    Debug level and argument are passed to all servers in the cluster via inter-process message bus.
    Timeout is in minutes. Debug level reverts to its current value and argument
    is erased after timeout. The default timeout is 10 min. If timeout=0, then debug
    level is set indefinitely. Argument can not contain spaces.

    Recognized debug levels: (enter the number as argument 'level', values can be combined with bitwise OR):

    DEBUG_NSGQL = 1
    DEBUG_DATA_POOL = 2
    DEBUG_AGENT_RESPONSES = 3
    DEBUG_COMPUTE = 4
    DEBUG_TSDB = 5
    DEBUG_STATUS = 6
    DEBUG_ZOOKEEPER = 7
    DEBUG_CACHES = 8
    DEBUG_SOCKET_IO = 9
    DEBUG_GRAPH = 10
    DEBUG_VARS = 11
    DEBUG_DATA_PUSH = 12
    DEBUG_SYSTEM_EVENTS_AND_HUD = 13
    DEBUG_INDEXER = 14
    DEBUG_MVARS = 15
    DEBUG_REDIS_EXECUTOR = 16
    DEBUG_AGENT_RESPONSE_CYCLE = 17
    DEBUG_DEVICES = 18
    DEBUG_DISCOVERY = 19
    DEBUG_AGENT_COMMAND_EXECUTION = 20
    DEBUG_STATE_MANAGER = 21
    DEBUG_TAGS = 22
    DEBUG_ALERTS = 23
    DEBUG_REPORTS = 24
    DEBUG_CLUSTERS = 25
    DEBUG_SERVER_LIFE_CYCLE = 26
    DEBUG_SELF_MONITORING = 27
    DEBUG_AGGREGATION = 28
    DEBUG_THRESHOLDS = 29
    DEBUG_WEB_SERVER_SESSIONS = 30
    DEBUG_WEBDAV = 31
    DEBUG_VIEWS = 32
    """
    api: API = ctx.obj['api']
    api.print_response(api.debug(level, arg, time_min))
