"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import click
import json
import os

from cmd import Cmd

from typing import List

from nsgcli import response_formatter
from nsgcli.version import __version__
from nsgcli.api import API

TIME_FORMAT_MS = 'ms'
TIME_FORMAT_ISO_UTC = 'iso_utc'
TIME_FORMAT_ISO_LOCAL = 'iso_local'


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


class NsgQLCommandLine(Cmd):

    def __init__(self, base_url=None, token=None, netid=1, output_format='table', raw=False,
                 time_format=TIME_FORMAT_MS, timeout_set=180):
        Cmd.__init__(self)
        self.base_url = base_url
        self.access_token = token
        self.netid = netid
        self.format = output_format
        self.raw = raw
        self.time_format = time_format
        self.timeout_sec = timeout_set

    @staticmethod
    def do_q():
        """Quits the program."""
        print('Quitting.')
        raise SystemExit

    @staticmethod
    def do_quit():
        """Quits the program."""
        print('Quitting.')
        raise SystemExit

    def do_select(self, arg):
        self.execute('SELECT {0}'.format(arg))

    def do_show(self, arg):
        self.execute('SHOW {0}'.format(arg))

    def do_describe(self, arg):
        self.execute('DESCRIBE {0}'.format(arg))

    def execute(self, arg):
        with self.post_data(arg.split(';')) as response:
            status = response.status_code
            if status != 200:
                for line in response.iter_lines():
                    print('ERROR: {0}'.format(json.loads(line)))
                    return None
            else:
                table_formatter = response_formatter.ResponseFormatter(self.time_format)
                # print(response)
                deserialized = response.json()
                # print(deserialized)
                # print(type(line))
                # print(line)
                if not self.raw and self.format == 'table':
                    for resp in deserialized:
                        error = self.is_error(resp)
                        if error:
                            print('Server error: {0}'.format(error))
                            continue
                        table_formatter.print_result_as_table(resp)
                    return
                print(json.dumps(deserialized))
                # print(deserialized)

    def is_error(self, response):
        if isinstance(response, dict) and 'error' in response:
            error = response.get('error', '')
            return error
        if isinstance(response, list):
            return self.is_error(response[0])
        if isinstance(response, str):
            resp_obj = json.loads(response)
            return self.is_error(resp_obj)
        return None

    def summary(self):
        print()
        print('Base url: {0}'.format(self.base_url))
        print('To exit, enter "quit" or "q" at the prompt')

    def post_data(self, queries):
        """
        Make NetSpyGlass JSON API call to execute query

        :param queries  -- a list of NsgQL queries
        """
        path = "/v2/query/net/{0}/data/".format(self.netid)
        # if self.access_token:
        #     path += '?access_token=' + self.access_token

        nsgql = {
            'targets': []
        }

        for query in queries:
            if query:
                nsgql['targets'].append(
                    {
                        'nsgql': query,
                        'format': self.format
                    }
                )

        return api.call(self.base_url, 'POST', path,
                        data=nsgql, token=self.access_token, stream=True, timeout=self.timeout_sec)
