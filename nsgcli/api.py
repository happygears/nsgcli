"""
This module implements the NetSpyGlass API

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import copy

import urllib3
from requests_unixsocket import Session

from . import error_handlers
from . import response_handlers

try:
    import http.client as httplib
except ImportError:
    import http.client


def call(base_url, method, uri_path, data=None, token=None, timeout=180, headers=None, stream=True,
         response_format=None, error_format=None):
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
    :param response_format:       - format of the response e.g. 'json', 'json_array' (default=None)
    :param error_format:       - format of the error e.g. 'json_array' (default=None)
    """
    # disable warning
    # InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate
    #       verification is strongly advised.
    # See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
    urllib3.disable_warnings()
    url = concatenate_url(base_url, uri_path)
    if headers is None:
        send_headers = {}
    else:
        send_headers = copy.copy(headers)
    if token is not None:
        send_headers['X-NSG-Auth-API-Token'] = token
    try:
        response = make_call(url, method, data, timeout, headers=send_headers, stream=stream)
    except Exception as ex:
        error = 'Received error when making request to endpoint: {}. Error: {}'.format(url, ex)
        print(error)
        return None, error
    else:
        error = check_error(response, error_format)
        if error is None:
            return decode_response(response, response_format), None
        else:
            return None, error


def check_error(response, error_format):
    status_code = response.status_code
    if status_code < 200 or status_code >= 300:
        if error_format is not None and error_format == 'json_array':
            return error_handlers.JsonArrayErrorHandler.handle_error(response)
        else:
            return error_handlers.BaseErrorHandler.handle_error(response)
    return None


def decode_response(response, response_format):
    if response_format is not None:
        if response_format == 'json':
            return response_handlers.JsonResponseHandler.get_data(response)
        elif response_format == 'json_array':
            return response_handlers.JsonArrayResponseHandler.get_data(response)
        else:
            print('Unknown format provided to decode response. Received format: {}'.format(response_format))
    else:
        return response_handlers.BaseResponseHandler.get_data(response)


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
