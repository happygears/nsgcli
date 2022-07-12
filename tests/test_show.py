import unittest

import testutils

status_resp = testutils.read_file('status_resp.json')
status_first_element_expected = testutils.read_file('status_first_element_expected.json')
cluster_status_resp = testutils.read_file('cluster_status_resp.json')
device_query_response = testutils.read_file('device_query_response.json')


class ShowTestCase(unittest.TestCase):

    def test_show_uuid(self):
        cmdline = 'show uuid'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, status_resp)
        expected = '90380f0a-98b8-11ec-923d-cdc8e22ae0a7'
        self.assertEqual(actual, expected)

    def test_show_version(self):
        cmdline = 'show version'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, status_resp)
        expected = '7.1.0-b111a (net6685)'
        self.assertEqual(actual, expected)

    def test_show_status(self):
        cmdline = 'show status'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, status_resp)
        self.assertEqual(actual, status_first_element_expected)

    def test_show_system_status(self):
        cmdline = 'show system status'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, cluster_status_resp)
        self.assertIn('labdcdev-docker-monitor-1', actual)
        self.assertIn('labdcdev-monitor-1', actual)

    def test_show_system_version(self):
        cmdline = 'show system version'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, cluster_status_resp)
        self.assertIn('labdcdev-monitor-1', actual)
        self.assertIn('1.1.0-13', actual)
