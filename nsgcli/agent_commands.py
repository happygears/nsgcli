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

CMD_TEMPLATE_WITH_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?region={2}&args={3}'
CMD_TEMPLATE_WITHOUT_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?args={2}'
AGENT_LOG_DIR = '/opt/nsg-agent/var/logs'
HELP = """
Call agents to execute various commands.
        
log:    retrieve agent's log file
        this command assumes standard directory structure on the agent where logs are
        located in /opt/nsg-agent/var/logs

        Example: agent <agent_name> log [-NN] <log_file_name>


tail: tail a file on an agent.

        Example: agent <agent_name> tail -100 /opt/nsg-agent/home/logs/agent.log


probe_snmp: discover working snmp configuration for the device

        Example: agent <agent_name> probe_snmp <device_address> <snmp_conf_name_1> <snmp_conf_name_2> ...


find: Find an agent responsible for polling given target (IP address). Use 'all' in place of the agent name.

        Example: agent all find 1.2.3.4

"""


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

    def __init__(self, agent_name, base_url, token, net_id, region=None):
        super(AgentCommands, self).__init__(base_url, token, net_id, region=region)
        self.agent_name = agent_name
        self.current_region = region
        if region is None:
            self.prompt = 'agent {0} # '.format(self.agent_name)
        else:
            self.prompt = '[{0}] agent {1} # '.format(self.current_region, self.agent_name)

    def completedefault(self, text, _line, _begidx, _endidx):
        # _line='show system' if user hits Tab after "show system"
        # this method is not called when user enters "show system" context and hits Tab then
        # print('ShowCommands.completedefault text=' + text + ', _line=' + _line)
        return self.get_args(text)

    def help(self):
        print(HELP)

    def make_args(self, input_arg):
        args = input_arg.split()
        args.insert(0, self.agent_name) # agent name must be the first argument
        return ' '.join(args)

    def do_log(self, arg):
        """
        retrieve agent's log file

        Example: agent agent_name log [-NN] log_file_name

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

        Example: agent agent_name tail -100 /opt/nsg-agent/home/logs/agent.log
        """
        cmd_args = self.make_args(arg)

        if self.current_region:
            request = CMD_TEMPLATE_WITH_REGION.format(self.netid, 'tail', self.current_region, cmd_args)
        else:
            request = CMD_TEMPLATE_WITHOUT_REGION.format(self.netid, 'tail', cmd_args)

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

    def do_probe_snmp(self, arg):
        """
        try to discover working snmp configuration for the device

        Example: agent agent_name probe_snmp <device_address> <snmp_conf_name_1> <snmp_conf_name_2> ...
        """
        cmd_args = self.make_args(arg)

        if self.current_region:
            request = CMD_TEMPLATE_WITH_REGION.format(self.netid, 'discover-snmp-access', self.current_region, cmd_args)
        else:
            request = CMD_TEMPLATE_WITHOUT_REGION.format(self.netid, 'discover-snmp-access', cmd_args)

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
        Find an agent responsible for polling given target (IP address). This command
        does not require agent name argument.

        Example: agent find 1.2.3.4
        """
        self.common_command('find_agent', args, hide_errors=True)

    def do_restart(self, arg):
        """
        Restart agent with given name

        Example:  agent agent_name restart
        """
        cmd_args = self.make_args(arg)
        self.common_command('restart_agent', cmd_args)
