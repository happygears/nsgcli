"""
This module sends gnmi commands to the NSG Agent via NSG API server

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""
from nsgcli import api
from nsgcli.agent_commands import HashableAgentCommandResponse
from nsgcli.sseclient import SSEClient
from jsonpath_ng import parse

import base64
import json

APPLICATION_JSON = 'application/json'


class NsgGnmiCommandLine:

    def __init__(self, base_url=None, token=None, netid=1, region='world', xpath=None, timeout_set=180):
        self.base_url = base_url
        self.token = token
        self.netid = netid
        self.timeout_sec = timeout_set
        self.pattern = None
        self.region = region
        self.xpath = xpath

    ##########################################################################################
    def stream(self, command, address, data):
        req = self.compose_gnmi_api_url(address, command)

        headers = {
                'Content-Type': APPLICATION_JSON,
                'X-NSG-Auth-API-Token': self.token
        }

        jsonpath_expr = None
        if self.xpath:
            jsonpath_expr = parse(self.xpath)

        messages = SSEClient(self.base_url + req, data=data, headers=headers)
        for msg in messages:
            if jsonpath_expr:
                for m in jsonpath_expr.find(json.loads(msg.data)['response'][0]):
                    print(m.value)
            else:
                print(json.loads(msg.data))

    ##########################################################################################

    def send(self, command, address, data):
        """
        send command to agents and pick up replies.
        """

        req = self.compose_gnmi_api_url(address, command)

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
                if status == 'ok':
                    replies.append((status, HashableAgentCommandResponse(acr)))
                for status, acr in replies:
                    self.print_agent_response(acr, status, self.xpath)

    def compose_gnmi_api_url(self, address, command):
        GNMI_EXEC_TEMPLATE = '/v2/gnmi/net/{0}/exec/{1}?address={2}&region={3}&agent={4}'
        return GNMI_EXEC_TEMPLATE.format(self.netid, command, address, self.region, "all")
        # GNMI_EXEC_TEMPLATE = '/v2/nsg/cluster/net/{0}/exec/{1}?method={2}&address={3}&region={4}&agent={5}'
        # return GNMI_EXEC_TEMPLATE.format(self.netid, "gnmi", command, address, self.region, "all")

    @staticmethod
    def print_agent_response(acr, status, xpath):
        try:
            if not status or status == 'ok':
                for acr_n in acr['response']:
                    if 'notification' in acr_n:
                        for notification in acr_n['notification']:
                            for update in notification['update']:
                                if 'jsonIetfVal' in update['val']:
                                    update['val']['jsonIetf'] = json.loads(base64.b64decode(update['val'].pop('jsonIetfVal')))

                    if xpath:
                        jsonpath_expr = parse(xpath)
                        for m in jsonpath_expr.find(acr_n):
                            print(m.value)
                    else:
                        print(json.dumps(acr_n, indent=4))
            else:
                print(status)
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
