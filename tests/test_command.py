import unittest
import testutils

device_download_resp = testutils.read_file('device_download_response.json', as_text=False)
debug_status_resp = testutils.read_file('debug_status_resp.json')
expire_resp = testutils.read_file('expire_resp.json')
not_authorized_resp = testutils.read_file('not_authorized.txt')


class CommandTestCase(unittest.TestCase):

    def test_device_download(self):
        cmdline = 'device download 1'
        actual = testutils.run_cmd_with_mock(cmdline, "get", 200, device_download_resp)
        self.assertIn('\"name\": \"s09246ap06\"', actual)
        self.assertIn('Cid.t74gww', actual)
        self.assertIn('\"discoveryState\": \"ds_complete\"', actual)

    def test_debug(self):
        cmdline = 'debug 1'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, debug_status_resp)
        expected = 'set debug level to 1 and reset in 10 min'
        self.assertEqual(actual, expected)

    def test_expire(self):
        cmdline = 'expire 1'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, expire_resp)
        expected = 'Scheduled forced variable expiration at the end of the next cycle with retention time 1.0 hours'
        self.assertEqual(actual, expected)

    def test_unauthorized_access(self):
        cmdline = 'show system status'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 401, not_authorized_resp, content_type='text/plain')
        self.assertEqual(actual, 'An error occurred. Error: not authorized or invalid, API status code: 401')