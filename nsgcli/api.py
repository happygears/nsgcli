"""
This module implements the NetSpyGlass API

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import copy
import json

import urllib3
from requests_unixsocket import Session

try:
    import http.client as httplib
except ImportError:
    import http.client


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

    return http_call_stream(base_url, method, uri_path, data=data, token=token, timeout=timeout, headers=headers,
                            stream=stream)


def call_with_response_handling(base_url, method, uri_path, data=None, token=None, timeout=180, headers=None,
                                stream=True, format='plain'):
    url = concatenate_url(base_url, uri_path)
    if headers is None:
        send_headers = {}
    else:
        send_headers = copy.copy(headers)
    if token is not None:
        send_headers['X-NSG-Auth-API-Token'] = token
    response =  make_call(url, method, data, timeout, headers=send_headers, stream=stream)
    error_message = check_response(response)
    if error_message is None:
        return decode_response(response, format)


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


def handle_error_response(response):
    MSG_TEMPLATE = ("An error occurred when calling the operation: "
                    "{0} and api error code: {1}")

    status_code = response.status_code
    error = get_error(response)
    error_message = MSG_TEMPLATE.format(error, status_code)
    print(error_message)
    return error_message


def check_response(response):
    status_code = response.status_code
    if status_code < 200 or status_code >= 300:
        return handle_error_response(response)
    return None


def decode_response(response, format):
    if format == 'json':
        return json.loads(response.content)
    else:
        return response.content


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
