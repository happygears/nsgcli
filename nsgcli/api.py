"""
This module implements the NetSpyGlass API

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import copy
import click
import json
import requests
from typing import Optional, Any
from nsgcli.response_formatter import ResponseFormatter, TIME_FORMAT_MS


class API(object):
    def __init__(self, **kwargs):
        self.args = kwargs
        self.base_url = kwargs['base_url']
        self.netid = kwargs.get('netid', 1)
        self.token = kwargs.get('token')
        self.response_formatter = ResponseFormatter(kwargs.get('time_format', TIME_FORMAT_MS))

    def get_status(self) -> Any:
        request = 'v2/ui/net/{0}/status'.format(self.netid)
        return json.loads(self.call('GET', request).content)[0]

    def get_cluster_status(self) -> Any:
        request = 'v2/nsg/cluster/net/{netid}/status'.format(netid=self.netid)
        return json.loads(self.call('GET', request).content)

    def get_views(self, view_id: Optional[int]) -> Any:
        request = 'v2/ui/net/{netid}/views/{viewid}/map'.format(netid=self.netid, viewid=view_id)
        return json.loads(self.call('GET', request).content)

    def get_cache_data(self):
        request = 'v2/ui/net/{netid}/actions/cache/list'.format(netid=self.netid)
        return json.loads(self.call('GET', request).content)

    def get_index(self):
        request = 'v2/ui/net/{netid}/actions/indexes/list'.format(netid=self.netid)
        return self.call('GET', request)

    def get_device_json(self, device_id: int):
        request = 'v2/ui/net/{netid}/devices/{device_id}'.format(netid=self.netid, device_id=device_id)
        return self.call('GET', request)

    # TODO(colin): it is very un-REST-ful to have a GET endpoint used for its effect, not its value
    def reload(self, thing: str):
        request = 'v2/ui/net/{netid}/actions/reload/{thing}'.format(netid=self.netid, thing=thing)
        return self.call('GET', request)

    def call(self, method, uri, data=None, timeout=180, headers=None, stream=True):
        return self.http_call_stream(method, uri, data, timeout, headers, stream)

    def nsgql_call(self, query) -> object:
        """
        makes API call v2/query/net/{0}/data and returns the response.
        """
        request = "/v2/query/net/{netid}/data/".format(netid=self.netid)
        return json.loads(
            self.call('POST', request, data={'targets': [{'nsgql': query, 'format': 'table'}]},
                      stream=True).content)[0]

    def http_call_stream(self, method, uri, data, timeout, headers, stream):
        url = concatenate_url(self.base_url, uri)
        return self.make_call(url, method, data, timeout, headers=headers, stream=stream)

    def make_call(self, url, method, data, timeout, headers, stream):
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


def call(base_url, method, uri_path, data=None, token=None, timeout=180, headers=None, stream=True):
    """
    Make NetSpyGlass JSON API call to execute query

    :param base_url:     - this is 'http://host' or 'https://host'
    :param method:       - GET, PUT or POST
    :param uri_path:     - API call url without "http:/server" part and without any query string parameters
    :param data:         - (a dictionary) this is the request data for PUT and POST requests
                           or query string for GET requests
    :param token:        - access token
    :param timeout:      - timeout, seconds
    :param headers:      - http request headers
    :param stream:       - if True, return result as a stream (default=True)
    """

    return http_call_stream(base_url, method, uri_path, data=data, token=token, timeout=timeout, headers=headers,
                            stream=stream)


def http_call_stream(base_url, method, uri_path, data=None, token=None, timeout=30, headers=None, stream=True):
    """
    returns a generator that yields tuples [http_code, line]
    """
    url = concatenate_url(base_url, uri_path)
    if headers is None:
        send_headers = {}
    else:
        send_headers = copy.copy(headers)
    if token is not None:
        send_headers['X-NSG-Auth-API-Token'] = token
    return make_call(url, method, data, timeout, headers=send_headers, stream=stream)


def make_call(url, method, data, timeout, headers, stream=False):
    # timeout_obj = urllib3.Timeout(connect=timeout, read=timeout)

    if method == 'GET':
        response = requests.get(url, params=data, timeout=timeout, headers=headers, verify=False, stream=stream)
    elif method == 'POST':
        response = requests.post(url, json=data, timeout=timeout, headers=headers, verify=False, stream=stream)
    elif method == 'PUT':
        response = requests.put(url, data=data, timeout=timeout, headers=headers, verify=False)
    else:
        raise NotImplementedError('Invalid request method {0}'.format(method))
    if response.encoding is None:
        response.encoding = 'utf-8'
    return response


def make_socket_url(base_url, uri_path):
    url = base_url.replace('/', '%2F').replace(':%2F%2F', '://')
    return concatenate_url(url, uri_path)


def concatenate_url(base_url, uri_path):
    if uri_path[0] == '/':
        return base_url + uri_path
    else:
        return base_url + '/' + uri_path


def transform_remote_command_response_stream(response_generator):
    """
    the server sends objects as JSON array. Inside of the array, each item
    occupies one line. Skip array start and end ( [ and ] ) and deserialize each
    line separately

    :param response_generator:  Response object returned by the requests 'get' or 'post' call
    :return: generator that yields lines
    """
    # print(response_generator.headers)

    for line in response_generator.iter_lines(decode_unicode=True):
        # print('####' + line)

        if not line or line.strip() in ['[', ']']:
            continue
        if line[0] == '[':
            line = line[1:]

        try:
            yield json.loads(line)
        except Exception as e:
            print('{0} : {1}'.format(e, line))
