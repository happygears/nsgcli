# NetSpyGlass Command Line Tools (`nsgcli`)

Command-line utilities and Python client library for [NetSpyGlass](https://docs.netspyglass.com/3.0.x/index.html) Network Monitoring System (NMS).

This package provides command-line tools for querying data, checking cluster health, managing alert silences, diagnosing network agents, and working with gNMI telemetry:

- **`nsgql`**: Query metrics, interface states, alerts, and topology using NsgQL (NetSpyGlass Query Language) with tabular, JSON, or time series output.
- **`nsgcli`**: Interactive and batch control interface for server status, discovery queues, device management, and agent execution commands (ping, fping, traceroute).
- **`silence`**: Add, update, and list active or scheduled alert silences.

---

## Installation & Upgrade

### Using `uv` (Recommended)

[`uv`](https://docs.astral.sh/uv/) installs the CLI tools into an isolated environment and links the executables into your `PATH`:

```bash
# Install
uv tool install nsgcli

# Upgrade to latest version
uv tool upgrade nsgcli
```

### Using `pip`

```bash
# Install
pip install --user nsgcli

# Upgrade
pip install --user --upgrade nsgcli
```

---

## Configuration

Set default connection parameters via environment variables in your shell profile (e.g. `~/.zshrc` or `~/.bashrc`):

```bash
export NSG_SERVICE_URL="https://nsg.example.com:9100"
export NSG_API_TOKEN="your-api-access-token"
```

Alternatively, pass them explicitly on each invocation with `--base-url` (or `-b`) and `--token` (or `-a`).

---

## Commands and Usage

### 1. NsgQL Queries (`nsgql`)

Run queries against the NetSpyGlass data store. Output formats include `table` (default ASCII table), `json`, `list`, or `time_series`.

```bash
# Run a query with tabular output
nsgql "select deviceId, device, address, interface, ifAddress from interfaces where address='10.0.0.1'"

# Count active alerts
nsgql "select count(key) from alerts"

# Output as JSON
nsgql -f json "select device, address from interfaces limit 5"

# Run interactively
nsgql
```

*Corresponding Backend API:*
```bash
curl -d '{"targets": [{"format":"table", "nsgql":"select count(key) from alerts"}]}' \
  -X POST -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  $NSG_SERVICE_URL/v2/query/net/1/data/
```

---

### 2. Cluster Control & Diagnostics (`nsgcli`)

Execute commands either interactively or as single-line invocations:

```bash
# Check server and cluster version
nsgcli show version

# View cluster status
nsgcli show status

# Check discovery queue
nsgcli discovery queue

# Run ping from a specific agent
nsgcli agent ping <agent-name> 10.0.0.1

# Run fping from an agent
nsgcli agent fping <agent-name> 10.0.0.1

# Run traceroute from an agent
nsgcli agent traceroute <agent-name> 10.0.0.1

# Adjust log level on an agent
nsgcli agent set_log_level <agent-name> io.grpc DEBUG

# Start interactive shell
nsgcli
```

*Corresponding Backend APIs:*
```bash
# System status:
curl -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  $NSG_SERVICE_URL/v2/nsg/cluster/net/1/status

# Agent ping:
curl -L -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  "$NSG_SERVICE_URL/apiv3/net/1/exec/ping/agent/<agent-name>?address=10.0.0.1"

# Set agent log level:
curl -G -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" \
  $NSG_SERVICE_URL/v2/nsg/cluster/net/1/exec/set_log_level \
  --data-urlencode 'region=world' \
  --data-urlencode 'args=<agent-name> io.grpc DEBUG'
```

---

### 3. Alert Silencing (`silence`)

Manage temporary maintenance silences for alerts:

```bash
# List active and upcoming silences
silence list

# Silence all alerts for a specific device for 60 minutes
silence add --var_name='.*' --dev_id=212 --expiration=60 --reason="Scheduled maintenance"

# Silence a specific alert variable with tags
silence add --var_name='busyCpuAlert' --tags='Explicit.prod' --expiration=120

# Update expiration on an existing silence
silence update --id=8 --expiration=180
```

