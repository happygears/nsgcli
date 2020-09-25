"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import click

from typing import List
from nsgcli.api import API


@click.group(name='exec')
@click.pass_context
def execute(_: click.Context) -> None:
    """
    Call agents to execute various commands
    """
    pass


# fping command allows fping options as arguments
@execute.command(context_settings={"ignore_unknown_options": True})
@click.pass_context
@click.argument('address', type=click.STRING)
@click.argument('args', nargs=-1)
def fping(ctx: click.Context, address: str, args: List[str]) -> None:
    """
    Runs fping to give address on an agent. If region has been selected prior to running this command,
    uses only agents in the region. Otherwise tries all agents in all regions.

    fping <address> [fping args]

    fping exit codes:

    Exit status is 0 if all the hosts are reachable,
        1 if some hosts were unreachable,
        2 if any IP addresses were not found,
        3 for invalid command line arguments, and
        4 for a system call failure.
    """
    api: API = ctx.obj['api']
    response = api.fping(address, args)
    with response:
        for acr in api.transform_remote_command_response_stream(response):
            # fping_status = parse_fping_status(acr)
            api.print_agent_response(acr)


@execute.command()
@click.pass_context
@click.argument('address', type=click.STRING)
def ping(ctx: click.Context, address: str) -> None:
    api: API = ctx.obj['api']
    api.common_command('ping', [address])


@execute.command()
@click.pass_context
@click.argument('address', type=click.STRING)
def traceroute(ctx: click.Context, address: str) -> None:
    api: API = ctx.obj['api']
    api.common_command('traceroute', [address])


# TODO(colin): for some reason agent is reporting exitStatus 0 from fping. So we aren't
# doing this; just report the output lines we get.
def parse_fping_status(acr):
    print('arc=', acr)
    ec = acr['exitStatus']
    if ec == 0:
        status = 'ok'
    elif ec == 1:
        status = 'some hosts were unreachable'
    elif ec == 2:
        status = 'any IP addresses were not found'
    elif ec == 3:
        status = 'invalid command line arguments'
    elif ec == 4:
        status = 'system call failure'
    elif ec == -1:
        status = 'could not find and execute the command'
    elif 'error' in acr:
        status = acr['error']
    else:
        status = 'unknown error'
    return status
