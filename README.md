# 📡 UniFi Network MCP Server

A self-hosted [Model Context Protocol](https://github.com/modelcontextprotocol) (MCP) server that turns your UniFi Network Controller into a rich set of programmable tools. Every capability is exposed via standard MCP **tools** prefixed with `unifi_`, so any LLM or agent that speaks MCP (e.g. Claude Desktop, `mcp-cli`, LangChain, etc.) can query, analyse **and** – when explicitly confirmed – modify your network.

---

## Table of Contents

* [Features](#features)
* [Quick Start](#quick-start)
  * [Docker](#docker)
  * [Python / UV](#python--uv)
  * [Install from PyPI](#install-from-pypi)
* [Using with Claude Desktop](#using-with-claude-desktop)
* [Runtime Configuration](#runtime-configuration)
* [📚 Tool Catalog](#-tool-catalog)
* [Releasing / Publishing](#releasing--publishing)

---

## Features

* Full catalog of UniFi controller operations – firewall, traffic-routes, port-forwards, QoS, VPN, WLANs, stats, devices, clients **and more**.
* All mutating tools require `confirm=true` so nothing can change your network by accident.
* Works over **stdio** (FastMCP) *and* exposes an SSE HTTP endpoint (defaults to `:3000`).
* One-liner launch via the console-script **`mcp-server-unifi-network`**.
* Idiomatic Python ≥ 3.10, packaged with **pyproject.toml** and ready for PyPI.

---

## Quick Start

### Docker

```bash
# 1. Retrieve the latest image (published from CI)
docker pull ghcr.io/sirkirby/unifi-network-mcp:latest

# 2. Run – supply UniFi credentials via env-vars or a mounted .env file
docker run -i --rm \
  -e UNIFI_HOST=192.168.1.1 \
  -e UNIFI_USERNAME=admin \
  -e UNIFI_PASSWORD=secret \
  ghcr.io/sirkirby/unifi-network-mcp:latest
```

### Python / UV

```bash
# Install UV (modern pip/venv manager) if you don't already have it
curl -fsSL https://astral.sh/uv/install.sh | bash

# 1. Clone & create a virtual-env
git clone https://github.com/sirkirby/unifi-network-mcp.git
cd unifi-network-mcp
uv venv
source .venv/bin/activate

# 2. Install in editable mode (develop-install)
uv pip install --no-deps -e .

# 3. Provide credentials (either export vars or create .env)
cp .env.example .env  # then edit values

# 4. Launch
mcp-server-unifi-network
```

### Install from PyPI

*(when published)*

```bash
uv pip install unifi-network-mcp  # or: pip install unifi-network-mcp
```

The `mcp-server-unifi-network` entry-point will be added to your `$PATH`.

---

## Using with Claude Desktop

Add (or update) the `unifi-network-mcp` block under `mcpServers` in your `claude_desktop_config.json`.

### Option 1 – Claude invokes the local package

```jsonc
"unifi-network-mcp": {
  "command": "/path/to/your/.local/bin/uvx",
  "args": ["--quiet", "unifi-network-mcp", "mcp-server-unifi-network"],
  "env": {
    "UNIFI_HOST": "192.168.1.1",
    "UNIFI_USERNAME": "admin",
    "UNIFI_PASSWORD": "secret",
    "UNIFI_SITE": "default"
  }
}
```

* `uvx` handles installing/running the package in its own environment.
* The `--quiet` flag prevents `uvx` warnings from interfering with MCP communication.
* The first argument (`unifi-network-mcp`) is the package name.
* The second argument (`mcp-server-unifi-network`) is the executable script provided by the package.

### Option 2 – Claude starts a Docker container

```jsonc
"unifi-network-mcp": {
  "command": "docker",
  "args": [
    "run", "--rm", "-i",
    "-e", "UNIFI_HOST=192.168.1.1",
    "-e", "UNIFI_USERNAME=admin",
    "-e", "UNIFI_PASSWORD=secret",
    "ghcr.io/sirkirby/unifi-network-mcp:latest"
  ]
}
```

After editing the config **restart Claude Desktop**, then test with:

```text
@unifi-network-mcp list tools
```

---

## Runtime Configuration

The server merges settings from **environment variables**, an optional `.env` file, and `src/config/config.yaml` (listed in order of precedence).

### Essential variables

| Variable | Description |
|----------|-------------|
| `CONFIG_PATH` | Full path to a custom config YAML file. If not set, checks CWD for `config/config.yaml`, then falls back to the bundled default (`src/config/config.yaml`). |
| `UNIFI_HOST` | IP / hostname of the controller |
| `UNIFI_USERNAME` | Local UniFi admin |
| `UNIFI_PASSWORD` | Admin password |
| `UNIFI_PORT` | HTTPS port (default `443`) |
| `UNIFI_SITE` | Site name (default `default`) |
| `UNIFI_VERIFY_SSL` | Set to `false` if using self-signed certs |

### `src/config/config.yaml`

Defines HTTP bind host/port (`0.0.0.0:3000` by default) plus granular permission flags. Examples below assume the default port.

---

## 📚 Tool Catalog

*All state-changing tools require the extra argument `confirm=true`.*

### Firewall

* `unifi_list_firewall_policies`
* `unifi_get_firewall_policy_details`
* `unifi_toggle_firewall_policy`
* `unifi_create_firewall_policy`
* `unifi_update_firewall_policy`
* `unifi_create_simple_firewall_policy`
* `unifi_list_firewall_zones`
* `unifi_list_ip_groups`

### Traffic Routes

* `unifi_list_traffic_routes`
* `unifi_get_traffic_route_details`
* `unifi_toggle_traffic_route`
* `unifi_update_traffic_route`
* `unifi_create_traffic_route`
* `unifi_create_simple_traffic_route`

### Port Forwarding

* `unifi_list_port_forwards`
* `unifi_get_port_forward`
* `unifi_toggle_port_forward`
* `unifi_create_port_forward`
* `unifi_update_port_forward`
* `unifi_create_simple_port_forward`

### QoS / Traffic Shaping

* `unifi_list_qos_rules`
* `unifi_get_qos_rule_details`
* `unifi_toggle_qos_rule_enabled`
* `unifi_update_qos_rule`
* `unifi_create_qos_rule`
* `unifi_create_simple_qos_rule`

### Networks & WLANs

* `unifi_list_networks`
* `unifi_get_network_details`
* `unifi_update_network`
* `unifi_create_network`
* `unifi_list_wlans`
* `unifi_get_wlan_details`
* `unifi_update_wlan`
* `unifi_create_wlan`

### VPN

* `unifi_list_vpn_clients`
* `unifi_get_vpn_client_details`
* `unifi_update_vpn_client_state`
* `unifi_list_vpn_servers`
* `unifi_get_vpn_server_details`
* `unifi_update_vpn_server_state`

### Devices

* `unifi_list_devices`
* `unifi_get_device_details`
* `unifi_reboot_device`
* `unifi_rename_device`
* `unifi_adopt_device`
* `unifi_upgrade_device`

### Clients

* `unifi_list_clients`
* `unifi_get_client_details`
* `unifi_list_blocked_clients`
* `unifi_block_client`
* `unifi_unblock_client`
* `unifi_rename_client`
* `unifi_force_reconnect_client`
* `unifi_authorize_guest`
* `unifi_unauthorize_guest`

### Statistics & Alerts

* `unifi_get_network_stats`
* `unifi_get_client_stats`
* `unifi_get_device_stats`
* `unifi_get_top_clients`
* `unifi_get_dpi_stats`
* `unifi_get_alerts`

### System

* `unifi_get_system_info`
* `unifi_get_network_health`
* `unifi_get_site_settings`

---

## Releasing / Publishing

This project uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) via a [GitHub Actions workflow](.github/workflows/publish-to-pypi.yml).

**To publish a new version:**

1. **Bump the `version`** in `pyproject.toml`.
2. **Create a new GitHub Release:** Draft a new release on GitHub, tagging it with the *exact* same version number (e.g., `v0.2.0` if the version in `pyproject.toml` is `0.2.0`).

Once published, users can install it via:

```bash
uv pip install unifi-network-mcp
```

---

### License

[MIT](LICENSE)
