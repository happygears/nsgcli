"""
This module implements the NetSpyGlass API

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from __future__ import print_function

import copy
import json

# from requests.packages import urllib3

import urllib3

from requests_unixsocket import Session

try:
    import http.client as httplib
except ImportError:
    import httplib


def call(base_url, method, uri_path, data=None, token=None, timeout=180, headers=None, stream=True):
    """
    Make NetSpyGlass JSON API call to execute query

    :param base_url:     - if unix socket, then this is 'http+unix:///path_to_socket';
                           if http over tcp, then this is 'http://host' or 'https://host'
    :param method:       - GET, PUT or POST
    :param uri_path:     - API call url without "http:/server" part and without any query string parameters
    :param data:         - (a dictionary) this is the request data for PUT and POST requests
                           or query string for GET requests
    :param token:        - (optional) access token if we talk to the server over the network rather than
                            unix socket
    :param timeout:      - timeout, seconds
    :param headers:      - http request headers
    :param stream:       - if True, return result as a stream (default=True)
    """
# disable warning
# InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised.
# See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
    urllib3.disable_warnings()

    if 'http+unix://' in base_url:
        return unix_socket_call_stream(base_url, method, uri_path, data=data, timeout=timeout, headers=headers, stream=stream)
    else:
        return http_call_stream(base_url, method, uri_path, data=data, token=token, timeout=timeout, headers=headers, stream=stream)


def unix_socket_call_stream(base_url, method, uri_path, data=None, timeout=30, headers=None, stream=True):
    url = make_socket_url(base_url, uri_path)
    return make_call(url, method, data, timeout, headers={}, stream=stream)


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

    session = Session()
    if method == 'GET':
        response = session.get(url, params=data, timeout=timeout, headers=headers, verify=False, stream=stream)
    elif method == 'POST':
        response = session.post(url, json=data, timeout=timeout, headers=headers, verify=False, stream=stream)
    elif method == 'PUT':
        response = session.put(url, data=data, timeout=timeout, headers=headers, verify=False)
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
