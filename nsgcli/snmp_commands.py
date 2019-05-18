"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import json
import types

import api
import sub_command
import system

SNMP_RESPONSE_FORMAT = """
Source:   {m[agent]} ({m[agentAddress]})
Status:   {m[status]}
"""

SNMP_TEMPLATE_WITHOUT_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?address={2}&oid={3}&timeout={4}'
SNMP_TEMPLATE_WITH_REGION = 'v2/nsg/cluster/net/{0}/exec/{1}?address={2}&oid={3}&timeout={4}&region={5}'


class SnmpCommands(sub_command.SubCommand, object):
    # prompt = "exec # "

    def __init__(self, base_url, token, net_id, region=None):
        super(SnmpCommands, self).__init__(base_url, token, net_id, region=region)
        self.current_region = region
        self.system_commands = system.SystemCommands(self.base_url, self.token, self.netid, region=region)
        if region is None:
            self.prompt = 'snmp # '
        else:
            self.prompt = '[{0}] snmp # '.format(self.current_region)

    def help(self):
        print('Execute SNMP GET or WALK query remotely on one of the agents in a region. Supported commands: get, walk')
        print('')
        print('Syntax:   snmp <command> <address> <oid1> [timeout] ')
        print('')
        print('The region is always determined automatically using device allocation configuration.')
        print('These commands operate only on one target address.')
        print('OID must be provided in the numeric form, MIB loading is not supported at this time.')
        print('Optional last argument specifies timeout in seconds')
        print('')
        print('Commands:')
        print('')
        print('  get:')
        print('     Arguments: "snmp get <address> oid"')
        print('     Example:   "snmp get 10.0.0.1 .1.3.6.1.2.1.1.2.0"')
        print('')
        print('  ')
        print('')
        print('  walk:')
        print('     Arguments: "snmp walk <address> oid"')
        print('     Example:   "snmp walk 10.0.0.1 .1.3.6.1.2.1.1.2"')
        print('')
        print('  Command "walk" supports only single OID argument')
        print('')
        print('  NOTE: this command is deprecated in favor of `agent <agent_name> snmpget|snmpwalk`')
        print('')

    def do_get(self, args):
        """
        Execute snmp GET command using agents in the currently selected region

        snmp_get <address> oid [timeout_ms]
        """
        self.snmp_command('snmpget', args)

    def do_walk(self, args):
        """
        Execute snmp WALK command using agents in the currently selected region

        snmp_walk <address> oid [timeout_ms]
        """
        self.snmp_command('snmpwalk', args)

    def snmp_command(self, command, arg):
        """
        snmp_get <address> oid [timeout_ms]
        snmp_walk <address> oid [timeout_ms]
        """
        args = arg.split()

        address = args[0]
        oid = args[1]
        timeout_ms = 2000
        if len(args) > 2:
            timeout_ms = int(args[2])

        if self.current_region is None:
            req = SNMP_TEMPLATE_WITHOUT_REGION.format(self.netid, command, address, oid, timeout_ms)
        else:
            req = SNMP_TEMPLATE_WITH_REGION.format(self.netid, command, address, oid, timeout_ms, self.current_region)
        # This call returns list of AgentCommandResponse objects in json format
        try:
            headers = {'Accept-Encoding': ''}  # to turn off gzip encoding to make response streaming work
            response = api.call(self.base_url, 'GET', req, token=self.token, stream=True, headers=headers, timeout=7200)
        except Exception as ex:
            return 503, ex
        else:
            with response:
                status = response.status_code
                if status != 200:
                    for line in response.iter_lines():
                        print('ERROR: {0}'.format(self.get_error(json.loads(line))))
                        return
                for acr in api.transform_remote_command_response_stream(response):
                    # pass
                    # print(acr)
                    status = self.parse_status(acr)
                    self.print_snmp_response(acr, status)

    def print_snmp_response(self, acr, status):
        try:
            for line in acr['response']:
                print('{0} | {1}'.format(acr['agent'], line))
        except Exception as e:
            print(e)
            print(acr)

    def parse_status(self, acr):
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

    def get_error(self, response):
        if isinstance(response, types.ListType):
            return self.get_error(response[0])
        if isinstance(response, types.UnicodeType) or isinstance(response, types.StringType):
            return response
        return response.get('error', '')
