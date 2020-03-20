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

import email
import json
import time
import types
import nsgcli.api


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


class NetSpyGlassAlertSilenceControl:
    def __init__(self, base_url='', token='', netid=1, silence_id=0, expiration=0, user='', reason='',
                 key='', var_name='', dev_id=0, dev_name='', index=0, tags='', start_time=0):
        self.base_url = base_url
        self.token = token
        self.netid = netid
        self.silence_id = silence_id
        self.expiration = expiration
        self.user = user
        self.reason = reason
        self.key = key
        self.var_name = var_name
        self.dev_id = dev_id
        self.dev_name = dev_name
        self.index = index
        self.tags = tags
        self.start_time = start_time
        self.silence_print_format = '{0:^4} | {1:^32} | {2:^14} | {3:^8} | {4:^40} | {5:^32} | {6:^32} | {7:^40}'

    def assemble_silence_data(self):
        """
        Assemble and return Silence object using data that has been provided on the command line

        :return: Silence object
        """
        silence = Silence({})
        if self.silence_id > 0:
            silence.id = self.silence_id
        silence.start_time_ms = self.start_time * 1000
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
        print(self.silence_print_format.format('id', 'start', 'exp.time, min', 'user', 'reason', 'created', 'updated', 'match'))
        print('{0:-<200}'.format('-'))

    def print_silence(self, silence):
        silence_dict = silence.get_dict()
        id = silence.id
        start_time = email.utils.formatdate(silence.start_time_ms / 1000, localtime=True)
        exp_min = silence.expiration_time_ms / 1000 / 60
        created_at = email.utils.formatdate(silence.created_at / 1000, localtime=True)
        updated_at = email.utils.formatdate(silence.updated_at / 1000, localtime=True)
        match = silence_dict.get('match', '{}')
        print(self.silence_print_format.format(id, start_time, exp_min, silence.user, silence.reason, created_at, updated_at, match))

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
            response = json.loads(res)
            self.print_silence_header()
            self.print_silence(Silence(response[0]))
            # print('Silence added successfully: id={0}'.format(response.get('id', 'unknown')))
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
            self.update_silence(existing_silence)
        elif status == 404:
            print('Network not found, probably network id={0} is invalid. '
                  'Use command line option --network(-n) to set correct network id'.format(self.netid))
        else:
            print(res)

    def update_silence(self, existing_silence):
        silence = self.assemble_silence_data()
        # update existing silence with new data
        existing_silence.merge(silence)
        status, res = self.post_data(existing_silence)
        if status == 200:
            response = json.loads(res)
            self.print_silence_header()
            self.print_silence(Silence(response[0]))
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

    def run(self, command):
        if command in ['add']:
            self.add()
        elif command in ['update']:
            self.update()
        elif command in ['list']:
            self.list()
        else:
            print('Unknown command "{0}"'.format(command))
