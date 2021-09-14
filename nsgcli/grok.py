"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2021 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import getopt
import json
import select
import sys
import os

import nsgcli.api
import nsgcli.sub_command
import nsgcli.system
import nsgcli.response_formatter

HELP = """
Parse text line with grok patterns
        Parse text line with grok patterns

        parse [--text <text>] [--pattern <pattern>]

        Parameters:
            --text val Optional. Text to be parsed, read stdin if not specified
            --pattern val Optional. Grok pattern to be applied to input text, use only pre-defined patterns if not specified.

        Examples:

            parse --text "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host
            '79.174.187.54'"

            parse --text "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user
            'root' from host 1.1.1.1" --pattern "Login failed for user '%{WORD:login_name}'"
            
            parse --pattern "Login failed for user '%{WORD:login_name}'" <<< 
            "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host 1.1.1.1"            
"""


class GrokCommands(nsgcli.sub_command.SubCommand, object):
    def __init__(self, base_url, token, net_id):
        super(GrokCommands, self).__init__(base_url, token, net_id)
        self.prompt = 'grok # '

    @staticmethod
    def help():
        print(HELP)

    ##########################################################################################
    def do_parse(self, _):
        """
        Parse text line with grok patterns

        parse [--text <text>] [--pattern <pattern>]

        Parameters:
            --text val Optional. Text to be parsed, read stdin if not specified
            --pattern val Optional. Grok pattern to be applied to input text, use only pre-defined patterns if not specified.

        Examples:

            parse --text "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host
            '79.174.187.54'"

            parse --text "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user
            'root' from host 1.1.1.1" --pattern "Login failed for user '%{WORD:login_name}'"

            parse --pattern "Login failed for user '%{WORD:login_name}'" <<<
            "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host 1.1.1.1"
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
            self.read_stdin(pattern)
        else:
            self.call_grok_api(txt, pattern)

    def call_grok_api(self, txt, pattern):
        request = 'v2/grok/net/{0}/parser'.format(self.netid)
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

    def read_stdin(self, pattern):
        in_buffer = ""
        while True:
            select.select([sys.stdin.fileno()], [], [])
            read = os.read(sys.stdin.fileno(), 512)

            # empty read: EOF
            if len(read) == 0:
                # in_buffer might not be empty
                if len(in_buffer) > 0:
                    self.call_grok_api(in_buffer, pattern)
                break

            # find newlines
            parts = read.split("\n")
            in_buffer += parts.pop(0)

            while len(parts) > 0:
                self.call_grok_api(in_buffer, pattern)
                in_buffer = parts.pop(0)


class InvalidArgsException(Exception):
    pass
