"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""


from __future__ import print_function

import json

import nsgcli.api
import nsgcli.sub_command
import nsgcli.system

RESPONSE_FORMAT = """
Source: {m[agent]} ({m[agentAddress]})
Status: {m[status]}
Output: 
{m[output]}"""

EXEC_TEMPLATE_WITH_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?address={2}&region={3}&args={4}'
EXEC_TEMPLATE_WITHOUT_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?address={2}&args={3}'

# FPING_TEMPLATE_WITH_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?address={2}&region={3}&args={4}'
# FPING_TEMPLATE_WITHOUT_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?address={2}&args={3}'


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


class ExecCommands(nsgcli.sub_command.SubCommand, object):
    # prompt = "exec # "

    def __init__(self, base_url, token, net_id, region=None):
        super(ExecCommands, self).__init__(base_url, token, net_id, region=region)
        self.current_region = region
        self.system_commands = nsgcli.system.SystemCommands(self.base_url, self.token, self.netid, region=region)
        if region is None:
            self.prompt = 'exec # '
        else:
            self.prompt = 'exec [' + self.current_region + '] # '

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

        try:
            response = nsgcli.api.call(self.base_url, 'GET', request, token=self.token, stream=True)
        except Exception as ex:
            print('ERROR: {0}'.format(ex))
        else:
            with response:
                status = response.status_code
                if status != 200:
                    for line in response.iter_lines():
                        print('ERROR: {0}'.format(self.get_error(json.loads(line))))
                        return

                for acr in nsgcli.api.transform_remote_command_response_stream(response):
                    fping_status = self.parse_fping_status(acr)
                    self.print_agent_response(acr, fping_status)

    def do_ping(self, args):
        """
        Tries to ping the address. If region has been selected, uses only agents in
        the region. Otherwise tries all agents in all regions.

        ping <address>
        """
        self.common_command('ping', args, hide_errors=False)

    def do_traceroute(self, args):
        """
        Runs traceroute to the given the address. If region has been selected, uses only agents in
        the region. Otherwise tries all agents in all regions.

        traceroute <address>
        """
        self.common_command('traceroute', args, deduplicate_replies=False, hide_errors=False)

    def do_find_agent(self, args):
        """
        Find an agent responsible for polling given target (IP address).
        If region has been selected, checks only agents in the region. Otherwise tries
        agents in all regions

        Example:  find_agent 1.2.3.4
        """
        self.common_command('find_agent', args, hide_errors=True)

    def do_restart_agent(self, args):
        """
        Restart agents.
        If region has been selected, restarts agents in the region, otherwise restarts all agents

        Example:  restart_agent
        """
        if not args:
            args = 'all'
        # insert dummy element because common_command() expects the list of arguments to have at least
        # one item which is not needed for this command.
        self.common_command('restart_agent', args)

    def common_command(self, command, arg, hide_errors=True, deduplicate_replies=True):
        """
        send command to agents and pick up replies. If hide_errors=True, only successful
        replies are printed, otherwise all replies are printed.

        If deduplicate_replies=True, duplicate replies are suppressed (e.g. when multiple agents
        reply)
        """
        args = arg.split()
        if not args:
            print('At least one argument (target address) is required')
            self.do_help(command)
            return

        address = args.pop(0)
        cmd_args = ' '.join(args)

        if self.current_region:
            req = EXEC_TEMPLATE_WITH_REGION.format(self.netid, command, address, self.current_region, cmd_args)
        else:
            req = EXEC_TEMPLATE_WITHOUT_REGION.format(self.netid, command, address, cmd_args)

        # print(response)

        try:
            response = nsgcli.api.call(self.base_url, 'GET', req, token=self.token, stream=True)
        except Exception as ex:
            print('ERROR: {0}'.format(ex))
        else:
            with response:
                status = response.status_code
                if status != 200:
                    for line in response.iter_lines():
                        print('ERROR: {0}'.format(self.get_error(json.loads(line))))
                        return

                # This call returns list of AgentCommandResponse objects in json format
                # print(response)
                replies = []
                for acr in nsgcli.api.transform_remote_command_response_stream(response):
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

    def parse_status(self, acr):
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
