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

import getopt
import getpass
import json
import sys
import time

import nsgcli.api

usage_msg = """
This script can add, update and list alert silences

Usage:

    silence <command> --base-url=url [--token=token] (-n|--network)=netid [-h|--help] (--id=NN) \\
                        --expiration=time (--var_name=name) (--dev_id=id) (--dev_name=name) \\
                        (--index=idx) (--tags=tags_string) (-reason=reason_text)

       command:        Can be 'add', 'update' or 'list'

       --base-url:     server access URL without the path, for example 'http://nsg.domain.com:9100'
                       --base-url must be provided.
       --network:      NetSpyGlass network id (a number, default: 1)
       --id:           silence id, if known (only for the command 'update')
       --expiration:   silence expiration time, minutes
       --key:          alert key to match
       --var_name:     variable name to match
       --dev_id:       device Id to match
       --dev_name:     device name
       --index:        component index to match
       --tags:         a string that represents comma-separated list of tags to match. Tag can be defined either
                       as 'Facet.word' or just 'Facet'. The latter is equivalent to matching 'Facet.*'. Tag
                       can be prepended with '!' to indicate negation - alert matches if it does not have corresponding
                       tag.
       --reason:       argument is a text string that describes the reason this silence is being added
       -h --help:      print this usage summary

    Variable (--var_name) and device name (--dev_name) match supports regular expressions. The whole string
    must match regular expression, that is, we use 'match' rather than 'search'

Commands:

    list   lists all active (that is, not expired yet) silences
    add    add new silence to the system. Parameter --expiration is mandatory and has no default value
    update this command allows the user to update existing silence. Parameter --id is mandatory, the value appears
           in the output of the 'list' command

    To delete existing silence that hasn't expired yet set its expiration time to a small but non-zero value,
    such as 1 min or less. The server expires silences every minute, so this silence will appear in the output
    of the 'list' command until server expires it.

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

    the following command adds silence that matches variable 'busyCpyAlert' for all devices with names that
    match regular expression 'sjc1-rtr-.*'
        silence.py add --var_name='busyCpuAlert' --dev_name='sjc1-rtr-.*'

    override server address and port number settings
        silence.py list --server=10.1.1.1 --port=9101
"""


def usage():
    print(usage_msg)


class InvalidArgsException(Exception):
    pass


class Silence:

    def __init__(self, dd):
        """
        initialize Silence object using data stored in dictionary `dd`

        @param dd:  a dictionary where items correspond to fields of this object, except some fields may have
                    wrong type, e.g. they can be strings where the field is a number
        """
        self.id = dd.get('id', 0)
        self.created_at = float(dd.get('createdAt', 0))
        self.updated_at = float(dd.get('updatedAt', 0))
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

    def get_dict(self):
        silence = {
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


class NetSpyGlassAlertSilenceControl:
    def __init__(self):
        self.command = ''
        self.base_url = ''
        self.token = ''
        self.netid = 1
        self.silence_id = 0
        self.expiration = 0
        self.user = ''
        self.reason = ''
        self.key = ''
        self.var_name = ''
        self.dev_id = 0
        self.dev_name = ''
        self.index = 0
        self.tags = ''
        self.silence_print_format = '{0:^4} | {1:^14} | {2:^24} | {3:^24} | {4:^8} | {5:^40} | {6:^40}'

    def parse_args(self, argv):

        if not argv:
            print('Invalid command: %s ' % self.command)
            raise InvalidArgsException

        self.command = argv[0]
        argv = argv[1:]

        if self.command not in ['add', 'update', 'list']:
            print('Invalid command: %s ' % self.command)
            raise InvalidArgsException

        try:
            opts, args = getopt.getopt(argv,
                                       's:p:n:h',
                                       ['base-url=', 'token=', 'network=', 'id=', 'expiration=',
                                        'key=', 'var_name=', 'dev_id=', 'dev_name=', 'index=',
                                        'tags=', 'reason='])
        except getopt.GetoptError as ex:
            print('UNKNOWN: Invalid Argument:' + str(ex))
            raise InvalidArgsException

        for opt, arg in opts:
            if opt in ['-h', '--help']:
                usage()
                sys.exit(3)
            elif opt in ('-b', '--base-url'):
                self.base_url = arg.rstrip('/ ')
            elif opt in ('-a', '--token'):
                self.token = arg
            elif opt in ['-n', '--network']:
                self.netid = int(arg)
            elif opt in ['--id']:
                self.silence_id = int(arg)
            elif opt in ['--expiration']:
                self.expiration = float(arg)
            elif opt in ['--key']:
                self.key = arg
            elif opt in ['--var_name']:
                self.var_name = arg
            elif opt in ['--dev_id']:
                self.dev_id = arg
            elif opt in ['--dev_name']:
                self.dev_name = arg
            elif opt in ['--index']:
                self.index = arg
            elif opt in ['--tags']:
                self.tags = arg
            elif opt in ['--reason']:
                self.reason = arg

        self.user = getpass.getuser()

        if self.command in ['add'] and self.expiration == 0:
            print('Invalid or undefined expiration time: {0}'.format(self.expiration))
            raise InvalidArgsException

    def assemble_silence_data(self):
        """
        Assemble and return Silence object using data that has been provided on the command line

        :return: Silence object
        """
        silence = Silence({})
        if self.silence_id > 0:
            silence.id = self.silence_id
        silence.expiration_time_ms = self.expiration * 60 * 1000
        silence.key = self.key
        silence.var_name = self.var_name
        silence.device_id = self.dev_id
        silence.device_name = self.dev_name
        silence.index = self.index
        silence.user = self.user
        silence.reason = self.reason

        if self.tags:
            silence.tags = self.tags.split(',')
        else:
            silence.tags = []

        return silence

    def print_silence_header(self):
        print(self.silence_print_format.format('id', 'exp.time, min', 'created', 'updated', 'user', 'reason', 'match'))
        print('{0:-<168}'.format('-'))

    def print_silence(self, silence):
        silence_dict = silence.get_dict()
        id = silence.id
        exp_min = silence.expiration_time_ms / 1000 / 60
        created_at = time.ctime(silence.created_at / 1000)
        updated_at = time.ctime(silence.updated_at / 1000)
        match = silence_dict.get('match', '{}')
        print(self.silence_print_format.format(id, exp_min, created_at, updated_at, silence.user, silence.reason, match))

    def get_data(self, silence_id=None):
        """
        Make NetSpyGlass JSON API call to get all active silences or only silence with given id

        :param silence_id: if of the silence to be retrieved, or None if all active silences should be retrieved
        :return: a tuple (HTTP_STATUS, list) where the second item is list of Silence objects
        """
        request = '/v2/alerts/net/{0}/silences/'.format(self.netid)
        if silence_id is not None and silence_id > 0:
            request += str(silence_id)

        try:
            response = nsgcli.api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            return 503, ex
        else:
            status = response.status_code
            if status != 200:
                return status, response
            else:
                res = []
                for dd in json.loads(response.content):
                    silence = Silence(dd)
                    res.append(silence)
            return response.status_code, res

    def post_data(self, silence):
        """
        Make NetSpyGlass JSON API call to add or update silence

        :param silence:  Silence object
        """
        assert isinstance(silence, Silence)
        request = '/v2/alerts/net/{0}/silences/'.format(self.netid)
        if silence.id is not None and silence.id > 0:
            request += str(silence.id)

        try:
            # serialized = json.dumps(silence.get_dict())
            response = nsgcli.api.call(self.base_url, 'POST', request, token=self.token, data=silence.get_dict())
        except Exception as ex:
            return 503, ex
        else:
            return response.status_code, response.content

    def add(self):
        status, res = self.post_data(self.assemble_silence_data())
        if status == 200:
            print('Silence added successfully')
        elif status == 404:
            print('Network not found, probably network id={0} is invalid. '
                  'Use command line option --network(-n) to set correct network id'.format(self.netid))
        else:
            print(res)

    def update(self):
        status, res = self.get_data(self.silence_id)
        if status == 200:
            if not res:
                print('Silence with id={0} does not exist'.format(self.silence_id))
                return
            existing_silence = res[0]
            assert isinstance(existing_silence, Silence)
            silence = self.assemble_silence_data()
            # update existing silence with new data
            existing_silence.merge(silence)
            self.post_data(existing_silence)
        elif status == 404:
            print('Network not found, probably network id={0} is invalid. '
                  'Use command line option --network(-n) to set correct network id'.format(self.netid))
        else:
            print(res)

    def list(self):
        status, res = self.get_data()
        if status == 200:
            self.print_silence_header()
            for silence in res:
                self.print_silence(silence)
        elif status == 404:
            print('Network not found, probably network id={0} is invalid. '
                  'Use command line option --network(-n) to set correct network id'.format(self.netid))
        else:
            print(res)

    def run(self):
        if self.command in ['add']:
            self.add()
        elif self.command in ['update']:
            self.update()
        elif self.command in ['list']:
            self.list()


def main():
    script = NetSpyGlassAlertSilenceControl()
    try:
        script.parse_args(sys.argv[1:])
        script.run()
    except InvalidArgsException as e:
        usage()
        sys.exit(3)
