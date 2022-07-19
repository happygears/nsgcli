import unittest
import testutils

reload_resp = testutils.read_file('reload_resp.json')

make_resp = testutils.read_file('make_resp.json')


class MakeTestCase(unittest.TestCase):

    def test_make_views(self):
        cmdline = 'make views'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, make_resp)
        expected = 'operation started'
        self.assertEqual(actual, expected)

    def test_make_variables(self):
        cmdline = 'make variables'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, make_resp)
        expected = 'operation started'
        self.assertEqual(actual, expected)

    def test_make_maps(self):
        cmdline = 'make maps'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, make_resp)
        expected = 'operation started'
        self.assertEqual(actual, expected)

    def test_make_tags(self):
        cmdline = 'make tags'
        actual = testutils.run_cmd_with_mock(cmdline, 'get', 200, make_resp)
        expected = 'operation started'
        self.assertEqual(actual, expected)
