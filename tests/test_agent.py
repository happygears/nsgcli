import json
import unittest
from unittest import mock

from requests import Session

import testutils


def snmpwalk_chunk(*values):
    return json.dumps({'response': list(values), 'exitStatus': 0, 'error': '',
                       'uuid': '3160fc80-b447-11ec-b068-b338bf74957f', 'agent': 'carrier-docker', 'status': 'OK'})


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
            'carrier-docker | .1.3.6.1.2.1.1.1.0 = STRING: Linux\n'
            'carrier-docker | .1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.8072\n'
        ])
        self.assertEqual(capture.stdout.getvalue().strip().splitlines(), [
            'carrier-docker | .1.3.6.1.2.1.1.1.0 = STRING: Linux',
            'carrier-docker | .1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.8072',
            'carrier-docker | .1.3.6.1.2.1.1.3.0 = TIMETICKS: 12345',
        ])


if __name__ == '__main__':
    unittest.main()
