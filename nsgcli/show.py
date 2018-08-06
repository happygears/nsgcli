"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import datetime
import json
import time

import nsgcli.api
import nsgcli.sub_command
import nsgcli.system


class ShowCommands(nsgcli.sub_command.SubCommand, object):
    # prompt = "show # "

    def __init__(self, base_url, token, net_id, region=None):
        super(ShowCommands, self).__init__(base_url, token, net_id)
        self.system_commands = nsgcli.system.SystemCommands(self.base_url, self.token, self.netid, region=region)
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
        try:
            response = nsgcli.api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            with response:
                status = response.status_code
                for acr in nsgcli.api.transform_remote_command_response_stream(response):
                    return status, acr

    ##########################################################################################
    def do_version(self, args):
        """
        Print software version
        """
        status, response = self.get_status()
        if status != 200:
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            response = response[0]
            print(response['version'])

    ##########################################################################################
    def do_uuid(self, args):
        """
        Print NSG cluster uuid
        """
        status, response = self.get_status()
        if status != 200:
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            response = response[0]
            print(response['uuid'])

    ##########################################################################################
    def do_cache(self, arg):
        """
        List contents of the long- and short-term NsgQL cache
        """
        request = 'v2/ui/net/{0}/actions/cache/list'.format(self.netid)
        try:
            response = nsgcli.api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            with response:
                status = response.status_code
                if status != 200:
                    print('ERROR: {0}'.format(self.get_error(response)))
                else:
                    response = json.loads(response.content)
                    print(json.dumps(response, indent=4))

    ##########################################################################################
    def do_server(self, arg):
        """
        Print server status
        """
        request = 'v2/nsg/test/net/{0}/server'.format(self.netid)
        try:
            response = nsgcli.api.call(self.base_url, 'GET', request, data={'action': 'status'}, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            with response:
                status = response.status_code
                if status != 200:
                    print('ERROR: {0}'.format(self.get_error(response)))
                else:
                    response = json.loads(response.content)
                    print(json.dumps(response, indent=4))

    ##########################################################################################
    def do_status(self, _):
        """
        Request server status
        """
        status, response = self.get_status()
        if status != 200:
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
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

    ##########################################################################################
    def do_views(self, arg):
        """
        Show map views defined in the system.
        Examples:
            show views          -- list all views defined in the system
            show views id NNN   -- prints parameters that define the view with id=NNNN.
                                   This data can not be used to export/import views at this time.
        """
        if not arg:
            self.list_views()
            return
        if arg[0:2] != 'id':
            print('Unknown keyword "{0}"; expected "show view id N"'.format(arg))
            return
        # arg must be view Id
        id = arg.split()[1]
        view_id = int(id)
        request = 'v2/ui/net/{0}/views/{1}/map'.format(self.netid, view_id)
        try:
            response = nsgcli.api.call(self.base_url, 'GET', request, token=self.token, stream=True)
        except Exception as ex:
            return 503, ex
        else:
            with response:
                status = response.status_code
                if status != 200:
                    print('ERROR: {0}'.format(self.get_error(response)))
                else:
                    # the server does not have proper "export view" API function. Instead, I am using
                    # the output of /status API call with some filtering. This is not suitable for
                    # view export/import
                    response = json.loads(response.content)
                    filtered = {}
                    for k in response.keys():
                        if k in ['links', 'nodes', 'path', 'singleUser', 'defaultVar', 'rule', 'linkRule', 'generation']:
                            continue
                        filtered[k] = response[k]
                    print(json.dumps(filtered, indent=4))
                    # print(response['formData'])

    def list_views(self):
        """
        API call status returns a dictionary that has an item 'status' with value that is
        also a dictionary. This makes parsing response harder
        """
        status, response = self.get_status()
        # print(response)
        if status != 200:
            print('ERROR: {0}'.format(self.get_error(response)))
        else:
            format = '{0[id]:<4} {0[name]:<32} {0[type]:<12} {1:<20}'
            header = {'id': 'id', 'name': 'name', 'type': 'type'}
            print(format.format(header, 'updated_at'))
            print('-' * 60)
            for view in response[0]['views']:
                updated_at = self.transform_value('updatedAt', view['updatedAt'])
                print(format.format(view, updated_at))

    def transform_value(self, field_name, value, outdated=False):
        if field_name in ['updatedAt', 'localTimeMs']:
            updated_at_sec = float(value) / 1000
            value = datetime.datetime.fromtimestamp(updated_at_sec)
            suffix = ''
            if outdated and time.time() - updated_at_sec > 15:
                suffix = ' outdated'
            return value.strftime('%Y-%m-%d %H:%M:%S') + suffix
        return value
