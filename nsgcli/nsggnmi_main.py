"""
This module sends gnmi commands to the NSG Agent via NSG API server

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""
from nsgcli import api
from nsgcli.agent_commands import HashableAgentCommandResponse
from nsgcli.sseclient import SSEClient

import base64
import json

APPLICATION_JSON = 'application/json'

GNMI_EXEC_TEMPLATE = '/v2/nsg/cluster/net/{0}/exec/{1}?method={2}&address={3}&region={4}&agent={5}'


class NsgGnmiCommandLine:

    def __init__(self, base_url=None, token=None, netid=1, region='world', timeout_set=180):
        self.base_url = base_url
        self.token = token
        self.netid = netid
        self.timeout_sec = timeout_set
        self.pattern = None
        self.region = region

    ##########################################################################################
    def stream(self, command, address, data):
        req = GNMI_EXEC_TEMPLATE.format(self.netid, "gnmi", command, address, self.region, "all")

        headers = {'Content-Type': APPLICATION_JSON, 'X-NSG-Auth-API-Token': self.token}

        messages = SSEClient(self.base_url + req, data=data, headers=headers)
        for msg in messages:
            print(msg)

    ##########################################################################################

    def send(self, command, address, data, hide_errors=True, deduplicate_replies=True):
        """
        send command to agents and pick up replies. If hide_errors=True, only successful
        replies are printed, otherwise all replies are printed.

        If deduplicate_replies=True, duplicate replies are suppressed (e.g. when multiple agents
        reply)
        """

        req = GNMI_EXEC_TEMPLATE.format(self.netid, "gnmi", command, address, self.region, "all")

        headers = {'Content-Type': APPLICATION_JSON, 'Accept': APPLICATION_JSON}
        response, error = api.call(self.base_url,
                                   'POST',
                                   req,
                                   data=data,
                                   token=self.token,
                                   headers=headers,
                                   stream=True,
                                   response_format='json_array',
                                   error_format='json_array',
                                   timeout=180)

        if error is None:
            replies = []
            for acr in response:
                status = self.parse_status(acr)
                if not hide_errors or status == 'ok':
                    replies.append((status, HashableAgentCommandResponse(acr)))
            if deduplicate_replies:
                for status, acr in set(replies):
                    self.print_agent_response(acr, status)
            else:
                for status, acr in replies:
                    self.print_agent_response(acr, status)

    @staticmethod
    def print_agent_response(acr, status):
        try:
            if not status or status == 'ok':
                for line in acr['response']:
                    acr_json = json.loads(line)
                    for notification in acr_json['notification']:
                        for update in notification['update']:
                            if 'jsonIetfVal' in update['val']:
                                update['val']['jsonIetf'] = json.loads(base64.b64decode(update['val'].pop('jsonIetfVal')))

                    print('{0} | {1}'.format(acr['agent'], json.dumps(acr_json, indent=4)))
            else:
                print('{0} | {1}'.format(acr['agent'], status))
        except Exception as e:
            print(e)
            print(acr)

    @staticmethod
    def parse_status(acr):
        try:
            ec = acr['exitStatus']
            if ec == 0:
                status = 'ok'
            elif 'error' in acr:
                status = acr['error']
            elif ec == -1:
                status = 'could not find and execute the command'
            else:
                status = 'unknown error'
            return status
        except Exception as e:
            print('Can not parse status in "{0}"'.format(acr))
            return 'unknown'


class InvalidArgsException(Exception):
    pass
