import json
import unittest
from unittest import mock

from requests import Session

import testutils
from nsgcli.nsgcli_main import NsgCLI


def snmpwalk_chunk(*values):
    return json.dumps({'response': list(values), 'exitStatus': 0, 'error': '',
                       'uuid': '3160fc80-b447-11ec-b068-b338bf74957f', 'agent': 'carrier-docker', 'status': 'OK'})


def run_with_lines(cmdline, lines, nsgcli=None):
    with mock.patch.object(Session, 'get') as mock_get:
        mock_resp = testutils.mock_response(200, b'', None)
        mock_resp.iter_lines = mock.Mock(return_value=lines)
        mock_get.return_value = mock_resp
        return testutils.run_cmd(nsgcli or testutils.get_nsgcli(), cmdline).splitlines()


SNMPWALK_LINES = ['[' + snmpwalk_chunk('.1.3.6.1.2.1.1.1.0 = STRING: Linux'), ']']


class AgentTestCase(unittest.TestCase):

    def test_snmpwalk_prints_chunks_as_they_arrive(self):
        cmdline = 'agent carrier-docker snmpwalk 10.0.15.150 .1.3.6.1.2.1.1'
        chunks = [
            snmpwalk_chunk('.1.3.6.1.2.1.1.1.0 = STRING: Linux', '.1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.8072'),
            snmpwalk_chunk('.1.3.6.1.2.1.1.3.0 = TIMETICKS: 12345'),
        ]
        stdout_before_second_chunk = []

        with testutils.capture_stdout() as capture:
            def iter_lines(**_kwargs):
                yield '[' + chunks[0]
                # the first chunk must already be printed before the next one is read from the server
                stdout_before_second_chunk.append(capture.stdout.getvalue())
                yield chunks[1]
                yield ']'

            with mock.patch.object(Session, 'get') as mock_get:
                mock_resp = testutils.mock_response(200, b'', None)
                mock_resp.iter_lines = iter_lines
                mock_get.return_value = mock_resp
                testutils.get_nsgcli().onecmd(cmdline)

        self.assertEqual(stdout_before_second_chunk, [
            '.1.3.6.1.2.1.1.1.0 = STRING: Linux\n'
            '.1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.8072\n'
        ])
        self.assertEqual(capture.stdout.getvalue().strip().splitlines(), [
            '.1.3.6.1.2.1.1.1.0 = STRING: Linux',
            '.1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.8072',
            '.1.3.6.1.2.1.1.3.0 = TIMETICKS: 12345',
        ])

    def test_named_agent_has_no_prefix(self):
        actual = run_with_lines('agent carrier-docker snmpwalk 10.0.15.150 .1', SNMPWALK_LINES)
        self.assertEqual(actual, ['.1.3.6.1.2.1.1.1.0 = STRING: Linux'])

    def test_all_agents_have_prefix(self):
        actual = run_with_lines('agent all snmpwalk 10.0.15.150 .1', SNMPWALK_LINES)
        self.assertEqual(actual, ['carrier-docker | .1.3.6.1.2.1.1.1.0 = STRING: Linux'])

    def test_find_has_prefix(self):
        lines = ['[' + snmpwalk_chunk('10.0.15.150'), ']']
        actual = run_with_lines('agent find 10.0.15.150', lines)
        self.assertEqual(actual, ['carrier-docker | 10.0.15.150'])

    def test_agent_prefix_always(self):
        nsgcli = NsgCLI(base_url='https://base_url', token='token', netid=1, agent_prefix='always')
        actual = run_with_lines('agent carrier-docker snmpwalk 10.0.15.150 .1', SNMPWALK_LINES, nsgcli)
        self.assertEqual(actual, ['carrier-docker | .1.3.6.1.2.1.1.1.0 = STRING: Linux'])

    def test_agent_prefix_never(self):
        nsgcli = NsgCLI(base_url='https://base_url', token='token', netid=1, agent_prefix='never')
        actual = run_with_lines('agent all snmpwalk 10.0.15.150 .1', SNMPWALK_LINES, nsgcli)
        self.assertEqual(actual, ['.1.3.6.1.2.1.1.1.0 = STRING: Linux'])


if __name__ == '__main__':
    unittest.main()
