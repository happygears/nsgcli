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
            return 200, json.loads(response.content)

    def get_cache_data(self):
        """
        make API call /v2/ui/net/{0}/actions/cache/list and return the response
        as a tuple (http_code,json)
        """
        request = 'v2/ui/net/{0}/actions/cache/list'.format(self.netid)
        try:
            response = nsgcli.api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            return 200, json.loads(response.content)

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
        status, resp_json = self.get_cache_data()
        if status != 200:
            print('ERROR: {0}'.format(self.get_error(resp_json)))
        else:
            print(json.dumps(resp_json, indent=4))

    ##########################################################################################
    def do_index(self, arg):
        """
        List NsgQL indexes and their cardinality
        """
        status, resp_json = self.get_cache_data()
        if status != 200:
            print('ERROR: {0}'.format(self.get_error(resp_json)))
        else:
            indexes = resp_json[0].get('INDEXES', {})
            format = '{0:<40} | {1:<20} | {2:<10} | {3:<5} | {4}'
            print(format.format('index', 'table', 'column', 'ext', 'cardinality'))
            print('----------------------------------------------------------------------------------------------------')
            for index_key in sorted(indexes.keys()):
                table, column, suffix = self.parse_index_key(index_key)
                print(format.format(index_key, table, column, suffix, indexes[index_key]))

    def parse_index_key(self, index_key):
        """
        parse index key and return table, column and suffix

        currently recognized format is

        table:column[.suffix]
        """
        first_colon = index_key.find(':')
        if first_colon < 0:
            return '', '', ''
        table = index_key[0 : first_colon]
        last_dot = index_key.rfind('.')
        if last_dot < 0:
            column = index_key[first_colon + 1:]
            suffix = ''
        else:
            column = index_key[first_colon + 1: last_dot]
            suffix = index_key[last_dot + 1:]
        return table, column, suffix

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
            status = response.status_code
            if status != 200:
                print('ERROR: {0}'.format(self.get_error(response)))
            else:
                resp_dict = json.loads(response.content)
                if 'success' in resp_dict:
                    d = resp_dict.get('success', {})
                    if isinstance(d, dict):
                        resp_dict = d
                    else:
                        resp_dict = json.loads(d)
                for key in sorted(resp_dict.keys()):
                    if key == 'HA':
                        continue
                    print('{0:<8} :   {1}'.format(key, resp_dict.get(key, '')))

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
