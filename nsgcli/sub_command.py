"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import cmd

from . import api

SKIP_NAMES_FOR_COMPLETION = ['EOF', 'q']

EXEC_TEMPLATE_WITH_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?address={2}&region={3}&args={4}'
EXEC_TEMPLATE_WITHOUT_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?address={2}&args={3}'


class HashableAgentCommandResponse(set):

    def __init__(self, acr):
        self.acr = acr

    def __eq__(self, other):
        return self.acr['uuid'] == other.acr['uuid']

    def __hash__(self):
        # print(self.acr.items())
        return hash(self.acr['uuid'])

    def __getitem__(self, item):
        return self.acr.__getitem__(item)

    def __str__(self):
        return str(acr)


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
        if isinstance(response, list):
            return self.is_error(response[0])
        if isinstance(response, dict):
            return response.get('error', None) is not None or response.get('status', 'ok').lower() != 'ok'
        else:
            return False

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

    def get_success(self, response):
        """
        if the response is in standard form (a dictionary with key 'error' or 'success') then
        this function finds and returns the value of the key 'success'. Otherwise it returns
        the whole response as a string
        """
        if isinstance(response, dict):
            return response.get('success', str(response))
        else:
            return str(response)

    def common_command(self, req, method='GET', hide_errors=True, deduplicate_replies=True):
        """
        send command to agents and pick up replies. If hide_errors=True, only successful
        replies are printed, otherwise all replies are printed.

        If deduplicate_replies=True, duplicate replies are suppressed (e.g. when multiple agents
        reply)
        """

        headers = {'Accept-Encoding': ''}  # to turn off gzip encoding to make response streaming work
        response, error = api.call(self.base_url, method, req, token=self.token,
                                   headers=headers, stream=True, response_format='json_array',
                                   error_format='json_array')
        if error is None:
            replies = []
            for acr in response:
                status = self.parse_status(acr)
                if not hide_errors or status == 'ok':
                    replies.append((status, HashableAgentCommandResponse(acr)))
            if deduplicate_replies:
                for status, acr in set(replies):
                    self.print_agent_response(acr, status)
            else:
                for status, acr in replies:
                    self.print_agent_response(acr, status)

    def print_agent_response(self, acr, status):
        try:
            if not status or status == 'ok':
                for line in acr['response']:
                    print('{0} | {1}'.format(acr['agent'], line))
            else:
                print('{0} | {1}'.format(acr['agent'], status))
        except Exception as e:
            print(e)
            print(acr)

    def parse_status(self, acr):
        try:
            ec = acr['exitStatus']
            if ec == 0:
                status = 'ok'
            elif 'error' in acr:
                status = acr['error']
            elif ec == -1:
                status = 'could not find and execute the command'
            else:
                status = 'unknown error'
            return status
        except Exception as e:
            print('Can not parse status in "{0}"'.format(acr))
            return 'unknown'
