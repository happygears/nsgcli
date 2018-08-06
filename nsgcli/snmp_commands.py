"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import json
import types

import nsgcli.api

SNMP_RESPONSE_FORMAT = """
Source:   {m[agent]} ({m[agentAddress]})
Status:   {m[status]}
"""

SNMP_TEMPLATE_WITHOUT_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?address={2}&oid={3}&timeout={4}'
SNMP_TEMPLATE_WITH_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?address={2}&oid={3}&timeout={4}&region={5}'


def snmp_get(base_url, netid, token, args, region=None):
    """
    Execute snmp GET command using agents in the currently selected region

    snmp_get <address> oid1  [timeout_sec]
    """
    snmp_command(base_url, netid, 'snmpget', token, args, region)


def snmp_walk(base_url, netid, token, args, region=None):
    """
    Execute snmp WALK command using agents in the currently selected region

    snmp_walk <address> oid1 [timeout_sec]
    """
    snmp_command(base_url, netid, 'snmpwalk', token, args, region)


def snmp_command(base_url, netid, command, token, args, region):
    """
    snmp_get <address> oid1 [timeout_sec]
    snmp_walk <address> oid [timeout_sec]
    """
    address = args[0]
    oid = args[1]
    timeout_sec = 2
    if len(args) > 2:
        timeout_sec = int(args[2])

    if region is None:
        req = SNMP_TEMPLATE_WITHOUT_REGION.format(netid, command, address, oid, timeout_sec)
    else:
        req = SNMP_TEMPLATE_WITH_REGION.format(netid, command, address, oid, timeout_sec, region)
    # This call returns list of AgentCommandResponse objects in json format
    try:
        response = nsgcli.api.call(base_url, 'GET', req, token=token, stream=True, timeout=300)
    except Exception as ex:
        return 503, ex
    else:
        with response:
            status = response.status_code
            if status != 200:
                for line in response.iter_lines():
                    print('ERROR: {0}'.format(get_error(json.loads(line))))
                    return
            for acr in nsgcli.api.transform_remote_command_response_stream(response):
                # pass
                # print(acr)
                status = parse_status(acr)
                print_snmp_response(acr, status)


def print_snmp_response(acr, status):
    try:
        for line in acr['response']:
            print('{0} | {1}'.format(acr['agent'], line))
    except Exception as e:
        print(e)
        print(acr)


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


def get_error(response):
    if isinstance(response, types.ListType):
        return self.get_error(response[0])
    if isinstance(response, types.UnicodeType) or isinstance(response, types.StringType):
        return response
    return response.get('error', '')
