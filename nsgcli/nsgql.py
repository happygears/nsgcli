"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import click
import json
import os

from typing import List
from nsgcli.api import API
from nsgcli.response_formatter import TIME_FORMAT_ISO_UTC, TIME_FORMAT_ISO_LOCAL


@click.command()
@click.option('--base-url',
              help="http://HOST:PORT of your NSG cluster API endpoint (defaults to $NSG_SERVICE_URL)",
              default=os.getenv('NSG_SERVICE_URL'))
@click.option('--format', 'format_', type=click.Choice(['list', 'table', 'time_series', 'json']), default='table')
@click.option('--raw')
@click.option('--token', help="API token for access to NSG cluster")
@click.option('--timeout', type=click.INT, default=180)
@click.option('-L', '--local', 'time_format', flag_value=TIME_FORMAT_ISO_LOCAL, default=True,
              help="Report timestamps in local timezone")
@click.option('-U', '--utc', 'time_format', flag_value=TIME_FORMAT_ISO_UTC,
              help="Report timestamps in UTC")
@click.option('--netid', default=1, help="Network ID. 1 is usually correct", type=click.INT)
@click.argument('query', nargs=-1)
def nsgql(base_url: str, format_: str, raw: bool, token: str, timeout: int, time_format: str, netid: int, query: List[str]):
    api = API(
        base_url=base_url.rstrip('/ '),
        token=token,
        time_format=time_format,
        netid=netid
    )
    # I don't love the quoting semantics here, because if a string in the query
    # has a ; in it, the split will ruin the query, but this is the way it
    # used to work.  One way of deprecating this would be to fold nsgql
    # queries into nsgcli, rename nsgcli to query, and have a 'query' subcommand
    # of nsg that would have more solid quoting behavior.
    execute(api, ' '.join(query).split(';'), raw, format_, timeout)


def execute(api: API, queries: List[str], raw=False, fmt='table', timeout=180):
    table_formatter = api.response_formatter
    results = api.nsgql_multiquery(queries, fmt, timeout)
    print('rs=', results)

    if not raw and fmt == 'table':
        for result in results:
            if 'error' in result:
                print('Server error: {0}'.format(result['error']))
                continue
            table_formatter.print_result_as_table(result)
        return
    print(json.dumps(results))
