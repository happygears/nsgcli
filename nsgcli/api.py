"""
This module implements the NetSpyGlass API

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import click
import json
import requests
from typing import Optional, Any, List
from nsgcli.response_formatter import ResponseFormatter, TIME_FORMAT_MS


class API(object):
    def __init__(self, **kwargs):
        self.base_url = kwargs['base_url']
        self.network = kwargs.get('network', 1)
        self.token = kwargs.get('token')
        self.region = kwargs.get('region')
        self.response_formatter = ResponseFormatter(kwargs.get('time_format', TIME_FORMAT_MS))

    def get_status(self) -> Any:
        request = 'v2/ui/net/{0}/status'.format(self.network)
        return json.loads(self.call('GET', request).content)[0]

    def get_cluster_status(self) -> Any:
        request = 'v2/nsg/cluster/net/{network}/status'.format(network=self.network)
        return json.loads(self.call('GET', request).content)

    def get_views(self, view_id: Optional[int]) -> Any:
        request = 'v2/ui/net/{network}/views/{viewid}/map'.format(network=self.network, viewid=view_id)
        return json.loads(self.call('GET', request).content)

    def get_cache_data(self):
        request = 'v2/ui/net/{network}/actions/cache/list'.format(network=self.network)
        return json.loads(self.call('GET', request).content)

    def get_index(self):
        request = 'v2/ui/net/{network}/actions/indexes/list'.format(network=self.network)
        return self.call('GET', request)

    def get_device_json(self, device_id: int):
        request = 'v2/ui/net/{network}/devices/{device_id}'.format(network=self.network, device_id=device_id)
        return self.call('GET', request)

    def cache(self, op: str):
        request = 'v2/ui/net/{network}/actions/cache/{op}'.format(network=self.network, op=op)
        return self.call('GET', request)

    def make(self, thing: str):
        request = 'v2/ui/net/{network}/actions/make/{thing}'.format(network=self.network, thing=thing)
        return self.call('GET', request)

    def discover(self, op: str) -> requests.Response:
        return self.call('GET', 'v2/nsg/discovery/net/{network}/{op}'.format(network=self.network, op=op))

    def hud(self, op: str) -> requests.Response:
        return self.call('GET', 'v2/nsg/test/net/{network}/hud/{op}'.format(network=self.network, op=op))

    def nsgql_schema(self, op: str) -> requests.Response:
        return self.call('GET', 'v2/ui/net/{network}/actions/nsgqlschema/{op}'.format(network=self.network, op=op))

    def restart(self, what: str) -> requests.Response:
        return self.call('GET', 'v2/ui/net/{network}/actions/{what}/reconnect'.format(network=self.network, what=what))

    def expire(self, retention: float) -> requests.Response:
        return self.call(
            'GET',
            'v2/ui/net/{network}/actions/expire/variables'.format(network=self.network),
            data={'retentionHrs': retention})

    def debug(self, level: int, arg: str, time_min: int):
        request = 'v2/nsg/test/net/{network}/debug'.format(network=self.network)
        return self.call(
            'GET',
            request,
            data={
                'level': level,
                'time': time_min,
                'arg': arg})

    # TODO(colin) possibly use command
    def snmp(self, agent: str, cmd: str, address: str, oid: str, timeout: int) -> requests.Response:
        request = 'v2/nsg/cluster/net/{network}/exec/{cmd}'.format(network=self.network, cmd=cmd)
        return self.call(
            'GET',
            request,
            data={
                'args': ' '.join([agent, address, oid, str(timeout)]),
                'region': self.region},
            headers={'Accept-Encoding': ''},
            timeout=7200
        )

    # TODO(colin) can shift to command
    def tail(self, agent: str, lines: int, logfile: str) -> requests.Response:
        request = 'v2/nsg/cluster/net/{network}/exec/tail'.format(network=self.network)
        return self.call(
            'GET',
            request,
            data={
                'args': ' '.join([agent, str(lines), logfile]),
                'region': self.region},
            headers={'Accept-Encoding': ''},
        )

    def fping(self, address: str, args: List[str]) -> requests.Response:
        request = 'v2/nsg/cluster/net/{network}/exec/fping'.format(network=self.network)
        return self.call(
            'GET',
            request,
            data={
                'address': address,
                'region': self.region,
                'args': ' '.join(args)
            },
            headers={'Accept-Encoding': ''},
        )

    def command(self, command: str, args: List[str]):
        request = 'v2/nsg/cluster/net/{network}/exec/{command}'.format(network=self.network, command=command)
        return self.call(
            'GET',
            request,
            data={
                'args': ' '.join(args),
                'region': self.region},
            headers={'Accept-Encoding': ''},
        )

    def reload(self, thing: str) -> requests.Response:
        request = 'v2/ui/net/{network}/actions/reload/{thing}'.format(network=self.network, thing=thing)
        return self.call('GET', request)

    def call(self, method, uri, data=None, timeout=180, headers=None, stream=True):
        return self.http_call_stream(method, uri, data, timeout, headers, stream)

    def nsgql_query(self, query: str, result_format='table') -> object:
        """
        makes API call v2/query/net/{0}/data and returns the response.
        """
        return self.nsgql_multiquery([query], result_format)[0]

    def nsgql_multiquery(self, queries: List[str], result_format, timeout=180) -> List[object]:
        """
        makes API call v2/query/net/{0}/data and returns the response.
        """
        request = "/v2/query/net/{network}/data/".format(network=self.network)
        return json.loads(
            self.call(
                'POST',
                request,
                data={'targets': [{'nsgql': q, 'format': result_format} for q in queries]},
                stream=True,
                timeout=timeout
            ).content)

    def ping_server(self) -> requests.Response:
        request = 'v2/ping/net/{network}/se'.format(network=self.network)
        return self.call('GET', request)

    def index_command(self, command) -> requests.Response:
        request = 'v2/ui/net/{network}/actions/indexes/{command}'.format(network=self.network, command=command)
        return self.call('GET', request)

    def index_create(self, table, column, function) -> requests.Response:
        request = 'v2/ui/net/{network}/actions/indexes/create'.format(network=self.network)
        return self.call(
            'POST',
            request,
            data={
                'table': table,
                'column': column,
                'function': function})

    def http_call_stream(self, method, uri, data, timeout, headers, stream) -> requests.Response:
        url = concatenate_url(self.base_url, uri)
        return self.make_call(url, method, data, timeout, headers=headers, stream=stream)

    def make_call(self, url, method, data, timeout, headers, stream) -> requests.Response:
        hs = {}
        if headers:
            hs.update(headers)
        if self.token:
            hs['X-NSG-Auth-API-Token'] = self.token
        if method == 'GET':
            response = requests.get(url, params=data, timeout=timeout, headers=hs, verify=False, stream=stream)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=timeout, headers=headers, verify=False, stream=stream)
        elif method == 'PUT':
            response = requests.put(url, data=data, timeout=timeout, headers=headers, verify=False)
        else:
            raise NotImplementedError('Invalid request method {0}'.format(method))
        if response.encoding is None:
            response.encoding = 'utf-8'

        if response.status_code != 200:
            try:
                payload = json.loads(response.content)
                if 'error' in payload:
                    raise click.ClickException(f'{response.status_code} {payload["error"]}')
                else:
                    raise click.ClickException(f'{response.status_code} {payload}')
            except json.JSONDecodeError:
                raise click.ClickException(response)

        return response

    def print_response(self, response: requests.Response) -> None:
        if response.status_code != 200:
            print(response)
        j = json.loads(response.content)
        if self.is_error(j):
            print('ERROR: {0}'.format(self.get_error(j)))
        else:
            print(j['success'])

    @staticmethod
    def print_agent_response(acr, status=None):
        if not status:
            for line in acr['response']:
                print('{0} | {1}'.format(acr['agent'], line))
        else:
            print('{0} | {1}'.format(acr['agent'], status))

    def is_error(self, x: Any) -> bool:
        if isinstance(x, list):
            return self.is_error(x[0])
        return isinstance(x, dict) and x.get('status', 'ok').lower() != 'ok'

    @staticmethod
    def get_error(response):
        """
        if the response is in standard form (a dictionary with key 'error' or 'success') then
        this function finds and returns the value of the key 'error'. Otherwise it returns
        the whole response as a string
        """
        if isinstance(response, dict):
            return response.get('error', str(response))
        else:
            return str(response)

    def common_command(self, command: str, args: List[str], deduplicate_replies=True) -> None:
        """
        send command to agents and pick up replies. If hide_errors=True, only successful
        replies are printed, otherwise all replies are printed.

        If deduplicate_replies=True, duplicate replies are suppressed (e.g. when multiple agents
        reply)
        """
        response = self.command(command, args)
        replies_seen = set()
        with response:
            for acr in self.transform_remote_command_response_stream(response):
                acr_str = json.dumps(acr)
                if deduplicate_replies:
                    if acr_str in replies_seen:
                        continue
                    replies_seen.add(acr_str)
                self.print_agent_response(acr)

    def transform_remote_command_response_stream(self, response_generator):
        """
        the server sends objects as JSON array. Inside of the array, each item
        occupies one line. Skip array start and end ( [ and ] ) and deserialize each
        line separately

        :param response_generator:  Response object returned by the requests 'get' or 'post' call
        :return: generator that yields lines
        """
        for line in response_generator.iter_lines(decode_unicode=True):
            line = line.strip('[]')
            if not line:
                continue
            o = json.loads(line)
            if self.is_error(o):
                raise click.ClickException(o.get('error', o))
            yield o


def concatenate_url(base_url, uri_path):
    if uri_path[0] == '/':
        return base_url + uri_path
    else:
        return base_url + '/' + uri_path
