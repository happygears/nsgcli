"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import click
from nsgcli.api import API


@click.group()
@click.pass_context
def search(_: click.Context) -> None:
    pass


@search.command()
@click.pass_context
@click.argument('match')
def device(ctx: click.Context, match):
    """
    search device match

    where match is name, address, serial number or box description
    """
    api: API = ctx.obj['api']
    query = f'''SELECT DISTINCT id,name,address,Vendor,SerialNumber,boxDescr FROM devices 
                WHERE (name REGEXP "^{match}.*$"
                OR address = "{match}"
                OR SerialNumber = "{match}"
                OR boxDescr REGEXP ".*{match}.*")
                AND Role NOT IN ("Cluster", "SimulatedNode")'''
    api.response_formatter.print_result_as_table(api.nsgql_query(query))