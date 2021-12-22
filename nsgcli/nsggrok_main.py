"""
This module implements Cmd commands that parses text input with Grok using grok-api service

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import os
import sys
import select
import json
from cmd import Cmd

import nsgcli.api


class NsgGrokCommandLine(Cmd):

    def __init__(self, base_url=None, token=None, netid=1, pattern=None, timeout_set=180):
        Cmd.__init__(self)
        self.base_url = base_url
        self.token = token
        self.netid = netid
        self.timeout_sec = timeout_set
        self.pattern = pattern

    def do_q(self, _):
        """Quits the program."""
        self.do_quit()

    @staticmethod
    def do_quit():
        """Quits the program."""
        print('Quitting.')
        raise SystemExit

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

    ##########################################################################################
    def do_log(self, cmd_args):
        """
        Parse syslog message with grok patterns
        The 'pattern' parameter is optional. If specified, it is applied to the input message only if other pre-defined
        patterns defined in NSG Agent syslog configuration didn't match the message.

        log <message>

        Parameters:
            message - Syslog Message to be parsed, read stdin if not specified

        Examples:
            log "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host '10.1.1.1'"
            --pattern="Login failed for user '%{WORD:user_name}'" log "<13>May 18 11:22:43 carrier sshd:
            SSHD_LOGIN_FAILED: Login failed for user 'root' from host '10.1.1.1'"
            log <<< "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host 10.1.1.1"
        """

        if cmd_args is None or "" == cmd_args:
            self.read_stdin("log")
        else:
            self.call_grok_api("log", cmd_args)

    ##########################################################################################
    def do_text(self, cmd_args):
        """
        Parse text line with grok patterns.
        Require 'pattern' parameter.

        --pattern="Hello world of %{WORD:world_name}" text <text>

        Parameters:
            text - Text line to be parsed, if not specified input is taken from stdin

        Examples:
            --pattern="Hello world of %{WORD:world_name}" text "Hello world of Grok"
            --pattern="Hello world of %{WORD:world_name}" text <<< "Hello world of Grok"
        """

        if self.pattern is None:
            print("'pattern' parameter is missing")
            raise InvalidArgsException

        if cmd_args is None or "" == cmd_args:
            self.read_stdin("")
        else:
            self.call_grok_api("", cmd_args)

    def get_error(self, response):
        """
        if the response is in standard form (a dictionary with key 'error' or 'success') then
        this function finds and returns the value of the key 'error'. Otherwise it returns
        the whole response as a string
        """
        if isinstance(response, dict):
            return response.get('error', str(response))
        else:
            return str(response)

    def call_grok_api(self, parser, txt):
        request = 'v2/grok/net/{0}/parser/{1}'.format(self.netid, parser)
        try:
            data = {'text': txt}
            if self.pattern:
                data['pattern'] = self.pattern

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

    def read_stdin(self, parser):
        in_buffer = ""
        while True:
            select.select([sys.stdin.fileno()], [], [])
            read = os.read(sys.stdin.fileno(), 512)

            # empty read: EOF
            if len(read) == 0:
                # in_buffer might not be empty
                if len(in_buffer) > 0:
                    self.call_grok_api(parser, in_buffer)
                break

            # find newlines
            parts = read.split("\n")
            in_buffer += parts.pop(0)

            while len(parts) > 0:
                self.call_grok_api(parser, in_buffer)
                in_buffer = parts.pop(0)


class InvalidArgsException(Exception):
    pass