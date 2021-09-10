"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2021 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import getopt
import json
import sys

import nsgcli.api
import nsgcli.sub_command
import nsgcli.system
import nsgcli.response_formatter

HELP = """
Parse text line with grok patterns pre-defined within NSG server and one custom grok pattern

parse --text <text> [--pattern <pattern>]

Examples:

    parse --text "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host
    '1.1.1.1'"

    parse --text "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host 
    1.1.1.1" --pattern "Login failed for user '%{WORD:login_name}'"

"""


class GrokCommands(nsgcli.sub_command.SubCommand, object):
    def __init__(self, base_url, token, net_id, time_format=nsgcli.response_formatter.TIME_FORMAT_MS, region=None):
        super(GrokCommands, self).__init__(base_url, token, net_id)
        self.system_commands = nsgcli.system.SystemCommands(
            self.base_url, self.token, self.netid, time_format=time_format, region=region)
        self.current_region = region
        if region is None:
            self.prompt = 'grok # '
        else:
            self.prompt = 'grok [' + self.current_region + '] # '

    ##########################################################################################
    def do_parse(self, _):
        """
        Parse text line with grok patterns pre-defined within NSG server and one custom grok pattern

        parse --text <text> [--pattern <pattern>]

        Examples:

            parse --text "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host
            '79.174.187.54'"

            parse --text "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user
            'root' from host 1.1.1.1" --pattern "Login failed for user '%{WORD:login_name}'"
        """
        try:
            opts, args = getopt.getopt(sys.argv[3:],
                                       't:p:',
                                       ['text=', 'pattern='])
        except getopt.GetoptError as ex:
            print('UNKNOWN: Invalid Argument:' + str(ex))
            raise InvalidArgsException

        txt = None
        pattern = None
        for opt, arg in opts:
            if opt in ['-t', '--text']:
                txt = arg
            elif opt in ('-p', '--pattern'):
                pattern = arg

        if not txt:
            print('--text parameter is mandatory')
            raise InvalidArgsException

        request = 'v2/grok/parser'
        try:
            data = {'text': txt}
            if pattern:
                data['pattern'] = pattern

            response = nsgcli.api.call(self.base_url, 'POST', request, data, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            status = response.status_code
            if status != 200:
                print("Failed with error code: {}".format(status))
                if status < 500:
                    print(self.get_error(json.loads(response.content)))
                exit(1)
            else:
                print(json.dumps(json.loads(response.content), indent=4))

    @staticmethod
    def help():
        print(HELP)


class InvalidArgsException(Exception):
    pass
