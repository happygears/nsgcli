import json
from json import JSONDecodeError
"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

class BaseResponseHandler:
    @staticmethod
    def get_data(response):
        return response


class JsonResponseHandler:
    @staticmethod
    def get_data(response):
        try:
            return json.loads(response.content)
        except JSONDecodeError as error:
            print('Unable to decode response data to json. Input data: {}, Error: {}'.format(response.content, error))
            return None


class JsonArrayResponseHandler:
    @staticmethod
    def get_data(response):
        """
        the server sends objects as JSON array. Inside of the array, each item
        occupies one line. Skip array start and end ( [ and ] ) and deserialize each
        line separately
        """
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
