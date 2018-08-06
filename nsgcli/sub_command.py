"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import cmd
import types

SKIP_NAMES_FOR_COMPLETION = ['EOF', 'q']


def sizeof_fmt(num, suffix='B'):
    if not num:
        return ''
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.3f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.3f %s%s" % (num, 'Y', suffix)


class SubCommand(cmd.Cmd, object):
    # prompt = "(sub_command) "

    def __init__(self, base_url, token, net_id, region=None):
        super(SubCommand, self).__init__()
        self.base_url = base_url
        self.token = token
        self.netid = net_id
        self.current_region = region
        if region is None:
            self.prompt = 'sub # '
        else:
            self.prompt = 'sub [' + self.current_region + '] # '

    def emptyline(self):
        pass

    def do_quit(self, args):
        return True

    do_EOF = do_quit
    do_q = do_quit

    def complete(self, text, state):
        """Return the next possible completion for 'text'.

        This simply calls the same function in the parent class and then adds a white space at the end.
        Standard implementation completes 'cl' with 'cluster' (no space) so I have to hit space before
        I can enter the argument. I do not want to do that.
        """
        return super(SubCommand, self).complete(text, state) + ' '

    def complete_cmd(self, text, variants):
        if not text:
            completions = variants[:]
        else:
            completions = [f for f in variants if f.startswith(text)]
        return completions

    def get_args(self, text=''):
        return [x for x in self.completenames(text) if x not in SKIP_NAMES_FOR_COMPLETION]

    def completedefault(self, text, _line, _begidx, _endidx):
        # print('SubCommand.completedefault text=' + text + ', _line=' + _line)
        return self.get_args(text)

    def print_success(self, response):
        print(response['success'])

    def print_response(self, response):
        if self.is_error(response):
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            self.print_success(response)

    def is_error(self, response):
        if isinstance(response, types.ListType):
            return self.is_error(response[0])
        return isinstance(response, types.DictionaryType) and response.get('status', 'ok').lower() != 'ok'

    def get_error(self, response):
        if isinstance(response, dict):
            return response.get('error', str(response))
        else:
            return str(response)
