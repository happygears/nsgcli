import io

from nsgcli.nsgcli_main import NsgCLI
from nsgcli.nsgql_main import NsgQLCommandLine
import contextlib
from unittest import mock
from pathlib import Path
import os
from requests import Session

nsg_cli = None
nsgql = None


def get_nsgcli():
    global nsg_cli
    if nsg_cli is None:
        nsg_cli = NsgCLI(base_url='https://base_url', token='token', netid=1)
    return nsg_cli


def get_nsgql():
    global nsgql
    if nsgql is None:
        nsgql = NsgQLCommandLine(base_url='https://base_url', token='token', netid=1)
    return nsgql


class CapturedOutput(object):
    def __init__(self, stdout):
        self.stdout = stdout


@contextlib.contextmanager
def capture_stdout():
    stdout = io.StringIO()
    with mock.patch('sys.stdout', stdout):
        yield CapturedOutput(stdout)


def run_cmd(cmd, cmdline):
    with capture_stdout() as capture:
        cmd.onecmd(cmdline)
    stdout = capture.stdout.getvalue().strip()
    return stdout


def read_file(file_name, as_text=True):
    current_path = Path(os.path.dirname(os.path.realpath(__file__)))
    file_path = current_path / 'fixtures' / file_name
    if as_text:
        return file_path.read_text()
    else:
        return file_path.read_bytes()


def mock_response(status_code, content):
    mock_resp = mock.Mock()
    mock_resp.status_code = status_code
    mock_resp.content = content
    mock_resp.encoding = 'utf-8'
    return mock_resp


def run_cmd_with_mock(cmdline, method, status, content):
    with mock.patch.object(Session, method) as mock_get:
        mock_resp = mock_response(status, content)
        mock_get.return_value = mock_resp
        mock_get.return_value.__enter__ = mock_resp
        mock_get.return_value.__exit__ = mock.Mock(return_value=False)
        nsgcli = get_nsgcli()
        actual = run_cmd(nsgcli, cmdline)
        return actual
