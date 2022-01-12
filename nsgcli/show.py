"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import datetime
import dateutil.relativedelta
import json
import time

from typing import Dict, Any

import discovery_commands
import nsgcli.api
import nsgcli.sub_command
import nsgcli.system
import nsgcli.response_formatter


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
        try:
            id = arg.split()[1]
            view_id = int(id)
            request = 'v2/ui/net/{0}/views/{1}/map'.format(self.netid, view_id)
            response = nsgcli.api.call(self.base_url, 'GET', request, token=self.token, stream=True)
        except Exception as ex:
            print(ex)
        else:
            with response:
                status = response.status_code
                if status != 200:
                    print('ERROR: {0}'.format(self.get_error(response)))
                else:
                    # the server does not have proper "export view" API function. Instead, I am using
                    # the output of /status API call with some filtering. This is not suitable for
                    # view export/import
                    try:
                        response = json.loads(response.content)
                    except Exception as e:
                        print(response.content)
                    else:
                        filtered = {}
                        for k in response.keys():
                            if k in ['links', 'nodes', 'path', 'singleUser', 'defaultVar', 'rule', 'linkRule',
                                     'generation']:
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

    ##########################################################################################
    def do_index(self, arg):
        """
        List NsgQL indexes and their cardinality
        """
        request = 'v2/ui/net/{0}/actions/indexes/list'.format(self.netid)
        try:
            response = nsgcli.api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            ordered_columns = ['table', 'column', 'suffix', 'type', 'cardinality', 'redisKey', 'updatedAt']
            title = {'table': 'table',
                     'column': 'column',
                     'suffix': 'ext',
                     'redisKey': 'redis',
                     'type': 'type',
                     'cardinality': 'cardinality',
                     'updatedAt': 'updatedAt'
                     }
            resp = json.loads(response.content)
            column_width = {}  # type: Dict[Any, Any]
            for column_name in title.keys():
                self.update_column_width(title, column_name, column_width)
            for row in resp:
                converted = self.convert_obj(row, ordered_columns)
                for column_name in ordered_columns:
                    self.update_column_width(converted, column_name, column_width)
            # assemble format string
            table_columns = []
            for column_name in ordered_columns:
                table_columns.append('{{0[{0}]:<{1}}}'.format(column_name, column_width.get(column_name)))
            format_str = u' | '.join(table_columns)
            title_line = format_str.format(title)
            print(title_line)
            print('-' * len(title_line))
            counter = 0
            for row in resp:
                converted = self.convert_obj(row, ordered_columns)
                print(format_str.format(converted))
                counter += 1
            print('-' * len(title_line))
            print('Total: {}'.format(counter))

    def convert_obj(self, obj, columns):
        new_obj = obj.copy()
        # fill in required columns that may be missing in the object
        for col in columns:
            if col not in new_obj:
                new_obj[col] = ''
        updated_at = int(obj['updatedAt'])
        if updated_at == 0:
            new_obj['updatedAt'] = '--'
        else:
            new_obj['updatedAt'] = self.convert_updated_at(updated_at) + ' ago'
        return new_obj

    def convert_updated_at(self, updated_at_ms):
        updated_at_sec = float(updated_at_ms) / 1000.0
        value = datetime.datetime.fromtimestamp(updated_at_sec)
        delta = datetime.datetime.now() - value
        return str(delta - datetime.timedelta(microseconds=delta.microseconds))

    def update_column_width(self, obj, column_name, col_wid_dict):
        w = col_wid_dict.get(column_name, 0)
        txt = unicode(obj.get(column_name, ''))
        w = max(w, len(txt))
        col_wid_dict[column_name] = w

    def parse_index_key(self, index_key):
        """
        parse index key and return table, column and suffix

        currently recognized format is

        table:column[.suffix]
        """
        first_colon = index_key.find(':')
        if first_colon < 0:
            return '', '', ''
        table = index_key[0: first_colon]
        last_dot = index_key.rfind('.')
        if last_dot < 0:
            column = index_key[first_colon + 1:]
            suffix = ''
        else:
            column = index_key[first_colon + 1: last_dot]
            suffix = index_key[last_dot + 1:]
        return table, column, suffix

    ##########################################################################################
    def do_device(self, arg):
        """
        Inspect device identified by its device Id

        show device device_id [field][,field...]

        Examples:

            show device 159
            show device 159 tags
            show device 159 id,generation,boxDescr,tags
        """
        if not arg:
            print('ERROR: at least one argument (device id) is required')
            return
        arg_list = arg.split()
        dev_id = arg_list[0]

        if len(arg_list) > 1:
            fields = arg_list[1].split(',')
        else:
            fields = None

        request = 'v2/ui/net/{0}/devices/{1}'.format(self.netid, dev_id)
        try:
            response = nsgcli.api.call(self.base_url, 'GET', request, data={'action': 'status'}, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            status = response.status_code
            if status != 200:
                print(self.get_error(json.loads(response.content)))
            else:
                # resp_dict = json.loads(response.content)
                dev = json.loads(response.content)
                if fields is not None:
                    print(json.dumps({x: dev.get(x, {}) for x in fields}, indent=4))
                else:
                    print(json.dumps(dev, indent=4))
