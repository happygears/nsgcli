"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import json

import nsgcli.api
import nsgcli.response_formatter
import nsgcli.sub_command
import nsgcli.system
from . import discovery_commands


class ShowCommands(nsgcli.sub_command.SubCommand, object):
    # prompt = "show # "

    def __init__(self, base_url, token, net_id, time_format=nsgcli.response_formatter.TIME_FORMAT_MS, region=None):
        super(ShowCommands, self).__init__(base_url, token, net_id)
        self.system_commands = nsgcli.system.SystemCommands(
            self.base_url, self.token, self.netid, time_format=time_format, region=region)
        self.current_region = region
        if region is None:
            self.prompt = 'show # '
        else:
            self.prompt = 'show [' + self.current_region + '] # '

    def completedefault(self, text, _line, _begidx, _endidx):
        # _line='show system' if user hits Tab after "show system"
        # this method is not called when user enters "show system" context and hits Tab then
        # print('ShowCommands.completedefault text=' + text + ', _line=' + _line)
        if _line and ' system' in _line:
            return self.complete_system(text, _line, _begidx, _endidx)
        else:
            return self.get_args(text)

    def help(self):
        print('Show various server parameters and state variables. Arguments: {0}'.format(self.get_args()))

    def get_status(self):
        request = 'v2/ui/net/{0}/status'.format(self.netid)
        return nsgcli.api.call(self.base_url, 'GET', request, token=self.token, response_format='json')

    def get_cache_data(self):
        """
        make API call /v2/ui/net/{0}/actions/cache/list and return the response
        as a tuple (http_code,json)
        """
        request = 'v2/ui/net/{0}/actions/cache/list'.format(self.netid)
        return nsgcli.api.call(self.base_url, 'GET', request, token=self.token, response_format='json')

    ##########################################################################################
    def do_version(self, args):
        """
        Print software version
        """
        response, error = self.get_status()
        if error is None:
            response = response[0]
            print(response['version'])

    ##########################################################################################
    def do_uuid(self, args):
        """
        Print NSG cluster uuid
        """
        response, error = self.get_status()
        if error is None:
            response = response[0]
            print(response['uuid'])

    ##########################################################################################
    def do_discovery(self, arg):
        """
        show discovery status
        """
        sub_cmd = discovery_commands.DiscoveryCommands(self.base_url, self.token, self.netid, None)
        sub_cmd.do_queue(arg)

    ##########################################################################################
    def do_status(self, _):
        """
        Request server status
        """
        response, error = self.get_status()
        if error is None:
            response = response[0]
            print(json.dumps(response, indent=4))

    ##########################################################################################
    def do_system(self, arg):
        if arg:
            self.system_commands.onecmd(arg)
        else:
            self.system_commands.cmdloop()

    def help_system(self):
        return self.system_commands.help()

    def complete_system(self, text, _line, _begidx, _endidx):
        return self.system_commands.completedefault(text, _line, _begidx, _endidx)
