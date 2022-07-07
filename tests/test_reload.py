import unittest
import testutils

reload_resp = testutils.read_file("reload_resp.json")


class ReloadTestCase(unittest.TestCase):

    def test_reload_config(self):
        expected = "operation started"

        cmdline = "reload config"
        actual = testutils.run_cmd_with_mock(cmdline, "get", 200, reload_resp)
        self.assertEqual(actual, expected)

    def test_reload_devices(self):
        expected = "operation started"

        cmdline = "reload devices"
        actual = testutils.run_cmd_with_mock(cmdline, "get", 200, reload_resp)
        self.assertEqual(actual, expected)

    def test_reload_clusters(self):
        expected = "operation started"

        cmdline = "reload clusters"
        actual = testutils.run_cmd_with_mock(cmdline, "get", 200, reload_resp)
        self.assertEqual(actual, expected)
