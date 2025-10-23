# 📡 UniFi Network MCP Server

[![License][license-shield]](LICENSE)
![Project Maintenance][maintenance-shield]
[![GitHub Activity][commits-shield]][commits]

[![GitHub Release][release-shield]][releases]
[![issues][issues-shield]][issues-link]
[![test-badge]][test-workflow]
[![validate-badge]][validate-workflow]
[![validate-docker-badge]][validate-docker-workflow]

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/sirkirby)

A self-hosted [Model Context Protocol](https://github.com/modelcontextprotocol) (MCP) server that turns your UniFi Network Controller into a rich set of interactive tools. Every capability is exposed via standard MCP **tools** prefixed with `unifi_`, so any LLM or agent that speaks MCP (e.g. Claude Desktop, `mcp-cli`, LangChain, etc.) can query, analyze **and** – when explicitly authorized – modify your network. These tools must have local access to your UniFi Network Controller, by either running locally or in the cloud connected via a secure reverse proxy. Please consider the [security implications](#security-considerations) of running these tools in the cloud as they contain sensitive information and access to your network.

---

## Table of Contents

* [Features](#features)
* [Quick Start](#quick-start)
  * [Docker](#docker)
  * [Python / UV](#python--uv)
  * [Install from PyPI](#install-from-pypi)
* [Using with Local LLMs and Agents](#using-with-local-llms-and-agents)
* [Using with Claude Desktop](#using-with-claude-desktop)
* [Runtime Configuration](#runtime-configuration)
* [Diagnostics (Advanced Logging)](#diagnostics-advanced-logging)
* [Developer Console (Local Tool Tester)](#developer-console-local-tool-tester)
* [Security Considerations](#security-considerations)
* [📚 Tool Catalog](#-tool-catalog)
* [Testing](#testing)
* [Contributing: Releasing / Publishing](#contributing-releasing--publishing)

---

## Features

* Full catalog of UniFi controller operations – firewall, traffic-routes, port-forwards, QoS, VPN, WLANs, stats, devices, clients **and more**.
* All mutating tools require `confirm=true` so nothing can change your network by accident.
* Works over **stdio** (FastMCP). Optional SSE HTTP endpoint can be enabled via config.
* One-liner launch via the console-script **`unifi-network-mcp`**.
* Idiomatic Python ≥ 3.10, packaged with **pyproject.toml** and ready for PyPI.

---

## Quick Start

### Docker

```bash
# 1. Retrieve the latest image (published from CI)
docker pull ghcr.io/sirkirby/unifi-network-mcp:latest

# 2. Run – supply UniFi credentials via env-vars or a mounted .env file
# Ensure all UNIFI_* variables are set as needed (see Runtime Configuration table)
docker run -i --rm \
  -e UNIFI_HOST=192.168.1.1 \
  -e UNIFI_USERNAME=admin \
  -e UNIFI_PASSWORD=secret \
  -e UNIFI_PORT=443 \
  -e UNIFI_SITE=default \
  -e UNIFI_VERIFY_SSL=false \
  ghcr.io/sirkirby/unifi-network-mcp:latest
  # Optional: Set controller type (auto-detected if omitted)
  # -e UNIFI_CONTROLLER_TYPE=auto \
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
# The server will auto-detect your controller type (UniFi OS vs standard)
# Use UNIFI_CONTROLLER_TYPE to manually override if needed
cp .env.example .env  # then edit values

# 4. Launch
unifi-network-mcp
```

### Install from PyPI

*(when published)*

```bash
uv pip install unifi-network-mcp  # or: pip install unifi-network-mcp
```

The `unifi-network-mcp` entry-point will be added to your `$PATH`.

---

## Using with Local LLMs and Agents

No internet access is required, everything runs locally. It's recommend you have an M-Series Mac or Windows/Linux with a very modern GPU (Nvidia RTX 4000 series or better)

### Recommended

Install [LM Studio](https://lmstudio.ai) and edit the mcp.json file `chat prompt --> tool icon --> edit mcp.json` to add the unifi-network-mcp server tools, allowing you to prompt using a locally run LLM of your choice. Configure just as you would for Claude desktop. I recommend loading a tool capable model like OpenAI's [gp-oss](https://lmstudio.ai/models/openai/gpt-oss-20b), and prompt it to use the UniFi tools.

```text
Example prompt: using the unifi tools, list my most active clients on the network and include the type of traffic and total bandwidth used.
```

### Alternative

Use [Ollama](https://ollama.com/) with [ollmcp](https://github.com/jonigl/mcp-client-for-ollama), allowing you to use a locally run LLM capable of tool calling via your favorite [terminal](https://app.warp.dev/referral/EJK58L).

## Using with Claude Desktop

Add (or update) the `unifi-network-mcp` block under `mcpServers` in your `claude_desktop_config.json`.

### Option 1 – Claude invokes the local package

```jsonc
"unifi-network-mcp": {
  "command": "/path/to/your/.local/bin/uvx",
  "args": ["--quiet", "unifi-network-mcp"], // Or "unifi-network-mcp==<version>"
  "env": {
    "UNIFI_HOST": "192.168.1.1",
    "UNIFI_USERNAME": "admin",
    "UNIFI_PASSWORD": "secret",
    "UNIFI_PORT": "443",
    "UNIFI_SITE": "default",
    "UNIFI_VERIFY_SSL": "false"
    // Optional: "UNIFI_CONTROLLER_TYPE": "auto"
  }
}
```

* `uvx` handles installing/running the package in its own environment.
* The `--quiet` flag is recommended if `uvx` outputs non-JSON messages.
* If you want to pin to a specific version, use `"unifi-network-mcp==<version_number>"` as the package name.
* If your script name in `pyproject.toml` differs from the package name, use `["--quiet", "<package-name>", "<script-name>"]`.

### Option 2 – Claude starts a Docker container

```jsonc
"unifi-network-mcp": {
  "command": "docker",
  "args": [
    "run", "--rm", "-i",
    "-e", "UNIFI_HOST=192.168.1.1",
    "-e", "UNIFI_USERNAME=admin",
    "-e", "UNIFI_PASSWORD=secret",
    "-e", "UNIFI_PORT=443",
    "-e", "UNIFI_SITE=default",
    "-e", "UNIFI_VERIFY_SSL=false",
    // Optional: "-e", "UNIFI_CONTROLLER_TYPE=auto",
    "ghcr.io/sirkirby/unifi-network-mcp:latest"
  ]
}
```

### Option 3 – Claude attaches to an existing Docker container (recommended for compose)

1) Using the container name as specified in `docker-compose.yml` from the repository root:

```yaml
docker-compose up --build
```

2) Then configure Claude Desktop:

```jsonc
"unifi-network-mcp": {
  "command": "docker",
  "args": ["exec", "-i", "unifi-network-mcp", "unifi-network-mcp"]
}
```

Notes:

* Use `-T` only with `docker compose exec` (it disables TTY for clean JSON). Do not use `-T` with `docker exec`.
* Ensure the compose service is running (`docker compose up -d`) before attaching.

After editing the config **restart Claude Desktop**, then test with:

```text
@unifi-network-mcp list tools
```

### Optional HTTP SSE endpoint (off by default)

For environments where HTTP is acceptable (e.g., local development), you can enable the HTTP SSE server and expose it explicitly:

```bash
docker run -i --rm \
  -p 3000:3000 \
  -e UNIFI_MCP_HTTP_ENABLED=true \
  ...
  ghcr.io/sirkirby/unifi-network-mcp:latest
```

Security note: Leave this disabled in production or sensitive environments. The stdio transport remains the default and recommended mode.

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
| `UNIFI_CONTROLLER_TYPE` | Controller API path type: `auto` (detect), `proxy` (UniFi OS), `direct` (standalone). Default `auto` |
| `UNIFI_MCP_HTTP_ENABLED` | Set `true` to enable optional HTTP SSE server (default `false`) |

### Controller Type Detection

The server automatically detects whether your UniFi controller requires UniFi OS proxy paths (`/proxy/network/api/...`) or standard direct paths (`/api/...`). This eliminates 404 errors on newer UniFi OS controllers without manual configuration.

#### Automatic Detection (Default)

```bash
# No configuration needed - detection happens automatically
UNIFI_CONTROLLER_TYPE=auto  # or omit entirely
```

The server will:
1. Probe both path structures during connection initialization
2. Cache the result for the session lifetime
3. Automatically use the correct paths for all API requests

**Detection Time**: Adds ~300ms to initial connection time (within 2-second target).

#### Manual Override

If automatic detection fails or you want to force a specific mode:

```bash
# For UniFi OS controllers (Cloud Gateway, UDM-Pro, self-hosted UniFi OS 4.x+)
export UNIFI_CONTROLLER_TYPE=proxy

# For standalone UniFi Network controllers
export UNIFI_CONTROLLER_TYPE=direct
```

#### Troubleshooting

If you encounter connection errors:

1. **Check controller accessibility**: Verify you can reach the controller on the configured port
2. **Try manual override**: Set `UNIFI_CONTROLLER_TYPE=proxy` or `direct` based on your controller type
3. **Check logs**: Look for detection messages in the server output
4. **See issue #19**: [UniFi OS path compatibility](https://github.com/sirkirby/unifi-network-mcp/issues/19)

**When to use manual override**:
- Detection fails (network issues, firewall blocking probes)
- Running in restricted network environment
- Want to skip detection for faster startup
- Testing specific path configuration

### `src/config/config.yaml`

Defines HTTP bind host/port (`0.0.0.0:3000` by default) plus granular permission flags. Examples below assume the default port.

---

## Diagnostics (Advanced Logging)

Enable a global diagnostics mode to emit structured logs for every tool call and controller API request. Only recommended for debugging.

Configuration in `src/config/config.yaml`:

```yaml
server:
  diagnostics:
    enabled: false            # toggle globally
    log_tool_args: true       # include tool args/kwargs (safely redacted)
    log_tool_result: true     # include tool results (redacted)
    max_payload_chars: 2000   # truncate large payloads
```

Environment overrides:

* `UNIFI_MCP_DIAGNOSTICS` (true/false)
* `UNIFI_MCP_DIAG_LOG_TOOL_ARGS` (true/false)
* `UNIFI_MCP_DIAG_LOG_TOOL_RESULT` (true/false)
* `UNIFI_MCP_DIAG_MAX_PAYLOAD` (integer)

Notes:

* Logs are emitted via standard Python logging under `unifi-network-mcp.diagnostics`.
* Set `server.log_level` (or `UNIFI_MCP_LOG_LEVEL`) to `INFO`/`DEBUG` to surface entries.
* Tool calls log timing and optional redacted args/results; API calls log method, path, timing, and redacted request/response snapshots.

---

## Developer Console (Local Tool Tester)

A lightweight interactive console to list and invoke tools locally without LLM tool calling. It uses your normal config and the same runtime, so diagnostics apply automatically when enabled. Grab your [favorite terminal](https://app.warp.dev/referral/EJK58L) to get started.

Location: `devtools/dev_console.py`

Run:

```bash
python devtools/dev_console.py
```

What it does:

* Loads config and initializes the UniFi connection.
* Auto-loads all `unifi_*` tools.
* Lists available tools with descriptions.
* On selection, shows a schema hint (when available) and prompts for JSON arguments.
* Executes the tool via the MCP server and prints the JSON result.

Tips:

* Combine with Diagnostics for deep visibility: set `UNIFI_MCP_DIAGNOSTICS=true` (or enable in `src/config/config.yaml`).
* For mutating tools, set `{"confirm": true}` in the JSON input when prompted.

### Supplying arguments

You can provide tool arguments in three ways:

* Paste a JSON object (recommended for complex inputs):
  ```json
  {"mac_address": "14:1b:4f:dc:5b:cf"}
  ```

* Type a single value when the tool has exactly one required parameter. The console maps it automatically to that key. Example for `unifi_get_client_details`:
```bash
  14:1b:4f:dc:5b:cf
  ```
* Press Enter to skip JSON and the console will interactively prompt for missing required fields (e.g., it will ask for `mac_address`).

Notes:

* For arrays or nested objects, paste valid JSON.
* The console shows a schema hint (when available). Defaults from the schema are used if you press Enter on a prompt.
* If validation fails, the console extracts required fields from the error and prompts for them.

### Environment setup

Using UV (recommended):

```bash
# 1) Install UV if needed
curl -fsSL https://astral.sh/uv/install.sh | bash

# 2) Create and activate a virtual environment
uv venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows PowerShell: .venv\\Scripts\\Activate.ps1

# 3) Install project and dependencies
uv pip install -e .

# 4) (If you see "ModuleNotFoundError: mcp") install the MCP SDK explicitly
uv pip install mcp

# 5) Run the console
python devtools/dev_console.py
```

Using Python venv + pip:

```bash
# 1) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows PowerShell: .venv\\Scripts\\Activate.ps1

# 2) Install project (and dependencies)
pip install -e .

# 3) (If you see "ModuleNotFoundError: mcp") install the MCP SDK explicitly
pip install mcp

# 4) Run the console
python devtools/dev_console.py
```

---

## Security Considerations

These tools will give any LLM or agent configured to use them full access to your UniFi Network Controller. While this can be for very useful for analysis and configuration of your network, there is potential for abuse if not configured correctly. By default, all tools that can modify state or disrupt availability are disabled, and must be explicitly enabled in the `src/config/config.yaml` file. When you have a use case for a tool, like updating a firewall policy, you must explicitly enable it in the `src/config/config.yaml` and restart the MCP server. The tools are build directly on the UniFi Network Controller API, so they can operate with similar functionality to the UniFi web interface.

### General Recommendations

* Use LM Studio or Ollama run tool capable models locally if possible. This is the recommended and safest way to use these tools.
* If you opt to use cloud based LLMs, like Claude, Gemini, and ChatGPT, for analysis. Enable read-only tools, which is the default configuration.
* Create, update, and removal tools should be used with caution and only enabled when necessary.
* Do not host outside of your network unless using a secure reverse proxy like Cloudflare Tunnel or Ngrok. Even then, an additional layer of authentication is recommended.

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

## Testing

The project includes comprehensive unit and integration tests for all features, including the UniFi OS controller type detection.

### Running Tests Locally

**Prerequisites:**
```bash
# Install UV (if not already installed)
curl -fsSL https://astral.sh/uv/install.sh | bash

# Clone the repository
git clone https://github.com/sirkirby/unifi-network-mcp.git
cd unifi-network-mcp

# Install dependencies (includes test dependencies)
uv sync
```

**Run all tests:**
```bash
uv run pytest tests/ -v
```

**Run only unit tests:**
```bash
uv run pytest tests/unit/ -v
```

**Run only integration tests:**
```bash
uv run pytest tests/integration/ -v
```

**Run with coverage report:**
```bash
uv run pytest tests/ --cov=src --cov-report=term-missing
```

**Run specific test file:**
```bash
uv run pytest tests/unit/test_path_detection.py -v
```

**Run specific test:**
```bash
uv run pytest tests/unit/test_path_detection.py::TestPathDetection::test_detects_unifi_os_correctly -v
```

### Test Structure

```
tests/
├── conftest.py              # Pytest configuration
├── unit/                    # Unit tests (fast, isolated)
│   └── test_path_detection.py
└── integration/             # Integration tests (slower, with mocks)
    └── test_path_interceptor.py
```

### Test Coverage

The test suite includes:
- **8 unit tests** for UniFi OS path detection logic
- **5 integration tests** for path interception and manual override
- Coverage for automatic detection, manual override, retry logic, and error handling

All tests use `pytest-asyncio` for async support and `aioresponses` for HTTP mocking.

### Continuous Integration

Tests run automatically on every push and pull request via GitHub Actions. See [`.github/workflows/test.yml`](.github/workflows/test.yml) for the CI configuration.

---

## Contributing: Releasing / Publishing

This project uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) via a [GitHub Actions workflow](.github/workflows/publish-to-pypi.yml).

**To publish a new version:**

1. **Bump the `version`** in `pyproject.toml`.
2. **Create a new GitHub Release:** Draft a new release on GitHub, tagging it with the *exact* same version number (e.g., `v0.2.0` if the version in `pyproject.toml` is `0.2.0`).

Once published, users can install it via:

```bash
uv pip install unifi-network-mcp
```

## Local Development

Docker:

```bash
docker compose up --build
```

Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

---

### License

[MIT](LICENSE)

[commits-shield]: https://img.shields.io/github/commit-activity/y/sirkirby/unifi-network-mcp?style=for-the-badge
[commits]: https://github.com/sirkirby/unifi-network-mcp/commits/main
[license-shield]: https://img.shields.io/github/license/sirkirby/unifi-network-mcp.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-sirkirby-blue.svg?style=for-the-badge

[releases]: https://github.com/sirkirby/unifi-network-mcp/releases
[release-shield]: https://img.shields.io/github/v/release/sirkirby/unifi-network-mcp?style=flat

[issues-shield]: https://img.shields.io/github/issues/sirkirby/unifi-network-mcp?style=flat
[issues-link]: https://github.com/sirkirby/unifi-network-mcp/issues

[test-badge]: https://github.com/sirkirby/unifi-network-mcp/actions/workflows/test.yml/badge.svg
[test-workflow]: https://github.com/sirkirby/unifi-network-mcp/actions/workflows/test.yml

[validate-badge]: https://github.com/sirkirby/unifi-network-mcp/actions/workflows/publish-to-pypi.yml/badge.svg
[validate-workflow]: https://github.com/sirkirby/unifi-network-mcp/actions/workflows/publish-to-pypi.yml

[validate-docker-badge]: https://github.com/sirkirby/unifi-network-mcp/actions/workflows/docker-publish.yml/badge.svg
[validate-docker-workflow]: https://github.com/sirkirby/unifi-network-mcp/actions/workflows/docker-publish.yml
