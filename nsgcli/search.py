"""
This module implements subset of NetSpyGlass CLI commands

:copyright: (c) 2018 by Happy Gears, Inc
:license: Apache2, see LICENSE for more details.

"""

from . import api
from . import response_formatter
from . import sub_command


class SearchCommand(sub_command.SubCommand, object):
    # prompt = "show # "

    def __init__(self, base_url, token, net_id, region=None):
        super(SearchCommand, self).__init__(base_url, token, net_id)
        self.table_formatter = response_formatter.ResponseFormatter()
        self.current_region = region
        if region is None:
            self.prompt = 'search # '
        else:
            self.prompt = '[{0}] search # '.format(self.current_region)

    def completedefault(self, text, _line, _begidx, _endidx):
        return self.get_args(text)

    def help(self):
        print('Search device by its id, name, address, or serial number')

    def nsgql_call(self, query):
        """
        makes API call v2/nsg/cluster/net/{0}/status and returns the response. Note that
        the server does not 'json-stream' response for this API call
        """
        path = "/v2/query/net/{0}/data/".format(self.netid)
        nsgql = {
            'targets': []
        }

        if query:
            nsgql['targets'].append(
                {
                    'nsgql': query,
                    'format': 'table'
                }
            )
        return api.call(self.base_url, 'POST', path, data=nsgql, token=self.token,
                        stream=True)

    def do_device(self, arg):
        """
        search device match

        where match is device id, name, address, serial number or box description
        """
        query = 'SELECT DISTINCT id,name,address,Vendor,SerialNumber,boxDescr FROM devices ' \
                'WHERE (name REGEXP "^{0}.*$" OR address = "{0}" OR SerialNumber = "{0}" OR boxDescr REGEXP ".*{0}.*") ' \
                'AND Role NOT IN ("Cluster", "SimulatedNode")'
        response, error = self.nsgql_call(query.format(arg))
        if error is None:
            response = response[0]
            self.table_formatter.print_result_as_table(response)

        request = 'v2/ui/net/{0}/status'.format(self.netid)
        response, error = api.call(self.base_url, 'POST', request, token=self.token, response_format='json')
        if error is None:
            return response
