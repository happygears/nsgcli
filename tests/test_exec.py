import unittest
import testutils
from unittest import mock

from requests import Session

exec_ping_resp = testutils.read_file("exec_ping_resp.json")


class ExecTestCase(unittest.TestCase):

    def test_exec_ping(self):
        cmdline = "exec ping 10.0.15.150"
        with mock.patch.object(Session, 'get') as mock_get:
            mock_resp = testutils.mock_response(200, exec_ping_resp, None)
            mock_get.return_value = mock_resp
            mock_get.return_value.__enter__ = mock_resp
            mock_get.return_value.__exit__ = mock.Mock(return_value=False)
            mock_get.return_value.iter_lines = mock.Mock(
                return_value=["[{\"response\":[\".1 = STRING: result: true after 1.105 s\"],"
                              + "\"exitStatus\":0,\"error\":\"\",\"uuid\":\"3160fc80-b447-11ec-b068-b338bf74957f\","
                              + "\"agent\":\"carrier-docker\",\"status\":\"OK\"}", "]"])
            nsgcli = testutils.get_nsgcli()
            actual = testutils.run_cmd(nsgcli, cmdline)
            expected = "carrier-docker | .1 = STRING: result: true after 1.105 s"
            self.assertEqual(actual, expected)

    def test_exec_fping(self):
        cmdline = "exec fping 10.0.15.150"
        with mock.patch.object(Session, 'get') as mock_get:
            mock_resp = testutils.mock_response(200, exec_ping_resp, None)
            mock_get.return_value = mock_resp
            mock_get.return_value.__enter__ = mock_resp
            mock_get.return_value.__exit__ = mock.Mock(return_value=False)
            mock_get.return_value.iter_lines = mock.Mock(
                return_value=["[{\"response\":[\".1 = STRING: 10.0.15.150 is alive\"],\"exitStatus\":0,"
                              + "\"uuid\":\"3160fc80-b447-11ec-b068-b338bf74957f\",\"agent\":\"\",\"error\":\"\","
                              + "\"status\":\"OK\"}", "{\"response\":[],\"exitStatus\":0,"
                              + "\"uuid\":\"3160fc80-b447-11ec-b068-b338bf74957f\",\"agent\":\"carrier-docker\","
                              + "\"error\":\"\",\"status\":\"OK\"}", "]"])
            nsgcli = testutils.get_nsgcli()
            actual = testutils.run_cmd(nsgcli, cmdline)
            expected = "| .1 = STRING: 10.0.15.150 is alive"
            self.assertEqual(actual, expected)

    def test_exec_traceroute(self):
        cmdline = "exec traceroute 10.0.15.150"
        with mock.patch.object(Session, 'get') as mock_get:
            mock_resp = testutils.mock_response(200, exec_ping_resp, None)
            mock_get.return_value = mock_resp
            mock_get.return_value.__enter__ = mock_resp
            mock_get.return_value.__exit__ = mock.Mock(return_value=False)
            mock_get.return_value.iter_lines = mock.Mock(
                return_value=["[{\"response\":[\".1 = STRING: traceroute to 10.0.15.150 (10.0.15.150), 30 "
                              + "hops max, 60 byte packets\"],\"exitStatus\":0,\"error\":\"\","
                              + "\"uuid\":\"3160fc80-b447-11ec-b068-b338bf74957f\",\"agent\":\"\",\"status\":\"OK\"}",
                              "{\"response\":[\".1 = STRING:  1  10.0.15.150 (10.0.15.150)  0.095 ms  0.031 "
                              + "ms  0.029 ms\"],\"exitStatus\":0,\"error\":\"\","
                              + "\"uuid\":\"3160fc80-b447-11ec-b068-b338bf74957f\",\"agent\":\"\",\"status\":\"OK\"}",
                              "{\"response\":[],\"exitStatus\":0,\"error\":\"\","
                              + "\"uuid\":\"3160fc80-b447-11ec-b068-b338bf74957f\",\"agent\":\"carrier-docker\","
                              + "\"status\":\"OK\"}", "]"])
            nsgcli = testutils.get_nsgcli()
            actual = testutils.run_cmd(nsgcli, cmdline)
            expected = "| .1 = STRING: traceroute to 10.0.15.150 (10.0.15.150), 30 hops max, 60 byte packets\n | .1 = STRING:  1  10.0.15.150 (10.0.15.150)  0.095 ms  0.031 ms  0.029 ms"
            self.assertEqual(actual, expected)
