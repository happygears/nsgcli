"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import datetime
import json

from typing import Dict, Any

import api
import sub_command


class IndexCommands(sub_command.SubCommand, object):
    # prompt = "show # "

    def __init__(self, base_url, token, net_id, region=None):
        super(IndexCommands, self).__init__(base_url, token, net_id)
        self.current_region = region
        if region is None:
            self.prompt = 'index # '
        else:
            self.prompt = '[{0}] index # '.format(self.current_region)

    def completedefault(self, text, _line, _begidx, _endidx):
        return self.get_args(text)

    def help(self):
        print('Various operations on NsgQL indexes. Commands: {0}'.format(self.get_args()))

    ##########################################################################################

    def do_refresh(self, arg):
        """
        Refresh all NsgQL indexes
        """
        request = 'v2/ui/net/{0}/actions/indexes/refresh'.format(self.netid)
        try:
            response = api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            with response:
                status = response.status_code
                if status != 200:
                    print('ERROR: {0}'.format(self.get_error(json.loads(response.content))))
                else:
                    print(response.content)

    def do_drop(self, arg):
        """
        List NsgQL indexes and their cardinality
        """
        request = 'v2/ui/net/{0}/actions/indexes/drop'.format(self.netid)
        try:
            response = api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            with response:
                status = response.status_code
                if status != 200:
                    print('ERROR: {0}'.format(self.get_error(json.loads(response.content))))
                else:
                    print(response.content)

    def do_create(self, arg):
        """
        Create NsgQL index described by the table name and column name with optional function and boolean flag
        to make the index sort in descending order

        index create table_name column_name function_name

        The function is only applicable when column name is equal to 'metric'.

        Supported function names: tslast, tsmin, tsmax

        Examples:

             index create ifInRate ifDescription
             index create ifInRate metric tslast
             index create ifInRate metric tsmax

        """
        request = 'v2/ui/net/{0}/actions/indexes/create'.format(self.netid)
        args = arg.split()
        if len(args) < 2:
            print('ERROR: insufficient arguments for the command. Try "help index create"')
            return
        table = args[0]
        column = args[1]
        nsgql_function = ''
        if len(args) > 2:
            nsgql_function = args[2]
        if nsgql_function not in ['', 'tslast', 'tsmin', 'tsmax']:
            print('ERROR: unsupported function "{0}"'.format(nsgql_function))
            return

        body = {
            'table': table,
            'column': column,
            'function': nsgql_function
        }

        try:
            response = api.call(self.base_url, 'POST', request, token=self.token, data=body)
        except Exception as ex:
            return 503, ex
        else:
            result = ''
            with response:
                status = response.status_code
                response_dict = json.loads(response.content)
                if status != 200:
                    result = 'ERROR: {0}'.format(self.get_error(response_dict))
                else:
                    result = self.get_success(response_dict)
            print('Creating index {0}:{1}:{2} -- {3}'.format(table, column, nsgql_function, result))

    def do_show(self, arg):
        """
        List NsgQL indexes and their cardinality
        """
        request = 'v2/ui/net/{0}/actions/indexes/list'.format(self.netid)
        try:
            response = api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            try:
                resp = json.loads(response.content)
            except Exception as ex:
                print(ex)
                print(response.content)
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
                column_width = {}  # type: Dict[Any, Any]
                for idx in resp:
                    converted = self.convert_obj(idx, ordered_columns)
                    for column_name in ordered_columns:
                        self.update_column_width(converted, column_name, column_width)
                        self.update_column_width(title, column_name, column_width)
                if column_width:
                    # assemble format string
                    table_columns = []
                    for column_name in ordered_columns:
                        table_columns.append('{{0[{0}]:<{1}}}'.format(column_name, column_width.get(column_name)))
                    format_str = ' | '.join(table_columns)
                    title_line = format_str.format(title)
                    print(title_line)
                    print('-' * len(title_line))
                    for idx in resp:
                        converted = self.convert_obj(idx, ordered_columns)
                        print(format_str.format(converted))

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
        w = max(w, len(str(obj.get(column_name, ''))))
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

