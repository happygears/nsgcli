"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import getopt
import json
from pyhocon import ConfigFactory
import sys
from cmd import Cmd

import nsgcli.api
import response_formatter


HTTP_OVER_UNIX_SOCKET_PROTOCOL = 'http+unix://'
STANDARD_UNIX_SOCKET_PATH = HTTP_OVER_UNIX_SOCKET_PROTOCOL + '/opt/netspyglass/var/data/socket/jetty.sock'

TIME_FORMAT_MS = 'ms'
TIME_FORMAT_ISO_UTC = 'iso_utc'
TIME_FORMAT_ISO_LOCAL = 'iso_local'

usage_msg = """
This script executes NsgQL queries provided on command line or interactively

Usage:

    nsgql.py [--socket=abs_path_to_unix_socket] [--base-url=url] (-n|--network)=netid [(-f|--format)=format] 
                [-h|--help] [-a|--token=token] [-U|--utc] [-L|--local] [(-t|--timeout)=timeout_sec] [command]

       --socket:       a path to the unix socket created by the server that can be used to access it 
                       when script runs on the same machine. Usually /opt/netspyglass/home/data/socket/jetty.sock
       --base-url:     Base URL for the NetSpyGlass UI backend server. This includes protocol (http/https),
                       server name or address and port number. Examples: http://localhost:9100 , https://nsg-server:9100
                       Either --base-url or --socket must be provided.
       --network:      NetSpyGlass network id (a number, default: 1). 
       --format:       how to format query result. This can be one of 'list', 'table', 'time_series', 'json'. 
                       Default is 'table'
       --raw:          print data as returned by the server. Specifically, do not try to print data returned for
                       --format=table as an ascii table
       --command:      execute NsgQL queries provided as argument. Multiple NsgQL queries can be separated by ';'
       --token:        API access token string
       --utc:          print values in the column `time` in ISO 8601 format in UTC
       --local:        print values in the column `time` in ISO 8601 format in local timezone
       --timeout:      timeout, seconds
       -h --help:      print this usage summary

    Parameter --base-url is optional. If it is not provided, the script connects to the server using
    Unix socket. This works only if the script runs on the same machine and if the user running the script
    has permissions to read and write to the socket. Usually, this would be used `nw2` or root. 

"""


def usage():
    print(usage_msg)


class InvalidArgsException(Exception):
    pass


class NsgQLCommandLine(Cmd):

    def __init__(self):
        Cmd.__init__(self)
        self.base_url = STANDARD_UNIX_SOCKET_PATH
        # self.server = ''
        # self.port = 9100
        self.netid = 1
        self.format = 'table'
        self.raw = False
        self.access_token = ''
        self.command = ''
        self.nsg_config = ''
        self.time_format = TIME_FORMAT_MS
        self.timeout_sec = 180

    def do_help(self, arg):
        usage()

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
                table_formatter = response_formatter.ResponseFormatter(self.time_format)
                # print(response)
                deserialized = response.json()
                # print(deserialized)
                try:
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
                    print(deserialized)
                except ValueError as e:
                    print('Error: {0}'.format(e))

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

    def parse_args(self, argv):

        try:
            opts, args = getopt.getopt(
                argv,
                's:b:n:f:ha:C:LUt:',
                ['help', 'socket=', 'base-url=', 'network=', 'format=',
                 'raw', 'token=', 'config=', 'local', 'utc', 'timeout='])
        except getopt.GetoptError as ex:
            print('UNKNOWN: Invalid Argument:' + str(ex))
            raise InvalidArgsException

        for opt, arg in opts:
            if opt in ['-h', '--help']:
                usage()
                sys.exit(3)
            elif opt in ('-s', '--socket'):
                if arg[0] != '/':
                    print('Argument of --socket must be an absolute path to the unix socket')
                    sys.exit(1)
                self.base_url = HTTP_OVER_UNIX_SOCKET_PROTOCOL + arg
            elif opt in ('-b', '--base-url'):
                self.base_url = arg
            elif opt in ['-n', '--network']:
                self.netid = int(arg)
            elif opt in ['-f', '--format']:
                self.format = arg
            elif opt in ['-r', '--raw']:
                self.raw = True
            elif opt in ['-a', '--token', '--access']:
                self.access_token = arg
            elif opt in ['-C', '--config']:
                # if path to nsg config file is provided using this parameter, then --token is interpreted as
                # the path to the configuration parameter in this file
                self.nsg_config = arg
            elif opt in ['-U', '--utc']:
                # prints time in ISO format in UTC
                self.time_format = TIME_FORMAT_ISO_UTC
            elif opt in ['-L', '--local']:
                # prints time in ISO format in local time zone
                self.time_format = TIME_FORMAT_ISO_LOCAL
            elif opt in ['-t', '--timeout']:
                self.timeout_sec = int(arg)
            if args:
                self.command = ' '.join(args)

        if self.nsg_config and self.access_token:
            # print('using NSG config {0}, parameter {1}'.format(self.nsg_config, self.access_token))
            conf = ConfigFactory.parse_file(self.nsg_config)
            self.access_token = conf.get_string(self.access_token)

    def summary(self):
        print()
        if self.nsg_config and self.access_token:
            print('using NSG config {0}, parameter {1}'.format(self.nsg_config, self.access_token))
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


def main():
    script = NsgQLCommandLine()
    script.parse_args(sys.argv[1:])
    try:
        if script.command:
            print('Command={0}'.format(script.command))
            script.onecmd(script.command)
        else:
            script.summary()
            script.prompt = script.base_url + ' > '
            script.cmdloop()
    except KeyboardInterrupt as e:
        sys.exit(0)
