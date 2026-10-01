# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Python client library and CLI tools for the NetSpyGlass NMS: `nsgcli` (interactive/one-shot ops shell), `nsgql` (NsgQL queries), `silence` (alert silences), `nsggrok` (Grok pattern testing), `nsggnmi` (gNMI requests). No pyproject; packaging is `setup.py` only, with dependencies listed in `install_requires`.

## Commands

```bash
# Dev environment (editable install pulls in requests, pandas, gnmi-proto, etc.)
uv venv && source .venv/bin/activate && uv pip install -e .

# All tests (unittest, no pytest)
PYTHONPATH=. python3 -m unittest discover tests

# Single test: tests do `import testutils`, so tests/ must be on PYTHONPATH too
PYTHONPATH=.:tests python3 -m unittest test_show.ShowTestCase.test_show_uuid

# Local package build into dist/
./tools/build.sh
```

There is no linter configured.

`bin/*` scripts are installed via `setup.py scripts=`, which copies them at install time. An editable install (`uv tool install --editable`) picks up changes to `nsgcli/*.py` immediately, but changes to `bin/*` only take effect after `uv tool install --editable --reinstall /path/to/nsgcli`.

## Releases

CI (`.github/workflows/build.yml`) builds on every push. It publishes to PyPI only when a `v*` tag is pushed (e.g. `git tag v2.2.10 && git push origin v2.2.10`). CI overwrites `nsgcli/version.py` with the version taken from the tag, so don't bump that file by hand. `README_PYPI.md` is the PyPI long description (end-user docs). `README.md` is the GitHub developer doc and has curl examples for the backend REST endpoints the CLI wraps.

## Architecture

- **Entry points**: `bin/*` are thin getopt scripts installed via `setup.py scripts=`. They parse flags (`--base-url`, `--token`, `--network`, `--region`, `-U/-L` time format), fall back to the `NSG_SERVICE_URL` / `NSG_API_TOKEN` env vars, and hand off to a class in `nsgcli/<tool>_main.py`.
- **Command tree built on `cmd.Cmd`**: `NsgCLI` (`nsgcli_main.py`) and every command group subclass `sub_command.SubCommand`, which is a `cmd.Cmd`. A top-level `do_show`/`do_agent`/`do_discovery`/... builds a fresh sub-command object (`show.ShowCommands`, `agent_commands.AgentCommands`, `discovery_commands`, `device_commands`, `exec_commands`, `system`, `search`). With args it calls `onecmd(arg)`; without args it enters that group's own `cmdloop()`. Each group follows the same `do_X` / `help_X` / `complete_X` triplet pattern. One-shot mode (`nsgcli show status`) is `onecmd` on the joined argv.
- **HTTP layer**: every request goes through `api.call(base_url, method, uri_path, ..., response_format, error_format)`, which returns `(response, error)`. It uses a `requests_unixsocket.Session`, so `base_url` can also be `http+unix://...`. TLS verification is disabled. It sends the token as the `X-NSG-Auth-API-Token` header. `response_format` picks a handler in `response_handlers.py`: `None` returns the raw Response, `'json'` returns parsed JSON, and `'json_array'` parses the server's streaming one-object-per-line JSON array. `error_format` picks a handler in `error_handlers.py`. Error handlers **print** the error and also return it.
- **Output**: commands print directly to stdout. `response_formatter.py` handles table/time formatting (`TIME_FORMAT_*` constants), using `tabulate`/`pandas`.
- `sseclient.py` is a vendored SSE client used for streaming endpoints.

## Testing pattern

Tests drive commands end to end. `testutils.run_cmd_with_mock(cmdline, 'get'|'post', status, content)` patches `requests.Session.<method>` to return a fixture from `tests/fixtures/`, runs `NsgCLI.onecmd(cmdline)`, and returns the captured stdout for comparison. New command tests should add a JSON fixture and assert on the printed output.
