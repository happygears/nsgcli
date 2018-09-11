"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""


from __future__ import print_function

import json

import api
import sub_command

RESPONSE_FORMAT = """
Source: {m[agent]} ({m[agentAddress]})
Status: {m[status]}
Output: 
{m[output]}"""

TAIL_TEMPLATE_WITH_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?region={2}&args={3}'
TAIL_TEMPLATE_WITHOUT_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?args={2}'
AGENT_LOG_DIR = '/opt/nsg-agent/var/logs'

class HashableAgentCommandResponse(set):

    def __init__(self, acr):
        super(HashableAgentCommandResponse, self).__init__()
        self.acr = acr

    def __eq__(self, other):
        return self.acr['uuid'] == other.acr['uuid']

    def __hash__(self):
        # print(self.acr.items())
        return hash(self.acr['uuid'])

    def __getitem__(self, item):
        return self.acr.__getitem__(item)

    def __str__(self):
        return str(self.acr)


class AgentCommands(sub_command.SubCommand, object):
    # prompt = "exec # "

    def __init__(self, base_url, token, net_id, region=None):
        super(AgentCommands, self).__init__(base_url, token, net_id, region=region)
        self.current_region = region
        if region is None:
            self.prompt = 'agent # '
        else:
            self.prompt = 'agent [' + self.current_region + '] # '

    def completedefault(self, text, _line, _begidx, _endidx):
        # _line='show system' if user hits Tab after "show system"
        # this method is not called when user enters "show system" context and hits Tab then
        # print('ShowCommands.completedefault text=' + text + ', _line=' + _line)
        return self.get_args(text)

    def help(self):
        print('Call agents to execute various commands. Arguments: {0}'.format(self.get_args()))

    def do_log(self, arg):
        """
        retrieve agent's log file

        Example: agent log agent_name [-NN] log_file_name

        this command assumes standard directory structure on the agent where logs are
        located in /opt/nsg-agent/var/logs
        """
        args = arg.split()
        # args[0]=agent_name
        # args[-1]=file_name
        args[-1] = AGENT_LOG_DIR + '/' + args[-1]
        self.do_tail(' '.join(args))

    def do_tail(self, arg):
        """
        tail a file on an agent.

        Example: agent tail agent_name|all -100 /opt/nsg-agent/home/logs/agent.log
        """
        args = arg.split()
        if not args:
            print('At least two arguments (agent name and the file path) are required')
            self.do_help('tail')
            return

        cmd_args = ' '.join(args)

        if self.current_region:
            request = TAIL_TEMPLATE_WITH_REGION.format(self.netid, 'tail', self.current_region, cmd_args)
        else:
            request = TAIL_TEMPLATE_WITHOUT_REGION.format(self.netid, 'tail', cmd_args)

        try:
            response = api.call(self.base_url, 'GET', request, token=self.token, stream=True)
        except Exception as ex:
            print('ERROR: {0}'.format(ex))
        else:
            with response:
                status = response.status_code
                if status != 200:
                    for line in response.iter_lines():
                        print('ERROR: {0}'.format(self.get_error(json.loads(line))))
                        return

                for acr in api.transform_remote_command_response_stream(response):
                    status = self.parse_status(acr)
                    self.print_agent_response(acr, status)

    def do_find(self, args):
        """
        Find an agent responsible for polling given target (IP address).
        If region has been selected, checks only agents in the region. Otherwise tries
        agents in all regions

        Example: agent find 1.2.3.4
        """
        self.common_command('find_agent', args, hide_errors=True)

    def do_restart(self, args):
        """
        Restart agent with given name

        Example:  agent restart agent_name
        """
        if not args:
            args = 'all'
        # insert dummy element because common_command() expects the list of arguments to have at least
        # one item which is not needed for this command.
        self.common_command('restart_agent', args)

