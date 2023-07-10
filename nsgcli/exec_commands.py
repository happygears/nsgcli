"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import json

from . import api
from . import sub_command

RESPONSE_FORMAT = """
Source: {m[agent]} ({m[agentAddress]})
Status: {m[status]}
Output: 
{m[output]}"""

EXEC_TEMPLATE_WITH_REGION = 'apiv3/net/{0}/exec/{1}?address={2}&region={3}&args={4}'
EXEC_TEMPLATE_WITHOUT_REGION = 'apiv3/net/{0}/exec/{1}?address={2}&args={3}'


class ExecCommands(sub_command.SubCommand, object):
    # prompt = "exec # "

    def __init__(self, base_url, token, net_id, region=None):
        super(ExecCommands, self).__init__(base_url, token, net_id, region=region)
        self.current_region = region
        if region is None:
            self.prompt = 'exec # '
        else:
            self.prompt = '[{0}] exec # '.format(self.current_region)

    def completedefault(self, text, _line, _begidx, _endidx):
        # _line='show system' if user hits Tab after "show system"
        # this method is not called when user enters "show system" context and hits Tab then
        # print('ShowCommands.completedefault text=' + text + ', _line=' + _line)
        return self.get_args(text)

    def help(self):
        print('Call agents to execute various commands. Arguments: {0}'.format(self.get_args()))

    def do_fping(self, arg):
        """
        Runs fping to give address on an agent. If region has been selected prior to running this command,
        uses only agents in the region. Otherwise tries all agents in all regions.

        fping <address> [fping args]

        fping exit codes:

        Exit status is 0 if all the hosts are reachable,
            1 if some hosts were unreachable,
            2 if any IP addresses were not found,
            3 for invalid command line arguments, and
            4 for a system call failure.
        """
        args = arg.split()
        if not args:
            print('At least one argument (target address) is required')
            self.do_help('fping')
            return

        address = args.pop(0)
        cmd_args = ' '.join(args)

        if self.current_region:
            request = EXEC_TEMPLATE_WITH_REGION.format(self.netid, 'fping', address, self.current_region, cmd_args)
        else:
            request = EXEC_TEMPLATE_WITHOUT_REGION.format(self.netid, 'fping', address, cmd_args)

        headers = {'Accept-Encoding': ''}  # to turn off gzip encoding to make response streaming work
        response, error = api.call(self.base_url, 'GET', request, token=self.token, headers=headers, stream=True,
                                   response_format='json_array', error_format='json_array')
        if error is None:
            for acr in response:
                fping_status = self.parse_fping_status(acr)
                self.print_agent_response(acr, fping_status)

    def do_ping(self, arg):
        """
        Tries to ping the address. If region has been selected, uses only agents in
        the region. Otherwise tries all agents in all regions.

        ping <address>
        """
        args = arg.split()
        if not args:
            print('At least one argument (target address) is required')
            self.do_help('ping')
            return

        address = args.pop(0)
        cmd_args = ' '.join(args)

        if self.current_region:
            request = EXEC_TEMPLATE_WITH_REGION.format(self.netid, 'ping', address, self.current_region, cmd_args)
        else:
            request = EXEC_TEMPLATE_WITHOUT_REGION.format(self.netid, 'ping', address, cmd_args)
        self.common_command(request, hide_errors=False)

    def do_traceroute(self, arg):
        """
        Runs traceroute to the given the address. If region has been selected, uses only agents in
        the region. Otherwise tries all agents in all regions.

        traceroute <address>
        """
        args = arg.split()
        if not args:
            print('At least one argument (target address) is required')
            self.do_help('traceroute')
            return

        address = args.pop(0)
        cmd_args = ' '.join(args)

        if self.current_region:
            request = EXEC_TEMPLATE_WITH_REGION.format(self.netid, 'traceroute', address, self.current_region, cmd_args)
        else:
            request = EXEC_TEMPLATE_WITHOUT_REGION.format(self.netid, 'traceroute', address, cmd_args)

        self.common_command(request, deduplicate_replies=False, hide_errors=False)

    def parse_fping_status(self, acr):
        ec = acr['exitStatus']
        if ec == 0:
            status = 'ok'
        elif ec == 1:
            status = 'some hosts were unreachable'
        elif ec == 2:
            status = 'any IP addresses were not found'
        elif ec == 3:
            status = 'invalid command line arguments'
        elif ec == 4:
            status = 'system call failure'
        elif ec == -1:
            status = 'could not find and execute the command'
        elif 'error' in acr:
            status = acr['error']
        else:
            status = 'unknown error'
        return status
