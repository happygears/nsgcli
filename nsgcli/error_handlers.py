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
        msg_template = ("An error occurred when calling the operation: "
                        "{0} and api error code: {1}")
        status_code = response.status_code
        error = get_error(response)
        error_message = msg_template.format(error, status_code)
        print(error_message)
        return error_message


class JsonArrayErrorHandler:
    @staticmethod
    def handle_error(response):
        for line in response.iter_lines():
            print('ERROR: {0}'.format(get_error(json.loads(line))))
            return

        response_list = []
        for line in response.iter_lines(decode_unicode=True):
            if not line or line.strip() in ['[', ']']:
                continue
            if line[0] == '[':
                line = line[1:]

            try:
                response_list.append(json.loads(line))
            except Exception as error:
                print(
                    'Unable to decode response data to json. Input data: {}, Error: {}'.format(line, error))
        return response_list
