# NetSpyGlass Command Line Tools

this package installs Python module `nsgcli` and two command line scripts: `nsgcli` and `nsgql` that
use it

Use script `tools/build.sh` to build and `tools/upload.sh` to push to pypi

Example of API call made by `nsgcli` to NSG API:
    curl -H "X-NSG-Auth-API-Token:$NSG_API_TOKEN" $NSG_SERVICE_URL/v2/nsg/cluster/net/1/status
