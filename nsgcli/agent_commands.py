"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from . import api
from . import sub_command
from .exec_commands import ExecCommands

RESPONSE_FORMAT = """
Source: {m[agent]} ({m[agentAddress]})
Status: {m[status]}
Output:
{m[output]}"""

CMD_TEMPLATE_URL_WITH_AGENT = '/apiv3/net/{0}/exec/{1}/agent/{2}?{3}'

AGENT_LOG_DIR = '/opt/nsg-agent/var/logs'
HELP = """
Call agents to execute various commands.

log:    retrieve agent's log file
        this command assumes standard directory structure on the agent where logs are
        located in /opt/nsg-agent/var/logs

        Example:

            agent <agent_name> log [-NN] <log_file_name>


tail: tail a file on an agent.

        Example:

            agent <agent_name> tail -100 /opt/nsg-agent/var/logs/agent.log


probe_snmp: discover working snmp configuration for the device

        Example:

            agent <agent_name> probe_snmp <device_address> <snmp_conf_name_1> <snmp_conf_name_2> ...


find: Find an agent responsible for polling given target (IP address). Use 'all' in place of the agent name.

        Example:

            agent all find 1.2.3.4

restart: restart the agent

        Example: agent <agent_name> restart

snmp:    run snmp get or snmp walk command

        Arguments:

            agent <agent_name> snmpget <address> oid
            agent <agent_name> snmpwalk <address> oid

        Example:

            agent <agent_name> snmpget  10.0.0.1 .1.3.6.1.2.1.1.2.0

set_property:    set (or query) value of JVM system property

        Arguments:

            agent <agent_name> set_property foo
            agent <agent_name> set_property foo bar

set_log_level:  Contacts given agent (or all), and changes the log level of the particular logger for 
                specified time interval.
        
        Arguments:
        
            agent <agent_name> set_log_level logger-name logger-name [duration]

            logger-name - full class name or package name, if package name specified,
                          log level will be applied to all classes in a package
            logger-name - one of [debug, info, warn, error, trace, off, fatal, all]
            duration    - Optional. Time interval of how long the changed log level will be in effect.
                          When interval expires, log level is reverted to original value.
                          Value has to comply with ISO-8601 duration format. Ex. PT10M = 10 minutes.
                          If not provided, default interval is 10 minutes.

measurements:    query current values of agent monitoring variables

        Example:

            agent <agent_name> measurements
            
ping:   Tries to ping the address from the given agent.

        Arguments:

            agent <agent_name> ping <address>
            
            address - IP address

        Example:

            agent <agent_name> ping 8.8.8.8
            
fping:  Runs fping to give address on a given agent.

        Arguments:

            agent <agent_name> fping <address> [fping args]

        fping exit codes:

        Exit status is 0 if all the hosts are reachable,
            1 if some hosts were unreachable,
            2 if any IP addresses were not found,
            3 for invalid command line arguments, and
            4 for a system call failure.
            
traceroute: Runs traceroute to the given the address.

        Arguments:

            agent <agent_name> traceroute <address>            
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

    def do_tail(self, args):
        """
        tail a file on an agent.

        Example: agent agent_name tail -100 /opt/nsg-agent/var/logs/agent.log
        """
        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'tail', self.agent_name, 'args=' + args)

        response, error = api.call(self.base_url, 'GET', request, token=self.token, stream=True,
                                   response_format='json_array', error_format='json_array')
        if error is None:
            for acr in response:
                status = self.parse_status(acr)
                self.print_agent_response(acr, status)

    def do_probe_snmp(self, arg):
        """
        try to discover working snmp configuration for the device

        Example: agent agent_name probe_snmp <device_address> <snmp_conf_name_1> <snmp_conf_name_2> ...
        """
        args = arg.split()
        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'discover-snmp-access', self.agent_name,
                                                     'address=' + args.pop(0) + '&args=' + ' '.join(args))

        response, error = api.call(self.base_url, 'GET', request, token=self.token, stream=True,
                                   response_format='json_array', error_format='json_array')
        if error is None:
            for acr in response:
                status = self.parse_status(acr)
                self.print_agent_response(acr, status)

    def do_find(self, args):
        """
        Find an agent responsible for polling given target (IP address). This command
        does not require agent name argument.

        Example: agent find 1.2.3.4
        """
        if not self.current_region or self.current_region.isspace():
            print("Region must be specified for this command")
            exit(1)

        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid,
                                                     'find_agent',
                                                     self.agent_name,
                                                     'region=' + self.current_region + '&address=' + args)

        self.common_command(request, hide_errors=True)

    def do_restart(self, args):
        """
        Restart agent with given name

        Example:  agent agent_name restart
        """
        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'restart', self.agent_name, '')
        self.common_command(request)

    def do_ping(self, arg):
        """
        Tries to ping the address from the given agent.

        agent <agent_name> ping <address>
        """
        args = arg.split()
        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'ping', self.agent_name,
                                                     'address=' + args.pop(0) + '&args=' + ' '.join(args))

        response, error = api.call(self.base_url, 'GET', request, token=self.token, stream=True,
                                   response_format='json_array', error_format='json_array')
        if error is None:
            for acr in response:
                status = self.parse_status(acr)
                self.print_agent_response(acr, status)

    def do_fping(self, arg):
        """
        Runs fping to give address on a given agent.

        fping <address> [fping args]

        fping exit codes:

        Exit status is 0 if all the hosts are reachable,
            1 if some hosts were unreachable,
            2 if any IP addresses were not found,
            3 for invalid command line arguments, and
            4 for a system call failure.
        """
        args = arg.split()
        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'fping', self.agent_name,
                                           'address=' + args.pop(0) + '&args=' + ' '.join(args))

        headers = {'Accept-Encoding': ''}  # to turn off gzip encoding to make response streaming work
        response, error = api.call(self.base_url, 'GET', request, token=self.token, headers=headers, stream=True,
                                   response_format='json_array', error_format='json_array')
        if error is None:
            for acr in response:
                fping_status = ExecCommands.parse_fping_status(acr)
                self.print_agent_response(acr, fping_status)

    def do_traceroute(self, arg):
        """
        Runs traceroute to the given the address.

        traceroute <address>
        """
        args = arg.split()

        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'traceroute', self.agent_name,
                                                     'address=' + args.pop(0) + '&args=' + ' '.join(args))

        self.common_command(request, deduplicate_replies=False, hide_errors=False)

    def do_snmpget(self, args):
        """
        Execute snmp GET command using agents in the currently selected region

        agent <agent_name> snmp_get <address> oid [timeout_ms]
        """

        self.snmp_command('snmpget', args)

    def do_snmpwalk(self, args):
        """
        Execute snmp WALK command using agents in the currently selected region

        agent <agent_name> snmp_walk <address> oid [timeout_ms]
        """

        self.snmp_command('snmpwalk', args)

    def do_set_property(self, arg):
        """
        Contacts given agent (or all), and sets the system property key to value.
        (If value is omitted, the current value of the property is returned.)

        agent <agent_name> set_property key [value]
        """
        args = arg.split()
        query = ''
        if len(args) > 1:
            query = 'key=' + args.pop(0) + '&value=' + args.pop(0)
        elif len(args) > 0:
            query = 'key=' + args.pop(0)

        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'set_property', self.agent_name, query)
        self.common_command(request, method='PUT')

    def do_set_log_level(self, arg):
        """
        Contacts given agent (or all), and changes the log level of the particular logger for specified time interval.

        0 - logger-name - full class name or package name, if package name specified,
                          log level will be applied to all classes in a package
        1 - log-level   - one of [debug, info, warn, error, trace, off, fatal, all]
        2 - duration    - Optional. Time interval of how long the changed log level will be in effect.
                          When interval expires, log level is reverted to original value.
                          Value has to comply with ISO-8601 duration format. Ex. PT10M = 10 minutes.
                          If not provided, default interval is 10 minutes.

        agent <agent_name> set_log_level logger level [duration]
        """
        args = arg.split()
        query = ''
        if len(args) > 2:
            query = 'logger=' + args.pop(0) + '&log_level=' + args.pop(0) + '&duration=' + args.pop(0)
        elif len(args) > 1:
            query = 'logger=' + args.pop(0) + '&log_level=' + args.pop(0)
        else:
            print('Missing command arguments, logger name and logger are required')

        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'set_log_level', self.agent_name, query)
        self.common_command(request, method='PUT')

    def do_get_syslog_stats(self, args):
        """
        Contacts given agent (or all), and gets statistics of syslog server network IO

        agent <agent_name> get_syslog_stats
        """
        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'get_syslog_stats', self.agent_name, '')
        self.common_command(request)

    def do_get_configuration(self, args):
        """
        Contacts given agent (or all), and requests active configuration

        agent <agent_name> get_configuration
        """
        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'get_configuration', self.agent_name, '')
        self.common_command(request)

    def do_measurements(self, args):
        """
        Contacts agent (or all), and retrieves current values of its monitoring
        variables.

        agent <agent_name> measurements
        """
        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'measurements', self.agent_name, '')
        self.common_command(request)

    def do_bulk_request(self, args):
        """
        Contacts agent (or all), and retrieves current bulk request
        for given device ID.

        agent <agent_name> bulk_request <device_ID>
        """
        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, 'bulk_request', self.agent_name, 'device_id=' + args)
        self.common_command(request)

    def snmp_command(self, command, arg):
        """
        snmp_get <agent> <address> oid [timeout_ms]
        snmp_walk <agent> <address> oid [timeout_ms]
        """
        args = arg.split()

        # address = args[0]
        # oid = args[1]
        # timeout_ms = 2000
        # if len(args) > 2:
        #     timeout_ms = int(args[2])

        if len(args) < 4:
            args.append('2000')

        request = CMD_TEMPLATE_URL_WITH_AGENT.format(self.netid, command, self.agent_name,
                                                     'address=' + args.pop(0) +
                                                     '&oid=' + args.pop(0) +
                                                     '&timeout=' + args.pop(0)
                                                     )

        # This call returns list of AgentCommandResponse objects in json format
        headers = {'Accept-Encoding': ''}
        response, error = api.call(self.base_url, 'GET', request, token=self.token, stream=True,
                                   headers=headers, response_format='json_array', error_format='json_array')
        if error is None:
            for acr in response:
                status = self.parse_status(acr)
                self.print_agent_response(acr, status)
