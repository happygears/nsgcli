"""
This module is part of the nsgcli package

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.
"""

from __future__ import print_function

import datetime
import numbers
import time


MEMORY_VALUE_FIELDS = ['fsFreeSpace', 'fsTotalSpace', 'systemMemTotal',
                       'jvmMemFree', 'jvmMemMax', 'jvmMemTotal', 'jvmMemUsed',
                       'redisUsedMemory', 'redisMaxMemory']

PERCENTAGE_VALUE_FIELDS = ['cpuUsage', 'systemMemFreePercent', 'fsUtil']

TIME_FORMAT_MS = 'ms'
TIME_FORMAT_ISO_UTC = 'iso_utc'
TIME_FORMAT_ISO_LOCAL = 'iso_local'


def sizeof_fmt(num, suffix='B'):
    if not num:
        return ''
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.3f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return '%.3f %s%s' % (num, 'Y', suffix)


def percentage_fmt(num):
    return '%.2f %%' % num


class ResponseFormatter(object):
    def __init__(self, time_format=TIME_FORMAT_MS):
        super(ResponseFormatter, self).__init__()
        self.header_divider = '-+-'
        self.cell_divider = ' | '
        self.time_format = time_format

    def print_result_as_table(self, resp):
        columns = []  # e.g.:   [{u'text': u'device'}]
        for col in resp.get('columns'):
            columns.append(self.transform_column_title(col['text']))

        rows = resp.get('rows', [])
        widths = {}
        col_num = 0
        for col in columns:
            widths[col_num] = len(col)
            col_num += 1
        for row in rows:
            el_count = 0
            for element in row:
                element = self.transform_value(columns[el_count], element)
                element = str(element).rstrip()
                w = widths.get(el_count, 0)
                if len(element) > w:
                    widths[el_count] = len(element)
                el_count += 1
        total_width = 0
        formatted_column_titles = []
        self.print_table_header_separator(widths)
        for idx in range(0, len(widths)):
            form = '{0:' + str(widths[idx]) + '}'
            col_txt = form.format(columns[idx])
            formatted_column_titles.append(col_txt)
            total_width += len(col_txt)
        print(self.cell_divider.join(formatted_column_titles))
        self.print_table_header_separator(widths)
        if rows:
            for row in rows:
                row_elements = []
                for idx in range(0, len(widths)):
                    form = '{0:' + str(widths[idx]) + '}'
                    element = self.transform_value(columns[idx], row[idx])
                    row_txt = form.format(element)
                    row_elements.append(row_txt)
                print(self.cell_divider.join(row_elements))
            self.print_table_header_separator(widths)
        processing_time_sec = resp.get('processingTimeMs', 0) / 1000.0
        print('Count: {0}, served by: {1}, processing time: {2} sec; query id: {3}'.format(
            len(rows), resp.get('server', 'unknown'), processing_time_sec, resp.get('queryId', 0)))
        print('')

    def print_table_header_separator(self, widths):
        header_parts = []
        for idx in range(0, len(widths)):
            header_parts.append('-' * widths[idx])
        print(self.header_divider.join(header_parts))

    def transform_column_title(self, column):
        if column == 'time':
            if self.time_format == TIME_FORMAT_ISO_UTC:
                return column + ' (utc)'
            elif self.time_format == TIME_FORMAT_ISO_LOCAL:
                return column + ' (local)'
            else:
                return column
        else:
            return column

    def transform_value(self, field_name, value, outdated=False):
        if field_name in ['updatedAt', 'accessedAt', 'localTimeMs']:
            updated_at_sec = float(value) / 1000
            value = datetime.datetime.fromtimestamp(updated_at_sec)
            suffix = ''
            if outdated and time.time() - updated_at_sec > 15:
                suffix = ' outdated'
            return value.strftime('%Y-%m-%d %H:%M:%S') + suffix

        if field_name in ['systemUptime', 'processUptime']:
            td = datetime.timedelta(0, float(value))
            return str(td)

        if field_name.find('time') == 0:
            if self.time_format == TIME_FORMAT_ISO_UTC:
                value = datetime.datetime.utcfromtimestamp(float(value) / 1000.0)
                return value.isoformat(' ')
            elif self.time_format == TIME_FORMAT_ISO_LOCAL:
                time_as_dt = datetime.datetime.fromtimestamp(float(value) / 1000.0)
                return time_as_dt.isoformat(' ')
            else:
                return value

        # if field_name == 'cpuUsage':
        #     return value + ' %'

        if field_name in MEMORY_VALUE_FIELDS and value and isinstance(value, numbers.Number):
            return sizeof_fmt(float(value))

        if field_name in PERCENTAGE_VALUE_FIELDS and value and isinstance(value, numbers.Number):
            return percentage_fmt(float(value))
        return value

