"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import json
import shlex

from . import agent_commands
from . import api
from . import device_commands
from . import discovery_commands
from . import exec_commands
from . import maintenance_commands
from . import search
from . import show
from . import sub_command

TIME_FORMAT_MS = 'ms'
TIME_FORMAT_ISO_UTC = 'iso_utc'
TIME_FORMAT_ISO_LOCAL = 'iso_local'

# SHOW_ARGS = ['version', 'uuid']
CACHE_ARGS = ['clear', 'refresh']
MAKE_ARGS = ['views', 'variables', 'maps', 'tags']
RELOAD_ARGS = ['config', 'devices', 'clusters']
RESTART_ARGS = ['tsdb', 'monitor']
CLUSTER_ARGS = ['status', 'summary', 'os', 'jvm', 'tsdb', 'python', 'c3p0']
SERVER_ARGS = ['pause', 'status']
EXEC_ARGS = ['ping', 'fping', 'traceroute']
FIND_AGENT_ARGS = ['find_agent']
DISCOVERY_ARGS = ['start', 'pause', 'resume', 'submit', 'status']
HUD_ARGS = ['reset']
DEVICE_ARGS = ['download']
NSGQL_ARGS = ['rebuild']  # command "nsgql rebuild" rebuilds NsgQL dynamic schema
# values of the debug argument that mean "no argument"
DEBUG_ARG_PLACEHOLDERS = ['all', 'none', '-']


class NsgCLI(sub_command.SubCommand, object):
    def __init__(self, base_url=None, token=None, netid=1, region=None, time_format=TIME_FORMAT_MS,
                 agent_prefix=sub_command.AGENT_PREFIX_AUTO):
        super(NsgCLI, self).__init__(base_url='', token='', net_id=1, agent_prefix=agent_prefix)
        self.base_url = base_url
        self.token = token
        self.time_format = time_format
        self.current_region = region
        self.netid = netid
        self.prompt = ' > '
        # exit status of the last one-shot command, used by bin/nsgcli; only commands that track
        # it (currently "maintenance") change it
        self.exit_status = 0
        # self.prompt = lambda _: self.make_prompt()

    def make_prompt(self):
        if self.current_region is None:
            self.prompt = ' > '
        else:
            self.prompt = ' [' + self.current_region + '] > '
        return self.prompt

    def summary(self):
        print()
        print('Type "help" to get list of commands; "help command" returns more details about selected command.')
        print('Typing "command" with no arguments executes it or enters this commands context.')
        print('"Tab" autocompletes and to exit, enter "quit", "q" or "Ctrl-D" at the prompt.')

    ##########################################################################################
    def do_region(self, arg):
        """Set the region; all subsequent commands will execute on the agents in the given region"""
        self.current_region = arg
        self.make_prompt()

    ##########################################################################################
    def do_ping(self, _):
        """Test server status with '/ping' API call

        "ping" NetSpyGlass server this cli client connects to. This returns "ok" if the server is up and running
        """
        request = 'v2/ping/net/{0}/se'.format(self.netid)
        response, error = api.call(self.base_url, 'GET', request, token=self.token)
        if error is None:
            print(response.content.decode(response.encoding))

    ##########################################################################################
    def do_show(self, arg):
        sub_cmd = show.ShowCommands(self.base_url, self.token, self.netid, time_format=self.time_format,
                                    region=self.current_region)
        if arg:
            sub_cmd.onecmd(arg)
        else:
            sub_cmd.cmdloop()

    def help_show(self):
        sub_cmd = show.ShowCommands(self.base_url, self.token, self.netid, time_format=self.time_format,
                                    region=self.current_region)
        return sub_cmd.help()

    def complete_show(self, text, _line, _begidx, _endidx):
        sub_cmd = show.ShowCommands(self.base_url, self.token, self.netid, time_format=self.time_format,
                                    region=self.current_region)
        return sub_cmd.completedefault(text, _line, _begidx, _endidx)

    ##########################################################################################
    def do_search(self, arg):
        sub_cmd = search.SearchCommand(self.base_url, self.token, self.netid, region=self.current_region)
        if arg:
            sub_cmd.onecmd(arg)
        else:
            sub_cmd.cmdloop()

    def help_search(self):
        sub_cmd = search.SearchCommand(self.base_url, self.token, self.netid, region=self.current_region)
        return sub_cmd.help()

    def complete_search(self, text, _line, _begidx, _endidx):
        sub_cmd = search.SearchCommand(self.base_url, self.token, self.netid, region=self.current_region)
        return sub_cmd.completedefault(text, _line, _begidx, _endidx)

    ##########################################################################################
    def do_reload(self, arg):
        if arg not in RELOAD_ARGS:
            print('Invalid argument "{0}"'.format(arg))
            return
        request = 'v2/ui/net/{0}/actions/reload/{1}'.format(self.netid, arg)
        response = self.basic_command(request)
        if response is not None:
            self.print_response(response)

    def help_reload(self):
        print('Reload things. Supported arguments: {0}'.format(RELOAD_ARGS))

    def complete_reload(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, RELOAD_ARGS)

    ##########################################################################################
    def do_make(self, arg):
        if arg not in MAKE_ARGS:
            print('Invalid argument "{0}"'.format(arg))
            return
        request = 'v2/ui/net/{0}/actions/make/{1}'.format(self.netid, arg)
        response = self.basic_command(request)
        if response is not None:
            self.print_response(response)

    def help_make(self):
        print('Make things. Supported arguments: {0}'.format(MAKE_ARGS))

    def complete_make(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, MAKE_ARGS)

    ##########################################################################################
    def do_discovery(self, arg):
        """
        Manage discovery process. Supported commands:

        discovery start      --  deprecated, supported for backward compatibility with NSG clusters
                                 that do not implement incremental discovery
        discovery pause
        discovery resume
        discovery schedule device1 device2 device3   where each device is identified by device ID, name, sysName or address

        :param arg: command, possibly with argument (separated by space)
        """
        sub_cmd = discovery_commands.DiscoveryCommands(self.base_url, self.token, self.netid, self.time_format)
        if not arg:
            sub_cmd.cmdloop()
        else:
            sub_cmd.onecmd(arg)

    def help_discovery(self):
        sub_cmd = discovery_commands.DiscoveryCommands(self.base_url, self.token, self.netid, self.time_format)
        sub_cmd.help()

    def complete_discovery(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, DISCOVERY_ARGS)

    ##########################################################################################
    def do_device(self, arg):
        """
        download device. Supported commands:

        device download (devID|name)

        :param arg: command, possibly with argument
        """
        sub_cmd = device_commands.DeviceCommands(self.base_url, self.token, self.netid, self.time_format)
        if not arg:
            sub_cmd.cmdloop()
        else:
            sub_cmd.onecmd(arg)

    def help_device(self):
        sub_cmd = device_commands.DeviceCommands(self.base_url, self.token, self.netid, self.time_format)
        sub_cmd.help()

    def complete_device(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, DEVICE_ARGS)

    ##########################################################################################
    def make_maintenance_commands(self):
        return maintenance_commands.MaintenanceCommands(self.base_url, self.token, self.netid,
                                                        region=self.current_region)

    def do_maintenance(self, arg):
        """
        Cluster-wide maintenance operations (require the admin role). See "help maintenance".
        """
        sub_cmd = self.make_maintenance_commands()
        if not arg:
            sub_cmd.cmdloop()
        else:
            sub_cmd.onecmd(arg)
            self.exit_status = sub_cmd.exit_status

    def help_maintenance(self):
        self.make_maintenance_commands().help()

    def complete_maintenance(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, list(maintenance_commands.MAINTENANCE_COMMANDS.keys()))

    do_maint = do_maintenance
    help_maint = help_maintenance
    complete_maint = complete_maintenance

    ##########################################################################################
    def do_debug(self, arg):
        """
        Set debug level and optional argument with optional timeout:

        debug level
        OR
        debug level time_min
        OR
        debug level arg time_min

        If only one argument is given, it is assumed to be the debug level and it will be set for 10 min.
        If two arguments are given, they are interpreted as debug level and the time in minutes.
        If three arguments are given, they are interpreted as debug level, debug argument and the time in
        minutes. Use "-" (or "all", "none") as the argument to pass an empty one.

        Debug level and argument are passed to all servers in the cluster via inter-process message bus.
        Timeout is in minutes. Debug level reverts to its current value and argument
        is erased after timeout. The default timeout is 10 min. If timeout=0, then debug
        level is set indefinitely. Argument can not contain spaces.

        Recognized debug levels: (enter the number as argument 'level', values can be combined with bitwise OR):

        DEBUG_NSGQL = 1
        DEBUG_DATA_POOL = 2
        DEBUG_AGENT_RESPONSES = 3
        DEBUG_COMPUTE = 4
        DEBUG_TSDB = 5
        DEBUG_STATUS = 6
        DEBUG_ZOOKEEPER = 7
        DEBUG_CACHES = 8
        DEBUG_SOCKET_IO = 9
        DEBUG_GRAPH = 10
        DEBUG_VARS = 11
        DEBUG_DATA_PUSH = 12
        DEBUG_SYSTEM_EVENTS_AND_HUD = 13
        DEBUG_INDEXER = 14
        DEBUG_MVARS = 15
        DEBUG_REDIS_EXECUTOR = 16
        DEBUG_AGENT_RESPONSE_CYCLE = 17
        DEBUG_DEVICES = 18
        DEBUG_DISCOVERY = 19
        DEBUG_AGENT_COMMAND_EXECUTION = 20
        DEBUG_STATE_MANAGER = 21
        DEBUG_TAGS = 22
        DEBUG_ALERTS = 23
        DEBUG_REPORTS = 24
        DEBUG_CLUSTERS = 25
        DEBUG_SERVER_LIFE_CYCLE = 26
        DEBUG_SELF_MONITORING = 27
        DEBUG_AGGREGATION = 28
        DEBUG_THRESHOLDS = 29
        DEBUG_WEB_SERVER_SESSIONS = 30
        DEBUG_WEBDAV = 31
        DEBUG_VIEWS = 32
        """
        if not arg:
            print('Invalid argument "{0}"; see "help debug"'.format(arg))
            return
        # "level", "level time_min" or "level arg time_min"
        try:
            comps = shlex.split(arg)
            level = int(comps[0])
            if len(comps) == 1:
                # only level has been specified
                arg = ''
                time = 10
            elif len(comps) == 2:
                arg = ''
                time = int(comps[1])
            elif len(comps) == 3:
                arg = comps[1]
                time = int(comps[2])
            else:
                print('Invalid number of arguments; expected 1, 2 or 3 arguments, but got {0}'.format(arg))
                return
            if arg.lower() in DEBUG_ARG_PLACEHOLDERS:
                arg = ''
            request = 'v2/nsg/test/net/{0}/debug'.format(self.netid)
            response = self.basic_command(request, data={'level': level, 'time': time, 'arg': arg})
            if response is not None:
                self.print_response(response)
        except Exception as e:
            print('Error: {0}'.format(e))

    ##########################################################################################
    def do_expire(self, arg):
        """
        Force expiration of variables in the data pool of all servers. Syntax:

        expire retention_hrs

        Retention is in hours and can be fractional (e.g.  "expire 0.1" for 0.1 hours)
        """
        if not arg:
            print('Invalid argument "{0}"; expected a number'.format(arg))
            return
        # arg is a number: retention time in hours that can be fractional (floating point)
        try:
            retention = float(arg)
            request = 'v2/ui/net/{0}/actions/expire/variables?retentionHrs={1}'.format(self.netid, retention)
            response = self.basic_command(request)
            if response is not None:
                self.print_response(response)
        except Exception as e:
            print('Error: {0}'.format(e))

    ##########################################################################################
    def do_agent(self, arg):
        """
        agent [agent_name|all] command args
        """
        if not arg:
            print('Invalid command {0}: command "agent" requires at least one argument: agent name'.format(arg))
            return

        args = arg.split(' ')
        # arg[0] = agent_name
        # arg[1] = command
        if args[0] == 'find':
            # this command does not need agent name
            agent_name = 'all'
        else:
            agent_name = args.pop(0)

        work_args = ' '.join(args)
        if not work_args:
            sub_cmd = agent_commands.AgentCommands(agent_name, self.base_url, self.token, self.netid,
                                                   region=self.current_region, agent_prefix=self.agent_prefix)
            sub_cmd.cmdloop()
        else:
            sub_cmd = agent_commands.AgentCommands(agent_name, self.base_url, self.token, self.netid,
                                                   region=self.current_region, agent_prefix=self.agent_prefix)
            sub_cmd.onecmd(work_args)

    def help_agent(self):
        sub_cmd = agent_commands.AgentCommands('', self.base_url, self.token, self.netid, region=self.current_region)
        sub_cmd.help()

    def complete_agent(self, text, _line, _begidx, _endidx):
        sub_cmd = agent_commands.AgentCommands('', self.base_url, self.token, self.netid, region=self.current_region)
        return sub_cmd.completedefault(text, _line, _begidx, _endidx)

    ##########################################################################################
    def do_exec(self, arg):
        """
        exec command args

        @param arg:   words after 'exec' as one string
        """
        sub_cmd = exec_commands.ExecCommands(self.base_url, self.token, self.netid, region=self.current_region,
                                             agent_prefix=self.agent_prefix)
        if not arg:
            sub_cmd.cmdloop()
        else:
            sub_cmd.onecmd(arg)

    def help_exec(self):
        sub_cmd = exec_commands.ExecCommands(self.base_url, self.token, self.netid, region=self.current_region)
        sub_cmd.help()

    def complete_exec(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, EXEC_ARGS)

    ##########################################################################################
    def basic_command(self, request, data=None):
        """
        execute simple command via API call and return deserialized response
        """
        response, error = api.call(self.base_url, 'GET', request, data=data, token=self.token, response_format='json',
                                   error_format='json_array')
        return response
