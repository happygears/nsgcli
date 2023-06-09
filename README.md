# NetSpyGlass Command Line Tools

this package installs Python module `nsgcli` and two command line scripts: `nsgcli` and `nsgql` that
use it

Use script `tools/build.sh` to build and `tools/upload.sh` to push to pypi

Example of API call made by `nsgcli` to nsg-api service:

* System status

  ```bash
  curl -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" $NSG_SERVICE_URL/v2/nsg/cluster/net/1/status
  ```

* NSGQL

  ```bash
  curl -d '{"targets": [{"format":"table", "nsgql":"select count(key) from alerts"}]}' -X POST -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" $NSG_SERVICE_URL/v2/query/net/1/data/
  ```
  
* NSGGROK
  
  Parse text with custom pattern
  ```bash
  nsggrok --pattern "hello world of %{WORD:world_name}" text "hello world of Grok"
  {
  "world_name": "Grok"
  }
  ```
  
  Parse syslog message with built-in patterns
  ```bash
  nsggrok log "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host '10.1.1.1'"
  {
  "sshUser": "root",
  "index": "labdcdev-syslog-short",
  "sshSrcIp": "10.1.1.1",
  "logText": "SSHD_LOGIN_FAILED: Login failed for user 'root' from host '10.1.1.1'",
  "prio": "13",
  "logSyslogSeverityName": "notice",
  "logSource": "carrier",
  "logSyslogText": "<13>May 18 11:22:43 carrier sshd: SSHD_LOGIN_FAILED: Login failed for user 'root' from host '10.1.1.1'",
  "logSyslogFacilityName": "user",
  "logTimestamp": "2021-05-18T11:22:43.000Z",
  "program": "sshd",
  "logSyslogPriority": 13,
  "timestamp": "May 18 11:22:43",
  "logSyslogFacilityCode": 1,
  "logSyslogSeverityCode": 5
  }
  ```
  
* Meraki API call
```bash
curl -G -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" $NSG_SERVICE_URL/v2/nsg/cluster/net/1/exec/api --data-urlencode 'region=world' --data-urlencode 'url=https://api.meraki.com/api/v1/organizations/626563298157920259/devices' --data-urlencode 'method=GET' --data-urlencode 'args=gap-meraki'
```

* Test connection to remote server
```bash
curl -G -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" $NSG_SERVICE_URL/v2/nsg/cluster/net/1/exec/connect --data-urlencode 'region=world' --data-urlencode 'args=10.210.24.112 9339 1000'
```

* Set log level
```bash
curl -G -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" $NSG_SERVICE_URL/v2/nsg/cluster/net/1/exec/set_log_level --data-urlencode 'region=world' --data-urlencode 'args=tme-server-15v io.grpc DEBUG'
```