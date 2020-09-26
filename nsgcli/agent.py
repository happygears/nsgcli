"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import click


from typing import List
from nsgcli.api import API

AGENT_LOG_DIR = '/opt/nsg-agent/var/logs'


@click.group()
@click.pass_context
@click.argument('target_agent', type=click.STRING)
def agent(ctx: click.Context, target_agent):
    """
    Call agents to execute various commands.

    log:    retrieve agent's log file
            this command assumes standard directory structure on the agent where logs are
            located in /opt/nsg-agent/var/logs

            Example:

                agent <agent_name> log [-NN] <log_file_name>


    tail: tail a file on an agent.

            Example:

                agent <agent_name> tail -100 /opt/nsg-agent/home/logs/agent.log


    probe_snmp: discover working snmp configuration for the device

            Example:

                agent <agent_name> probe_snmp <device_address> <snmp_conf_name_1> <snmp_conf_name_2> ...


    find: Find an agent responsible for polling given target (IP address). Use 'all' in place of the agent name.

            Example:

                agent all find 1.2.3.4

    restart: restart the agent

            Example: agent <agent_name> restart

    snmp:    run snmp get or snmp walk command

            Arguments:

                agent <agent_name> snmpget <address> oid
                agent <agent_name> snmpwalk <address> oid

            Example:

                agent <agent_name> snmpget  10.0.0.1 .1.3.6.1.2.1.1.2.0

    set_property:    set (or query) value of JVM system property

            Arguments:

                agent <agent_name> set_property foo
                agent <agent_name> set_property foo bar

    measurements:    query current values of agent monitoring variables

            Example:

                agent <agent_name> measurements

    """
    ctx.obj['target_agent'] = target_agent


@agent.command()
@click.pass_context
@click.argument('address')
@click.argument('oid')
@click.argument('timeout', required=False, type=click.INT, default=2000)
def snmpget(ctx: click.Context, address: str, oid: str, timeout: int) -> None:
    """
    Execute snmp GET command using agents in the currently selected region

    snmp_get <address> oid [timeout_ms]
    """
    snmp_command(ctx, 'snmpget', address, oid, timeout)


@agent.command()
@click.pass_context
@click.argument('address')
@click.argument('oid')
@click.argument('timeout', required=False, type=click.INT, default=2000)
def snmpwalk(ctx: click.Context, address: str, oid: str, timeout: int) -> None:
    """
    Execute snmp GET command using agents in the currently selected region

    snmp_get <address> oid [timeout_ms]
    """
    snmp_command(ctx, 'snmpwalk', address, oid, timeout)


# We need to "ignore unknown options" here because the tail length is traditionally
# specified like -100, which looks like an option, not an argument.
@agent.command(context_settings={"ignore_unknown_options": True})
@click.pass_context
@click.argument('lines', type=click.INT)
@click.argument('filename', type=click.STRING)
def tail(ctx: click.Context, lines, filename):
    """
    tail a file on an agent.

    Example: agent agent_name tail -100 /opt/nsg-agent/home/logs/agent.log
    """
    api: API = ctx.obj['api']
    response = api.tail(ctx.obj['target_agent'], lines, filename)
    with response:
        for acr in api.transform_remote_command_response_stream(response):
            print_response(acr)


# We need to "ignore unknown options" here because the tail length is traditionally
# specified like -100, which looks like an option, not an argument.
@agent.command(context_settings={"ignore_unknown_options": True})
@click.pass_context
@click.argument('lines', type=click.INT)
@click.argument('logfile', type=click.STRING)
def log(ctx: click.Context, lines, logfile):
    """
    retrieve agent's log file

    Example: agent agent_name log [-NN] log_file_name

    this command assumes standard directory structure on the agent where logs are
    located in /opt/nsg-agent/var/logs
    """
    tail(ctx, lines, AGENT_LOG_DIR + '/' + logfile)


@agent.command()
@click.pass_context
@click.argument('address')
def find(ctx: click.Context, address):
    """
    Find an agent responsible for polling given target (IP address). This command
    does not require agent name argument.

    Example: agent find 1.2.3.4
    """
    api: API = ctx.obj['api']
    api.common_command('find_agent', [address])


@agent.command()
@click.pass_context
def restart(ctx: click.Context):
    """
    Restart agent with given name

    Example:  agent agent_name restart
    """
    api: API = ctx.obj['api']
    api.common_command('restart_agent', [])


@agent.command()
@click.pass_context
@click.argument('key', required=False)
@click.argument('value', required=False)
def set_property(ctx: click.Context, key, value) -> None:
    """
    Contacts given agent (or all), and sets the system property key to value.
    (If value is omitted, the current value of the property is returned.)

    agent <agent_name> set_property key [value]
    """
    api: API = ctx.obj['api']
    args = [ctx.obj['target_agent']]
    if key:
        args.append(key)
    if value:
        args.append(value)
    api.common_command('set_property', args)


@agent.command()
@click.pass_context
def measurements(ctx: click.Context) -> None:
    """
    Contacts agent (or all), and retrieves current values of its monitoring
    variables.

    agent <agent_name> measurements
    """
    api: API = ctx.obj['api']
    api.common_command('measurements', [ctx.obj['target_agent']])


@agent.command()
@click.pass_context
@click.argument('device_id')
def bulk_request(ctx: click.Context, device_id) -> None:
    """
    Contacts agent (or all), and retrieves current bulk request
    for given device ID.

    agent <agent_name> bulk_request <device_ID>
    """
    api: API = ctx.obj['api']
    api.common_command('bulk_request', [ctx.obj['target_agent'], device_id])


@agent.command()
@click.pass_context
@click.argument('address')
@click.argument('polling_config', nargs=-1)
def probe_snmp(ctx: click.Context, address: str, polling_config: List[str]) -> None:
    """
    try to discover working snmp configuration for the device

    Example: agent agent_name probe_snmp <device_address> <snmp_conf_name_1> <snmp_conf_name_2> ...
    """
    api: API = ctx.obj['api']
    args = [ctx.obj['target_agent'], address]
    args.extend(polling_config)
    api.common_command('discover-snmp-access', args)


def snmp_command(ctx: click.Context, command: str, address: str, oid: str, timeout: int):
    api: API = ctx.obj['api']
    # This call returns list of AgentCommandResponse objects in json format
    response = api.snmp(ctx.obj['target_agent'], command, address, oid, timeout)
    with response:
        for acr in api.transform_remote_command_response_stream(response):
            print_response(acr)


def print_response(acr):
    for line in acr['response']:
        print('{0} | {1}'.format(acr['agent'], line))
