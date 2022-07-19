"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2022 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

import json

from . import api
from . import sub_command

HELP = """
Commands that operate with NSG devices: 
        
device download (devID|name)                   download device object identified by its ID or name
"""


class DeviceCommands(sub_command.SubCommand, object):
    """
    Download device

    device download (devID|name)
    """

    def __init__(self, base_url, token, net_id, time_format):
        super(DeviceCommands, self).__init__(base_url, token, net_id, region=None)
        self.time_format = time_format
        self.prompt = 'device # '

    def help(self):
        print(HELP)

    def do_download(self, arg):
        request = 'v2/nsg/test/net/{0}/devices/{1}?source=devicepool&format=pbjson'.format(self.netid, arg)
        try:
            response = api.call(self.base_url, 'GET', request, token=self.token)
        except Exception as ex:
            print('ERROR: {0}'.format(ex))
            return None
        else:
            with response:
                status = response.status_code
                if status != 200:
                    for line in response.iter_lines():
                        err = self.get_error(json.loads(line))
                        print('ERROR: {0}'.format(err))
                        return None
                print(response.content.decode(response.encoding))
