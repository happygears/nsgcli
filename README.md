# NetSpyGlass CLI (`nsgcli`) — Developer Guide

This repository contains the Python client library and CLI suite for the [NetSpyGlass](https://www.netspyglass.com/) Network Monitoring System (NMS):

* **`nsgcli`**: Interactive and single-command shell for system operations, discovery, and agent diagnostics.
* **`nsgql`**: Command-line interface for executing NsgQL queries against the NetSpyGlass backend.
* **`silence`**: Utility for creating, listing, and modifying alert silences.
* **`nsggrok`**: Utility for testing syslog message and string parsing against Grok patterns.
* **`nsggnmi`**: Utility for sending gNMI telemetry requests (Capabilities, Get, Subscribe) to devices.

---

## Local Development Setup

### Using `uv` (Recommended)

Install the repository in editable mode so changes in `~/src/nsg/nsgcli` take effect immediately:

```bash
uv tool install --editable /path/to/nsgcli
```

Or create a local virtual environment:

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Running Tests

Run the test suite using Python's `unittest`:

```bash
PYTHONPATH=. python3 -m unittest discover tests
```

---

## Build and Release Procedure

Releases to [PyPI](https://pypi.org/project/nsgcli/) are **fully automated** via GitHub Actions ([`.github/workflows/build.yml`](.github/workflows/build.yml)).

### How Releases Work

1. **Tag-driven releases**: When a Git tag matching `v*` (e.g. `v2.2.9`) is pushed to GitHub, CI automatically:
   - Uses `happygears/gt2v` to extract the release version from the tag.
   - Automatically writes `__version__ = '<version>'` to `nsgcli/version.py`.
   - Builds source distribution and wheels (`setup.py sdist bdist_wheel`).
   - Publishes the package to PyPI via `pypa/gh-action-pypi-publish` using repository credentials.

2. **Publishing a new release**:
   ```bash
   # 1. Commit and push your changes to master
   git commit -m "Description of changes"
   git push origin master

   # 2. Create and push a new semantic version tag
   git tag v2.2.10
   git push origin v2.2.10
   ```

3. **Documentation Separation**:
   - **`README.md`** (this file) is displayed on GitHub and contains developer/architecture information and API references.
   - **`README_PYPI.md`** is read by `setup.py` as `long_description` and displayed on PyPI as end-user documentation.

### Local Build & Verification (Optional)

To test packaging locally without publishing:

```bash
# Build distributions into dist/
./tools/build.sh

# Inspect built artifacts
tar -ztvf dist/*.tar.gz
```

---

## NetSpyGlass Backend API Reference

The CLI tools wrap NetSpyGlass REST API endpoints. You can execute these endpoints directly using `curl` with standard environment variables:

```bash
export NSG_SERVICE_URL="https://nsg.example.com:9100"
export NSG_API_TOKEN="your-token"
```

### Cluster & System Status
Endpoint: `GET /v2/nsg/cluster/net/{netid}/status`  
Wrapped by: `nsgcli show status`, `nsgcli show version`

```bash
curl -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  $NSG_SERVICE_URL/v2/nsg/cluster/net/1/status
```

### NsgQL Data Query
Endpoint: `POST /v2/query/net/{netid}/data/`  
Wrapped by: `nsgql "<query>"`

```bash
curl -d '{"targets": [{"format":"table", "nsgql":"select count(key) from alerts"}]}' \
  -X POST -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  $NSG_SERVICE_URL/v2/query/net/1/data/
```

### Agent Diagnostics (Ping, Fping, Traceroute)
Endpoints:
- Ping: `GET /apiv3/net/{netid}/exec/ping/agent/{agent}?address={ip}`
- Fping: `GET /v2/nsg/cluster/net/{netid}/exec/fping?agent={agent}&address={ip}`
- Traceroute: `GET /v2/nsg/cluster/net/{netid}/exec/traceroute?agent={agent}&address={ip}`  
Wrapped by: `nsgcli agent ping ...`, `nsgcli agent fping ...`, `nsgcli agent traceroute ...`

```bash
# Agent ping:
curl -L -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  "$NSG_SERVICE_URL/apiv3/net/1/exec/ping/agent/vkhome?address=127.0.0.1"

# Agent traceroute:
curl -G -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  "$NSG_SERVICE_URL/v2/nsg/cluster/net/1/exec/traceroute" \
  --data-urlencode 'agent=vkhome' \
  --data-urlencode 'address=10.0.0.1'
```

### Remote Server Connection Test
Endpoint: `GET /v2/nsg/cluster/net/{netid}/exec/connect`

```bash
curl -G -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  $NSG_SERVICE_URL/v2/nsg/cluster/net/1/exec/connect \
  --data-urlencode 'region=world' \
  --data-urlencode 'args=10.210.24.112 9339 1000'
```

### Set Agent Log Level
Endpoint: `GET /v2/nsg/cluster/net/{netid}/exec/set_log_level`  
Wrapped by: `nsgcli agent set_log_level <agent> <logger> <level>`

```bash
curl -G -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  $NSG_SERVICE_URL/v2/nsg/cluster/net/1/exec/set_log_level \
  --data-urlencode 'region=world' \
  --data-urlencode 'args=tme-server-15v io.grpc DEBUG'
```

### Meraki API Proxy
Endpoint: `GET /v2/nsg/cluster/net/{netid}/exec/api`

```bash
curl -G -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  $NSG_SERVICE_URL/v2/nsg/cluster/net/1/exec/api \
  --data-urlencode 'region=world' \
  --data-urlencode 'url=https://api.meraki.com/api/v1/organizations/626563298157920259/devices' \
  --data-urlencode 'method=GET' \
  --data-urlencode 'args=gap-meraki'
```

### Grok Pattern Matching (`nsggrok`)

```bash
# Text matching:
nsggrok --pattern "hello world of %{WORD:world_name}" text "hello world of Grok"

# Syslog matching:
nsggrok log "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host '10.1.1.1'"
```
