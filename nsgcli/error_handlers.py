"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import json


def get_error(response):
    """
    if the response is in standard form (a dictionary with key 'error' or 'success') then
    this function finds and returns the value of the key 'error'. Otherwise it returns
    the whole response as a string
    """
    if isinstance(response, dict):
        return response.get('error', str(response))
    elif isinstance(response, list):
        return get_error(response[0])
    elif isinstance(response, str) or isinstance(response, bytes):
        return response
    else:
        return str(response)


class BaseErrorHandler:
    @staticmethod
    def handle_error(response):
        msg_template = ("An error occurred. Error: "
                        "{0}, API status code: {1}")
        status_code = response.status_code
        is_response_json = False
        if response.headers is not None:
            is_response_json = response.headers['Content-Type'].__contains__('application/json')
        if is_response_json:
            error = get_error(json.loads(response.content))
        else:
            error = get_error(response.content)
        error_message = msg_template.format(error, status_code)
        print(error_message)
        return error_message


class JsonArrayErrorHandler:
    @staticmethod
    def handle_error(response):
        for line in response.iter_lines():
            error_message = 'ERROR: {0}'.format(get_error(json.loads(line)))
            print(error_message)
            return error_message
