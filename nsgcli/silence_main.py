#!/usr/bin/python
#
# Copyright 2015 HappyGears
#
# Author: vadim@happygears.net
#
# silence.py - version 1.0
#
# alert silence manipulation script
#
#
from getpass import getpass

import click
import os
import json
import dateutil.parser
from email.utils import formatdate

from nsgcli.api import API


@click.group()
@click.option('--base-url',
              help="http://HOST:PORT of your NSG cluster API endpoint (defaults to $NSG_SERVICE_URL)",
              default=os.getenv('NSG_SERVICE_URL'))
@click.option('--network', default='1', help="Network ID. 1 is usually correct")
@click.option('--token', help="API token for access to NSG cluster")
@click.option('--id', help="Silence ID, if known (used for update command)", type=click.INT)
@click.option('--start',
              help="""
silence should start on this date and time. Various input formats are supported,
examples: '2020-03-20 10:00:00' (no time zone) or 'March 20 2020 10:00:00 -0700' (with 
time zone). See Python module `dateutil` for the detailed list of supported formats. 
You can set the time zone, but if it is not specified, the time is assumed to be in local 
time zone. If this parameter is not provided, the start time of the silence is "now". If 
specified, the start time can be both in the future and in the past.""")
@click.option('--expiration',
              help="""
silence expiration time, minutes. The silence stops at the time calculated as the start time plus expiration time.""")
@click.option('--key', help='alert key to match')
@click.option('--var_name', help='variable name to match')
@click.option('--dev_id', help='device ID to match')
@click.option('--dev_name', help='device name to match')
@click.option('--index', help='component index to match')
@click.option('--tags',
              help="""
a string that represents comma-separated list of tags to match. Tag can be defined either
as 'Facet.word' or just 'Facet'. The latter is equivalent to matching 'Facet.*'. Tag
can be prepended with '!' to indicate negation - alert matches if it does not have corresponding
tag.""")
@click.option('--reason', help="argument is a text string that describes the reason this silence is being added")
@click.pass_context
def silence(ctx: click.Context, base_url, network, token, id, start, expiration,
            key, var_name, dev_id, dev_name, index, tags, reason) -> None:
    """
    This script can add, update and list alert silences

    Examples:

        the following command adds silence for alert 'busyCpuAlert' for device with id 212, any component and any tags:
            silence.py add --var_name='busyCpuAlert' --dev_id=212

        match alert by name and tag, for example silence all alerts for servers that belong to hbase cluster 'hbase0'
        except those marked 'important':
            silence.py add --var_name='busyCpuAlert' --tags='Explicit.hbase0, !Explicit.important'

        use this command to list active silences:
            silence.py list

        The output looks like this:
             id  | exp.time, min  |         created          |         updated          |                  match
            ------------------------------------------------------------------------------------------------------------------------
             8   |      60.0      | Mon Jun  8 19:50:15 2015 | Mon Jun  8 19:50:15 2015 | {u'varName': u'busyCpuAlert', u'tags': [], u'deviceId': 131, u'index': 0}

        use this command to update expiration time on the existing silence (use silence Id returned by the 'list' command):
            silence.py update --id=8 --expiration=120

        use the following command to add silence that matches all alerts regardgess of their name, device,
        component and tags (a 'catch all' silence):
            silence.py add --var_name='.*'

        use the following command to add silence that matches all alerts for given device
            silence.py add --var_name='.*' --dev_id=212

        specify start time with time zone:
            silence.py add --start='2020-04-01 00:00:00 -0800' --var_name='.*' --dev_id=212

        the following command adds silence that matches variable 'busyCpyAlert' for all devices with names that
        match regular expression 'sjc1-rtr-.*'
            silence.py add --var_name='busyCpuAlert' --dev_name='sjc1-rtr-.*'

        override server address and port number settings
            silence.py list --server=10.1.1.1 --port=9101
    """
    ctx.obj['api'] = API(base_url=base_url.rstrip('/ '), network=network, token=token)
    ctx.obj['args'] = {
        'id': id,
        'start_time_ms': dateutil.parser.parse(start).timestamp() * 1000,
        'expiration_ms': expiration * 60 * 1000,
        'key': key,
        'var_name': var_name,
        'dev_id': dev_id,
        'dev_name': dev_name,
        'index': index,
        'tags': tags,
        'reason': reason,
        'user': getpass.getuser()
    }


@silence.command()
@click.pass_context
def add(ctx: click.Context):
    s = ctx.obj['api'].update_silence(Silence.from_arguments(ctx.obj['args']))
    s.print_silence_header()
    s.print_silence()


@silence.command()
@click.pass_context
def update(ctx: click.Context):
    api: API = ctx.obj['api']
    args: dict = ctx.obj['args']
    existing_silence = api.get_silence(args['id'])
    updater = Silence.from_arguments(args)
    existing_silence.merge(updater)
    api.update_silence(existing_silence)
    existing_silence.print_silence_header()
    existing_silence.print_silence()

@silence.command()
@click.pass_context
def list(ctx: click.Context):
    api: API = ctx.obj['api']
    Silence.print_silence_header()
    for s in api.get_silences():
        s.print_silence()


class Silence:

    SILENCE_PRINT_FORMAT = '{0:^4} | {1:^32} | {2:^14} | {3:^8} | {4:^40} | {5:^32} | {6:^32} | {7:^40}'

    def __init__(self, dd):
        """
        initialize Silence object using data stored in dictionary `dd`

        @param dd:  a dictionary where items correspond to fields of this object, except some fields may have
                    wrong type, e.g. they can be strings where the field is a number
        """
        self.id = dd.get('id', 0)
        self.created_at = float(dd.get('createdAt', 0))
        self.updated_at = float(dd.get('updatedAt', 0))
        self.start_time_ms = int(dd.get('startsAt', 0))
        self.expiration_time_ms = float(dd.get('expirationTimeMs', 0))
        match = dd.get('match', {})
        self.key = match.get('key')
        self.var_name = match.get('varName', '')
        self.device_id = match.get('deviceId', 0)
        self.device_name = match.get('deviceName', '')
        self.index = match.get('index', 0)
        self.user = dd.get('user', '')
        self.reason = dd.get('reason', '')
        tags_str = match.get('tags', '')
        if tags_str:
            self.tags = tags_str
        else:
            self.tags = []

    # NB: we can stop quoting the return type here after Python 3.10,
    # or we could import 'annotations' from __future__

    @staticmethod
    def from_arguments(d: dict) -> 'Silence':
        """
        Assemble and return Silence object using data that has been provided on the command line

        :return: Silence object
        """
        silence = Silence({})
        if d['id'] > 0:
            silence.id = d['id']
        silence.start_time_ms = d['start_time_ms']
        silence.expiration_time_ms = d['expiration_ms']
        silence.key = d['key']
        silence.var_name = d['var_name']
        silence.device_id = d['dev_id']
        silence.device_name = d['dev_name']
        silence.index = d['index']
        silence.user = d['user']
        silence.reason = d['reason']

        if d['tags']:
            silence.tags = d['tags'].split(',')
        else:
            silence.tags = []

        return silence

    def get_dict(self):
        silence = {
            'startsAt': self.start_time_ms,
            'expirationTimeMs': self.expiration_time_ms,
            'user': self.user,
            'reason': self.reason,
            'match': {
                'key': self.key,
                'varName': self.var_name,
                'deviceId': self.device_id,
                'deviceName': self.device_name,
                'index': self.index,
            }
        }
        silence['match']['tags'] = self.tags
        if self.id > 0:
            silence['id'] = self.id
        return silence

    def merge(self, other):
        if other.id != 0:
            self.id = other.id
        if other.start_time_ms > 0:
            self.start_time_ms = other.start_time_ms
        if other.expiration_time_ms > 0:
            self.expiration_time_ms = other.expiration_time_ms
        if other.key != '':
            self.key = other.key
        if other.var_name != '':
            self.var_name = other.var_name
        if other.device_id != 0:
            self.device_id = other.device_id
        if other.device_name != '':
            self.device_name = other.device_name
        if other.index != 0:
            self.index = other.index
        if other.tags:
            self.tags = other.tags
        if other.user:
            self.user = other.user
        if other.reason:
            self.reason = other.reason

    @staticmethod
    def print_silence_header():
        print(Silence.SILENCE_PRINT_FORMAT.format('id', 'start', 'exp.time, min', 'user', 'reason', 'created',
                                                  'updated', 'match'))
        print('{0:-<200}'.format('-'))

    def print_silence(self):
        silence_dict = self.get_dict()
        start_time = formatdate(silence.start_time_ms / 1000, localtime=True)
        exp_min = silence.expiration_time_ms / 1000 / 60
        created_at = formatdate(silence.created_at / 1000, localtime=True)
        updated_at = formatdate(silence.updated_at / 1000, localtime=True)
        match = silence_dict.get('match', '{}')
        print(self.SILENCE_PRINT_FORMAT.format(self.id, start_time, exp_min, self.user, self.reason, created_at,
                                               updated_at, match))