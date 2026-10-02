import unittest
from unittest import mock

import testutils
from requests import Session

accepted_resp = testutils.read_file('maintenance_accepted.json')
forbidden_resp = testutils.read_file('maintenance_forbidden.json')
stubs_status_resp = testutils.read_file('maintenance_stubs_status.json')
debug_status_resp = testutils.read_file('debug_status_resp.json')

BASE = 'https://base_url/apiv3/net/1/maintenance/'


class MaintenanceTestCase(unittest.TestCase):

    def run_with_mock(self, cmdline, method, status, content, content_type=None):
        """
        run the command against a mocked requests.Session.<method>

        :return: (stdout, mock, exit_status)
        """
        with mock.patch.object(Session, method) as mock_call:
            mock_call.return_value = testutils.mock_response(status, content, content_type)
            nsgcli = testutils.get_nsgcli()
            actual = testutils.run_cmd(nsgcli, cmdline)
            return actual, mock_call, nsgcli.exit_status

    def assert_no_request(self, cmdline):
        with mock.patch.object(Session, 'post') as mock_post, mock.patch.object(Session, 'get') as mock_get:
            nsgcli = testutils.get_nsgcli()
            actual = testutils.run_cmd(nsgcli, cmdline)
            mock_post.assert_not_called()
            mock_get.assert_not_called()
            return actual, nsgcli.exit_status

    def test_every_action_posts_to_its_endpoint(self):
        for cmdline, path in [
            ('maintenance variables rebuild', 'variables/rebuild'),
            ('maintenance tags rebuild', 'tags/rebuild'),
            ('maintenance maps rebuild', 'maps/rebuild'),
            ('maintenance config reload', 'config/reload'),
            ('maintenance devices reload', 'devices/reload'),
            ('maintenance clusters reload', 'clusters/reload'),
            ('maintenance cache clear', 'cache/clear'),
            ('maintenance tsdb reconnect', 'tsdb/reconnect'),
            ('maintenance stubs resync', 'stubs/resync'),
        ]:
            with self.subTest(cmdline=cmdline):
                actual, mock_post, exit_status = self.run_with_mock(cmdline, 'post', 202, accepted_resp)
                self.assertEqual(mock_post.call_args[0][0], BASE + path)
                self.assertEqual(mock_post.call_args[1]['headers']['X-NSG-Auth-API-Token'], 'token')
                self.assertEqual(exit_status, 0)

    def test_accepted_response_is_printed(self):
        actual, _, _ = self.run_with_mock('maintenance variables rebuild', 'post', 202, accepted_resp)
        self.assertEqual(actual, 'variables_rebuild: accepted (operation dispatched to all servers in the area)')

    def test_maint_is_an_alias(self):
        _, mock_post, exit_status = self.run_with_mock('maint cache clear', 'post', 202, accepted_resp)
        self.assertEqual(mock_post.call_args[0][0], BASE + 'cache/clear')
        self.assertEqual(exit_status, 0)

    def test_stubs_resync_sends_scope_as_query_parameters(self):
        _, mock_post, _ = self.run_with_mock(
            'maintenance stubs resync --variable ifHCInOctets --device 42', 'post', 202, accepted_resp)
        self.assertEqual(mock_post.call_args[0][0], BASE + 'stubs/resync?variable=ifHCInOctets&device=42')

    def test_stubs_resync_accepts_equals_form_and_encodes_values(self):
        _, mock_post, _ = self.run_with_mock(
            'maintenance stubs resync --variable="a b&c"', 'post', 202, accepted_resp)
        self.assertEqual(mock_post.call_args[0][0], BASE + 'stubs/resync?variable=a+b%26c')

    def test_stubs_resync_placeholder_variable_means_unscoped(self):
        for placeholder in ['all', 'none', '-']:
            with self.subTest(placeholder=placeholder):
                _, mock_post, _ = self.run_with_mock(
                    'maintenance stubs resync --variable ' + placeholder, 'post', 202, accepted_resp)
                self.assertEqual(mock_post.call_args[0][0], BASE + 'stubs/resync')

    def test_stubs_resync_device_without_variable_is_rejected_locally(self):
        actual, exit_status = self.assert_no_request('maintenance stubs resync --device 42')
        self.assertEqual(actual, "ERROR: Parameter 'device' requires parameter 'variable'")
        self.assertEqual(exit_status, 1)

    def test_stubs_resync_non_numeric_device_is_rejected_locally(self):
        actual, exit_status = self.assert_no_request('maintenance stubs resync --variable cpuUtil --device abc')
        self.assertIn('--device must be a non-negative integer', actual)
        self.assertEqual(exit_status, 1)

    def test_wrong_verb_is_rejected_locally(self):
        actual, exit_status = self.assert_no_request('maintenance variables reload')
        self.assertEqual(actual, 'ERROR: expected "variables rebuild"')
        self.assertEqual(exit_status, 1)

    def test_unknown_noun_is_rejected_locally(self):
        actual, exit_status = self.assert_no_request('maintenance everything rebuild')
        self.assertIn('unknown maintenance command', actual)
        self.assertEqual(exit_status, 1)

    def test_forbidden_prints_server_error_and_sets_exit_status(self):
        actual, _, exit_status = self.run_with_mock('maintenance cache clear', 'post', 403, forbidden_resp)
        self.assertEqual(actual, "ERROR: 403: Role 'admin' is required to execute maintenance operations")
        self.assertEqual(exit_status, 1)

    def test_plain_text_unauthorized_is_printed_as_is(self):
        actual, _, exit_status = self.run_with_mock(
            'maintenance cache clear', 'post', 401, b'Not permitted to access this resource', 'text/plain')
        self.assertEqual(actual, 'ERROR: 401: Not permitted to access this resource')
        self.assertEqual(exit_status, 1)

    def test_success_after_failure_resets_exit_status(self):
        self.run_with_mock('maintenance cache clear', 'post', 403, forbidden_resp)
        _, _, exit_status = self.run_with_mock('maintenance cache clear', 'post', 202, accepted_resp)
        self.assertEqual(exit_status, 0)

    def test_stubs_status_prints_one_row_per_server(self):
        actual, mock_get, exit_status = self.run_with_mock('maintenance stubs status', 'get', 200, stubs_status_resp)
        self.assertEqual(mock_get.call_args[0][0], BASE + 'stubs/status')
        self.assertIn('nsg-mon-1', actual)
        self.assertIn('running (stale)', actual)
        self.assertIn('131072', actual)
        self.assertIn('nsg-mon-2', actual)
        self.assertIn('finished', actual)
        self.assertNotIn('finished (stale)', actual)
        self.assertEqual(exit_status, 0)

    def test_stubs_status_with_no_entries(self):
        actual, _, _ = self.run_with_mock('maintenance stubs status', 'get', 200, '{"servers": []}')
        self.assertEqual(actual, 'no stubs resync status has been recorded')


class DebugParsingTestCase(unittest.TestCase):

    def debug_params(self, cmdline):
        with mock.patch.object(Session, 'get') as mock_get:
            mock_get.return_value = testutils.mock_response(200, debug_status_resp, None)
            testutils.run_cmd(testutils.get_nsgcli(), cmdline)
            self.assertEqual(mock_get.call_args[0][0], 'https://base_url/v2/nsg/test/net/1/debug')
            return mock_get.call_args[1]['params']

    def test_level_only(self):
        self.assertEqual(self.debug_params('debug 991'), {'level': 991, 'time': 10, 'arg': ''})

    def test_level_and_time(self):
        self.assertEqual(self.debug_params('debug 991 5'), {'level': 991, 'time': 5, 'arg': ''})

    def test_level_arg_and_time(self):
        self.assertEqual(self.debug_params('debug 991 cpuUtil 5'), {'level': 991, 'time': 5, 'arg': 'cpuUtil'})

    def test_quoted_empty_arg(self):
        self.assertEqual(self.debug_params('debug 991 "" 5'), {'level': 991, 'time': 5, 'arg': ''})

    def test_placeholder_arg(self):
        self.assertEqual(self.debug_params('debug 991 - 5'), {'level': 991, 'time': 5, 'arg': ''})

    def test_too_many_arguments(self):
        with mock.patch.object(Session, 'get') as mock_get:
            actual = testutils.run_cmd(testutils.get_nsgcli(), 'debug 991 a b 5')
            mock_get.assert_not_called()
        self.assertIn('Invalid number of arguments', actual)


if __name__ == '__main__':
    unittest.main()
