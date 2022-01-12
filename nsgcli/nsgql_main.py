"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import json
from cmd import Cmd

import nsgcli.api
import response_formatter


TIME_FORMAT_MS = 'ms'
TIME_FORMAT_ISO_UTC = 'iso_utc'
TIME_FORMAT_ISO_LOCAL = 'iso_local'


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

    def do_q(self, arg):
        """Quits the program."""
        print('Quitting.')
        raise SystemExit

    def do_quit(self, arg):
        """Quits the program."""
        print('Quitting.')
        raise SystemExit

    def do_select(self, arg):
        self.execute('SELECT {0}'.format(arg))

    def do_SELECT(self, arg):
        self.execute('SELECT {0}'.format(arg))

    def do_show(self, arg):
        self.execute('SHOW {0}'.format(arg))

    def do_SHOW(self, arg):
        self.execute('SHOW {0}'.format(arg))

    def do_describe(self, arg):
        self.execute('DESCRIBE {0}'.format(arg))

    def do_DESCRIBE(self, arg):
        self.execute('DESCRIBE {0}'.format(arg))

    def execute(self, arg):
        with self.post_data(arg.split(';')) as response:
            status = response.status_code
            if status != 200:
                for line in response.iter_lines():
                    print('ERROR: {0}'.format(json.loads(line)))
                    return None
            else:
                table_formatter = response_formatter.ResponseFormatter(time_format=self.time_format)
                if self.raw:
                    print(response.content)
                    return None
                try:
                    deserialized = response.json()
                except Exception, e:
                    print('ERROR: {0}, response={1}'.format(e, response.content))
                    return None
                # print(deserialized)
                # print(type(line))
                # print(line)
                if self.format == 'table':
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

        :param queries  -- a lisrt of NsgQL queries
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

        return nsgcli.api.call(self.base_url, 'POST', path,
                               data=nsgql, token=self.access_token, stream=True, timeout=self.timeout_sec)
