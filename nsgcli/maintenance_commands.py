"""
This module implements the "maintenance" command group: cluster-wide maintenance operations
served by the NetSpyGlass APIv3 endpoints /apiv3/net/:id/maintenance/...

All operations require the admin role on the server.

:copyright: (c) 2026 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import json
import shlex
import time
from urllib.parse import urlencode

from tabulate import tabulate

from . import api
from . import sub_command

# noun -> verbs supported by "maintenance <noun> <verb>"
MAINTENANCE_COMMANDS = {
    'variables': ['rebuild'],
    'tags': ['rebuild'],
    'maps': ['rebuild'],
    'config': ['reload'],
    'devices': ['reload'],
    'clusters': ['reload'],
    'cache': ['clear'],
    'tsdb': ['reconnect'],
    'stubs': ['resync', 'status'],
}

# values of --variable that mean "unscoped"
UNSCOPED_PLACEHOLDERS = ['all', 'none', '-']

MAINTENANCE_PATH = 'apiv3/net/{0}/maintenance/{1}/{2}'

STATUS_FIELDS = ['server', 'state', 'scope', 'pushed', 'examined', 'updated']


class MaintenanceCommands(sub_command.SubCommand, object):
    """
    Cluster-wide maintenance operations. They require the admin role.

    The result of the last command is kept in self.exit_status (0 = success, 1 = error) rather than
    returned from do_* methods, because cmd.Cmd.cmdloop() stops on a truthy return value.
    """

    def __init__(self, base_url, token, net_id, region=None):
        super(MaintenanceCommands, self).__init__(base_url, token, net_id, region=region)
        self.prompt = 'maintenance # '
        self.exit_status = 0

    def help(self):
        print("""Cluster-wide maintenance operations (require the admin role):

maintenance variables rebuild       rebuild all monitoring variables
maintenance tags rebuild            rebuild device tags
maintenance maps rebuild            rebuild maps and views
maintenance config reload           reload configuration
maintenance devices reload          reload devices
maintenance clusters reload         reload device clusters
maintenance cache clear             flush the NsgQL query cache
maintenance tsdb reconnect          reconnect TSDB connection pools
maintenance stubs resync [--variable <name>] [--device <id>]
                                    re-push monitoring variable stubs to the OpenSearch index;
                                    --device requires --variable
maintenance stubs status            show the stubs resync status of every server

"maint" is an alias for "maintenance".
""")

    def default(self, line):
        print('ERROR: unknown maintenance command "{0}"; see "help maintenance"'.format(line))
        self.exit_status = 1

    ##########################################################################################
    def do_variables(self, arg):
        """maintenance variables rebuild"""
        self.simple_action('variables', arg)

    def do_tags(self, arg):
        """maintenance tags rebuild"""
        self.simple_action('tags', arg)

    def do_maps(self, arg):
        """maintenance maps rebuild"""
        self.simple_action('maps', arg)

    def do_config(self, arg):
        """maintenance config reload"""
        self.simple_action('config', arg)

    def do_devices(self, arg):
        """maintenance devices reload"""
        self.simple_action('devices', arg)

    def do_clusters(self, arg):
        """maintenance clusters reload"""
        self.simple_action('clusters', arg)

    def do_cache(self, arg):
        """maintenance cache clear"""
        self.simple_action('cache', arg)

    def do_tsdb(self, arg):
        """maintenance tsdb reconnect"""
        self.simple_action('tsdb', arg)

    def do_stubs(self, arg):
        """
        maintenance stubs resync [--variable <name>] [--device <id>]
        maintenance stubs status
        """
        tokens = self.split(arg)
        if tokens is None:
            return
        if not tokens or tokens[0] not in MAINTENANCE_COMMANDS['stubs']:
            self.fail('expected one of {0} after "stubs"'.format(MAINTENANCE_COMMANDS['stubs']))
            return
        if tokens[0] == 'status':
            if len(tokens) > 1:
                self.fail('"stubs status" takes no arguments')
                return
            self.stubs_status()
        else:
            query = self.parse_resync_options(tokens[1:])
            if query is not None:
                self.post('stubs', 'resync', query)

    def complete_variables(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, MAINTENANCE_COMMANDS['variables'])

    def complete_tags(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, MAINTENANCE_COMMANDS['tags'])

    def complete_maps(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, MAINTENANCE_COMMANDS['maps'])

    def complete_config(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, MAINTENANCE_COMMANDS['config'])

    def complete_devices(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, MAINTENANCE_COMMANDS['devices'])

    def complete_clusters(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, MAINTENANCE_COMMANDS['clusters'])

    def complete_cache(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, MAINTENANCE_COMMANDS['cache'])

    def complete_tsdb(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, MAINTENANCE_COMMANDS['tsdb'])

    def complete_stubs(self, text, _line, _begidx, _endidx):
        return self.complete_cmd(text, MAINTENANCE_COMMANDS['stubs'])

    ##########################################################################################
    def simple_action(self, noun, arg):
        tokens = self.split(arg)
        if tokens is None:
            return
        verbs = MAINTENANCE_COMMANDS[noun]
        if len(tokens) != 1 or tokens[0] not in verbs:
            self.fail('expected "{0} {1}"'.format(noun, ' | '.join(verbs)))
            return
        self.post(noun, tokens[0])

    def parse_resync_options(self, tokens):
        """
        parse "[--variable <name>] [--device <id>]" (also "--variable=<name>", "--device=<id>")

        :return: query parameters as a dictionary, or None after printing an error
        """
        options = {}
        i = 0
        while i < len(tokens):
            token = tokens[i]
            name, sep, value = token.partition('=')
            if name not in ('--variable', '--device'):
                self.fail('unknown option "{0}"; expected --variable or --device'.format(token))
                return None
            if not sep:
                i += 1
                if i >= len(tokens):
                    self.fail('option {0} requires a value'.format(name))
                    return None
                value = tokens[i]
            options[name] = value
            i += 1

        query = {}
        variable = options.get('--variable', '').strip()
        if variable and variable.lower() not in UNSCOPED_PLACEHOLDERS:
            query['variable'] = variable
        device = options.get('--device', '').strip()
        if device:
            if not device.isdigit():
                self.fail('--device must be a non-negative integer device id, got "{0}"'.format(device))
                return None
            if 'variable' not in query:
                self.fail("Parameter 'device' requires parameter 'variable'")
                return None
            query['device'] = device
        return query

    def post(self, noun, verb, query=None):
        response = self.request('POST', noun, verb, query)
        if response is None:
            return
        body = self.parse_json(response)
        operation = body.get('operation', '{0}_{1}'.format(noun, verb)) if isinstance(body, dict) else noun
        message = body.get('message', '') if isinstance(body, dict) else ''
        print('{0}: accepted{1}'.format(operation, ' ({0})'.format(message) if message else ''))
        self.exit_status = 0

    def stubs_status(self):
        response = self.request('GET', 'stubs', 'status')
        if response is None:
            return
        body = self.parse_json(response)
        servers = body.get('servers') if isinstance(body, dict) else None
        if servers is None:
            self.fail('unexpected response: {0}'.format(self.response_text(response)))
            return
        self.exit_status = 0
        if not servers:
            print('no stubs resync status has been recorded')
            return
        now_ms = int(time.time() * 1000)
        rows = []
        for s in servers:
            state = s.get('state', '')
            if s.get('stale'):
                state += ' (stale)'
            rows.append([s.get('server', ''), state, s.get('scope', ''), s.get('pushed', ''),
                         s.get('examined', ''), self.age(now_ms, s.get('updatedAtMs'))])
        print(tabulate(rows, STATUS_FIELDS, tablefmt='fancy_outline'))

    ##########################################################################################
    def request(self, method, noun, verb, query=None):
        """
        send the request and handle errors here rather than in api.check_error(): APIv3 errors are
        a single JSON object, and authentication failures are plain text

        :return: the response on 2xx, otherwise None after printing an error and setting exit_status
        """
        url = api.concatenate_url(self.base_url, MAINTENANCE_PATH.format(self.netid, noun, verb))
        if query:
            url += '?' + urlencode(query)
        headers = {}
        if self.token is not None:
            headers['X-NSG-Auth-API-Token'] = self.token
        try:
            response = api.make_call(url, method, None, timeout=180, headers=headers, stream=False)
        except Exception as ex:
            self.fail('request to {0} failed: {1}'.format(url, ex))
            return None
        if response.status_code < 200 or response.status_code >= 300:
            body = self.parse_json(response, quiet=True)
            if isinstance(body, dict) and body.get('error'):
                error = body['error']
            else:
                error = self.response_text(response)
            print('ERROR: {0}: {1}'.format(response.status_code, error))
            self.exit_status = 1
            return None
        return response

    def fail(self, message):
        print('ERROR: {0}'.format(message))
        self.exit_status = 1

    def split(self, arg):
        try:
            return shlex.split(arg)
        except ValueError as ex:
            self.fail('can not parse "{0}": {1}'.format(arg, ex))
            return None

    @staticmethod
    def parse_json(response, quiet=False):
        try:
            return json.loads(response.content)
        except Exception as ex:
            if not quiet:
                print('Unable to decode response as JSON: {0}'.format(ex))
            return None

    @staticmethod
    def response_text(response):
        content = response.content
        if isinstance(content, bytes):
            content = content.decode(response.encoding or 'utf-8', errors='replace')
        return str(content).strip()

    @staticmethod
    def age(now_ms, updated_at_ms):
        if not updated_at_ms:
            return ''
        seconds = max(0, (now_ms - int(updated_at_ms)) // 1000)
        if seconds < 120:
            return '{0}s ago'.format(seconds)
        minutes = seconds // 60
        if minutes < 120:
            return '{0}m ago'.format(minutes)
        return '{0}h ago'.format(minutes // 60)
