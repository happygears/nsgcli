"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import getopt
import json
from pyhocon import ConfigFactory
import sys

import api
import index
import show
import search
import agent_commands
import snmp_commands
import exec_commands
import sub_command


HTTP_OVER_UNIX_SOCKET_PROTOCOL = 'http+unix://'
STANDARD_UNIX_SOCKET_PATH = HTTP_OVER_UNIX_SOCKET_PROTOCOL + '/opt/netspyglass/var/data/socket/jetty.sock'

# SHOW_ARGS = ['version', 'uuid']
CACHE_ARGS = ['clear', 'refresh']
MAKE_ARGS = ['views', 'variables', 'maps', 'tags']
RELOAD_ARGS = ['config', 'devices']
RESTART_ARGS = ['tsdb', 'monitor']
CLUSTER_ARGS = ['status', 'summary', 'os', 'jvm', 'tsdb', 'python', 'c3p0']
SERVER_ARGS = ['pause', 'status']
EXEC_ARGS = ['ping', 'fping', 'traceroute']
FIND_AGENT_ARGS = ['find_agent']
SNMP_ARGS = ['get', 'walk']
DISCOVERY_ARGS = ['start']
HUD_ARGS = ['reset']

usage_msg = """
Interactive NetSpyGlass control script. This script can only communicate with 
NetSpyGlass server running on the same machine.

Usage:

    nsgcli.py [--socket=abs_path_to_unix_socket] [--base-url=url] [--token=token] [--network=netid] [--region=region] [command]
    
    --socket:    a path to the unix socket created by the server that can be used to access it 
                 when script runs on the same machine. Usually /opt/netspyglass/home/data/socket/jetty.sock
    --base-url:  server access URL without the path, for example 'http://nsg.domain.com:9100'
    --token:     server API access token (if the server is configured with user authentication)
    --region:    if present, all commands will be executed on given region. Equivalent to the command 'region' in
                 the interactive mode.

    all arguments provided on the command line after the last switch are interpreted together as nsgcli command
"""


def usage():
    print(usage_msg)


class InvalidArgsException(Exception):
    pass


class NsgCLI(sub_command.SubCommand, object):
    def __init__(self):
        super(NsgCLI, self).__init__(base_url=STANDARD_UNIX_SOCKET_PATH, token='', net_id=1)
        self.base_url = ''
        self.command = ''
        self.current_region = None
        self.nsg_config = ''
        self.token = ''
        self.netid = 1
        self.prompt = ' > '
        # self.prompt = lambda _: self.make_prompt()

    def make_prompt(self):
        if self.current_region is None:
            self.prompt = ' > '
        else:
            self.prompt = ' [' + self.current_region + '] > '
        return self.prompt

    def parse_args(self, argv):

        try:
            opts, args = getopt.getopt(argv,
                                       'hs:b:t:n:r:C:',
                                       ['help', 'socket=', 'base-url=', 'token=', 'network=', 'region=', 'config='])
        except getopt.GetoptError as ex:
            print('UNKNOWN: Invalid Argument:' + str(ex))
            raise InvalidArgsException

        for opt, arg in opts:
            if opt in ['-h', '--help']:
                usage()
                sys.exit(3)
            elif opt in ('-s', '--socket'):
                if arg[0] != '/':
                    print('Argument of --socket must be an absolute path to the unix socket')
                    sys.exit(1)
                self.base_url = HTTP_OVER_UNIX_SOCKET_PROTOCOL + arg
            elif opt in ('-b', '--base-url'):
                self.base_url = arg.rstrip('/ ')
            elif opt in ('-a', '--token'):
                self.token = arg
            elif opt in ('-n', '--network'):
                self.netid = arg
            elif opt in ['-r', '--region']:
                self.current_region = arg
            elif opt in ['-C', '--config']:
                # if path to nsg config file is provided using this parameter, then --token is interpreted as
                # the path to the configuration parameter in this file
                self.nsg_config = arg
            if args:
                self.command = ' '.join(args)

        if self.nsg_config and self.token:
            # print('using NSG config {0}, parameter {1}'.format(self.nsg_config, self.token))
            conf = ConfigFactory.parse_file(self.nsg_config)
            self.token = conf.get_string(self.token)

        self.make_prompt()

    def summary(self):
        print()
        if self.nsg_config and self.token:
            print('using NSG config {0}, parameter {1}'.format(self.nsg_config, self.token))
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
        try:
            response = api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            print(response.content)

    ##########################################################################################
    def do_show(self, arg):
        sub_cmd = show.ShowCommands(self.base_url, self.token, self.netid, region=self.current_region)
        if arg:
            sub_cmd.onecmd(arg)
        else:
            sub_cmd.cmdloop()

    def help_show(self):
        sub_cmd = show.ShowCommands(self.base_url, self.token, self.netid, region=self.current_region)
        return sub_cmd.help()

    def complete_show(self, text, _line, _begidx, _endidx):
        sub_cmd = show.ShowCommands(self.base_url, self.token, self.netid, region=self.current_region)
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
        sub_cmd = seach.SearchCommand(self.base_url, self.token, self.netid, region=self.current_region)
        return sub_cmd.completedefault(text, _line, _begidx, _endidx)

    ##########################################################################################
    def do_index(self, arg):
        sub_cmd = index.IndexCommands(self.base_url, self.token, self.netid, region=self.current_region)
        if arg:
            sub_cmd.onecmd(arg)
        else:
            sub_cmd.cmdloop()

    def help_index(self):
        sub_cmd = index.IndexCommands(self.base_url, self.token, self.netid, region=self.current_region)
        return sub_cmd.help()

    def complete_index(self, text, _line, _begidx, _endidx):
        sub_cmd = index.IndexCommands(self.base_url, self.token, self.netid, region=self.current_region)
        return sub_cmd.completedefault(text, _line, _begidx, _endidx)

    ##########################################################################################
    def do_cache(self, arg):
        if arg not in CACHE_ARGS:
            print('Invalid argument "{0}"'.format(arg))
            return
        response = self.basic_command('v2/ui/net/{0}/actions/cache/{1}'.format(self.netid, arg))
        if response is not None:
            self.print_response(response)

    def help_cache(self):
        print('Operations with cache. Supported arguments: {0}'.format(CACHE_ARGS))

    def complete_cache(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, CACHE_ARGS)

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
        if arg not in DISCOVERY_ARGS:
            print('Invalid argument "{0}"'.format(arg))
            return
        request = 'v2/nsg/discovery/net/{0}/{1}'.format(self.netid, arg)
        response = self.basic_command(request)
        if response is not None:
            self.print_response(response)

    def help_discovery(self):
        print('Operations with network discovery. Supported arguments: {0}'.format(DISCOVERY_ARGS))

    def complete_discovery(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, DISCOVERY_ARGS)

    ##########################################################################################
    def do_hud(self, arg):
        if arg not in HUD_ARGS:
            print('Invalid argument "{0}"'.format(arg))
            return
        request = 'v2/nsg/test/net/{0}/hud/{1}'.format(self.netid, arg)
        response = self.basic_command(request)
        if response is not None:
            self.print_response(response)

    def help_hud(self):
        print('Operations with HUD in the UI. Supported arguments: {0}'.format(HUD_ARGS))

    def complete_hud(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, HUD_ARGS)

    ##########################################################################################
    def do_restart(self, arg):
        """
        restart various components:

        restart tsdb         - restarts tsdb connector
        restart monitor      - restarts monitor (the component that communicates with NetSpyGlass agents)

        TODO: add 'restart server <server_name>'
        """
        if arg not in RESTART_ARGS:
            print('Invalid argument "{0}"'.format(arg))
            return
        request = 'v2/ui/net/{0}/actions/{1}/reconnect'.format(self.netid, arg)
        response = self.basic_command(request)
        if response is not None:
            self.print_response(response)

    def complete_restart(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, RESTART_ARGS)

    ##########################################################################################
    def do_debug(self, arg):
        """
        Set debug level and optional argument with optional timeout:

        debug level [arg] [time_min]

        Debug level and argument are passed to all servers in the cluster via inter-process message bus.
        Timeout is in minutes. Debug level reverts to its current value and argument
        is erased after timeout. The default timeout is 10 min. If timeout=0, then debug
        level is set indefinitely. Argument can not contain spaces.

        Special debug levels (enter the number as argument 'level', values can be combined with bitwise OR):

        DEBUG_NSGQL                     2
        DEBUG_DATA_POOL                 4
        DEBUG_AGENT_RESPONSES           8
        DEBUG_COMPUTE                  16
        DEBUG_TSDB                     32
        DEBUG_STATUS                   64
        DEBUG_ZOOKEEPER               128
        DEBUG_CACHES                  256
        DEBUG_SOCKET_IO               512
        DEBUG_GRAPH                  1024
        DEBUG_VARS                   2048
        DEBUG_DATA_PUSH              4096
        DEBUG_SYSTEM_EVENTS_AND_HUD  8192
        DEBUG_INDEXER               16384
        DEBUG_MVARS                 32768
        DEBUG_REDIS_EXECUTOR        65536

        """
        if not arg:
            print('Invalid argument "{0}"; see "help debug"'.format(arg))
            return
        # arg can be either just a number or two numbers separated by a space
        try:
            comps = arg.split(' ')
            level = int(comps[0])
            if len(comps) == 1:
                arg = ''
                time = 10
            elif len(comps) == 2:
                arg = ''
                time = int(comps[1])
            elif len(comps) == 3:
                arg = comps[1]
                time = int(comps[2])
            else:
                print('Invalid number of arguments; see "help debug"'.format(arg))
                return
            request = 'v2/nsg/test/net/{0}/debug?level={1}&time={2}&arg={3}'.format(self.netid, level, time, arg)
            response = self.basic_command(request)
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
    def do_server(self, arg):
        """
        Server actions. There is only one action "pause", it forces HA leader to become standby
        """
        if arg not in SERVER_ARGS:
            print('Invalid argument "{0}"'.format(arg))
            return
        request = 'v2/nsg/test/net/{0}/server'.format(self.netid)
        response = self.basic_command(request, data='action={0}'.format(arg))
        if response is not None:
            self.print_response(response)

    def complete_server(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, SERVER_ARGS)

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
        if arg[0] == 'find':
            # this command does not need agent name
            agent_name = 'all'
            work_args = args
        else:
            agent_name = args.pop(0)
            work_args = ' '.join(args)
        if not work_args:
            sub_cmd = agent_commands.AgentCommands(agent_name, self.base_url, self.token, self.netid, region=self.current_region)
            sub_cmd.cmdloop()
        else:
            sub_cmd = agent_commands.AgentCommands(agent_name, self.base_url, self.token, self.netid, region=self.current_region)
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
        sub_cmd = exec_commands.ExecCommands(self.base_url, self.token, self.netid, region=self.current_region)
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
    def do_snmp(self, arg):
        """
        snmp walk .1

        @param arg:   words after 'exec' as one string
        """
        sub_cmd = snmp_commands.SnmpCommands(self.base_url, self.token, self.netid, region=self.current_region)
        if not arg:
            sub_cmd.cmdloop()
        else:
            sub_cmd.onecmd(arg)

    def help_snmp(self):
        sub_cmd = snmp_commands.SnmpCommands(self.base_url, self.token, self.netid, region=self.current_region)
        sub_cmd.help()

    def complete_snmp(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, SNMP_ARGS)

    def basic_command(self, request, data=None):
        """
        execute simple command via API call and return deserialized response
        """
        try:
            response = api.call(self.base_url, 'GET', request, data=data, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            with response:
                status = response.status_code
                if status != 200:
                    for line in response.iter_lines():
                        print('ERROR: {0}'.format(json.loads(line)))
                        return None
                return json.loads(response.content)


def main():
    script = NsgCLI()
    script.parse_args(sys.argv[1:])
    if script.command:
        script.onecmd(script.command)
        sys.exit(0)
    else:
        script.summary()
        # script.prompt = ' > '
        # script.ping()
        script.cmdloop()
