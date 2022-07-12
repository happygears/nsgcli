import unittest
import testutils

discovery_queue_resp = testutils.read_file('discovery_queue_resp.json')
discovery_queue_paused_resp = testutils.read_file('discovery_queue_paused_resp.json')
status_ok_resp = testutils.read_file('status_ok_resp.json')


class DiscoveryTestCase(unittest.TestCase):

    def test_discovery_queue(self):
        cmdline = 'discovery queue'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, discovery_queue_resp)
        self.assertIn('Discovery queue is empty', actual)
        self.assertIn('Discovery servers are idle', actual)
        self.assertIn('Pending processing (the last device is the next up): 10', actual)

    def test_discovery_queue_paused(self):
        cmdline = 'discovery queue'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, discovery_queue_paused_resp)
        self.assertIn('Discovery is paused', actual)
        self.assertIn('Discovery queue is empty', actual)
        self.assertIn('Discovery servers are idle', actual)
        self.assertIn('Pending processing (the last device is the next up): 10', actual)

    def test_discovery_pause(self):
        cmdline = 'discovery pause'
        actual = testutils.run_cmd_with_mock(cmdline, 'post', 200, status_ok_resp)
        expected = 'ok'
        self.assertEqual(actual, expected)

    def test_discovery_resume(self):
        cmdline = 'discovery resume'
        actual = testutils.run_cmd_with_mock(cmdline, 'post', 200, status_ok_resp)
        expected = 'ok'
        self.assertEqual(actual, expected)

    def test_discovery_submit(self):
        cmdline = 'discovery submit 1 2'
        actual = testutils.run_cmd_with_mock(cmdline, 'post', 200, status_ok_resp)
        expected = 'ok\nok'
        self.assertEqual(actual, expected)
