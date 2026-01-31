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
* [Code Execution Mode](#code-execution-mode)
  * [Overview](#overview)
  * [Context Optimization](#context-optimization)
  * [Tool Index](#tool-index)
  * [Tool Execution](#tool-execution)
* [Runtime Configuration](#runtime-configuration)
* [Diagnostics (Advanced Logging)](#diagnostics-advanced-logging)
* [Developer Console (Local Tool Tester)](#developer-console-local-tool-tester)
* [Security Considerations](#security-considerations)
* [📚 Tool Catalog](#-tool-catalog)
* [📖 Documentation](#-documentation)
* [Testing](#testing)
* [Local Development](#local-development)
* [Contributing: Releasing / Publishing](#contributing-releasing--publishing)

---

## Features

* Full catalog of UniFi controller operations – firewall, traffic-routes, port-forwards, QoS, VPN, WLANs, stats, devices, clients **and more**.
* All mutating tools require `confirm=true` so nothing can change your network by accident.
* **Workflow automation friendly** – set `UNIFI_AUTO_CONFIRM=true` to skip confirmation prompts (ideal for n8n, Make, Zapier).
* Works over **stdio** (FastMCP). Optional SSE HTTP endpoint can be enabled via config.
* **Code execution mode** with tool index, async operations, and TypeScript examples.
* One-liner launch via the console-script **`unifi-network-mcp`**.
* Idiomatic Python ≥ 3.13, packaged with **pyproject.toml** and ready for PyPI.

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

---

## Code Execution Mode

The UniFi Network MCP server supports **code-execution mode**, enabling agents to write code that interacts with tools programmatically. This approach reduces token usage by up to 98% compared to traditional tool calls, as agents can filter and transform data in code before presenting results.

### Overview

Code execution mode consists of three key components:

1. **Tool Index** - Machine-readable catalog of all available tools with JSON schemas
2. **Async Operations** - Background job execution for long-running operations
3. **Reference Implementations** - Example clients showing code-execution patterns

This implementation follows the patterns described in [Anthropic's Code Execution with MCP article](https://www.anthropic.com/engineering/code-execution-with-mcp).

### 🚀 Context Optimization (New in v0.2.0)

The server now supports **lazy tool registration** to dramatically reduce LLM context usage.

**🎯 DEFAULT: Lazy Mode (lazy)** ⭐⭐⭐ **Active in v0.2.0!**
- Registers only 3 meta-tools initially
- ~200 tokens consumed (96% reduction!)
- Tools loaded automatically on first use
- **Seamless UX** - no manual discovery needed
- **Best of both worlds!**
- **Active by default** - no configuration needed

**Eager Mode (eager):**
- Registers all 67 tools immediately
- ~5,000 tokens consumed for tool schemas
- All tools visible in context from start
- **Best for:** Dev console, automation scripts
- **How to enable:** Set `UNIFI_TOOL_REGISTRATION_MODE=eager`

**Meta-Only Mode (meta_only):**
- Registers only 3 meta-tools initially
- ~200 tokens consumed (96% reduction!)
- Requires `unifi_tool_index` call for discovery
- **Best for:** Maximum control
- **How to enable:** Set `UNIFI_TOOL_REGISTRATION_MODE=meta_only`

**Upgrading from v0.1.x?**

If you're upgrading and want to restore the previous behavior (all tools registered immediately), add this to your config:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "uv",
      "args": ["--directory", "/path/to/unifi-network-mcp", "run", "python", "-m", "src.main"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "password",
        "UNIFI_TOOL_REGISTRATION_MODE": "eager"
      }
    }
  }
}
```

**Default behavior (lazy mode - recommended):**

```json
{
  "mcpServers": {
    "unifi": {
      "command": "uv",
      "args": ["--directory", "/path/to/unifi-network-mcp", "run", "python", "-m", "src.main"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "password"
        // UNIFI_TOOL_REGISTRATION_MODE defaults to "lazy" - no need to set!
      }
    }
  }
}
```

**Result:** Claude starts with minimal context, tools load transparently when called - 96% token savings with zero UX compromise!

### Tool Index

The server exposes a special `unifi_tool_index` tool that returns a complete list of all registered tools with their schemas:

```json
{
  "name": "unifi_tool_index",
  "arguments": {}
}
```

**Response:**
```json
{
  "tools": [
    {
      "name": "unifi_list_clients",
      "schema": {
        "name": "unifi_list_clients",
        "description": "List all network clients",
        "input_schema": {
          "type": "object",
          "properties": {
            "filter": {"type": "string"},
            "limit": {"type": "integer"}
          }
        }
      }
    },
    ...
  ]
}
```

**Use Cases:**
- Programmatic tool discovery
- Wrapper/SDK generation
- Dynamic client configuration
- IDE autocomplete support

### Tool Execution

The server provides two execution modes for discovered tools:

**Single Tool Execution (synchronous):**
```json
{
  "name": "unifi_execute",
  "arguments": {
    "tool": "unifi_list_clients",
    "arguments": {}
  }
}
```

**Batch Execution (parallel, async):**

For bulk operations or long-running tasks, use batch mode:

```json
{
  "name": "unifi_batch",
  "arguments": {
    "operations": [
      {"tool": "unifi_get_client_details", "arguments": {"mac": "aa:bb:cc:dd:ee:ff"}},
      {"tool": "unifi_get_client_details", "arguments": {"mac": "11:22:33:44:55:66"}}
    ]
  }
}
```

**Response:**
```json
{
  "jobs": [
    {"index": 0, "tool": "unifi_get_client_details", "jobId": "af33b233cbdc860c"},
    {"index": 1, "tool": "unifi_get_client_details", "jobId": "bf44c344dcde971d"}
  ],
  "message": "Started 2 operation(s). Use unifi_batch_status to check progress."
}
```

**Check batch status:**
```json
{
  "name": "unifi_batch_status",
  "arguments": {
    "jobIds": ["af33b233cbdc860c", "bf44c344dcde971d"]
  }
}
```

**Response:**
```json
{
  "jobs": [
    {"jobId": "af33b233cbdc860c", "status": "done", "result": {...}},
    {"jobId": "bf44c344dcde971d", "status": "done", "result": {...}}
  ]
}
```

**Notes:**
- Use `unifi_execute` for single operations (returns result directly)
- Use `unifi_batch` + `unifi_batch_status` for parallel/bulk operations
- Jobs are stored in-memory only (no persistence)
- Job IDs are unique per server session

### Using with Claude Desktop

Claude Desktop has built-in code execution that automatically uses the tool index:

```
You: "Show me the top 10 wireless clients by traffic, excluding guest networks"
```

Claude will:
1. Query `unifi_tool_index` to discover tools
2. Call `unifi_list_clients` to fetch data
3. Write and execute code to filter/sort in its sandbox
4. Show you only the final top 10 results

**Token savings:** Instead of processing 500+ clients in context, Claude processes them in code and shows only the summary.

See [`examples/CLAUDE_DESKTOP.md`](examples/CLAUDE_DESKTOP.md) for detailed usage guide.

### Python Client Examples

Practical examples showing programmatic usage:

```python
from mcp import ClientSession, stdio_client

# Discover tools
tools = await session.call_tool("unifi_tool_index", {})

# Execute a single tool (returns result directly)
result = await session.call_tool("unifi_execute", {
    "tool": "unifi_list_clients",
    "arguments": {}
})

# Batch execution for parallel operations
batch = await session.call_tool("unifi_batch", {
    "operations": [
        {"tool": "unifi_get_client_details", "arguments": {"mac": "..."}},
        {"tool": "unifi_get_device_details", "arguments": {"mac": "..."}}
    ]
})

# Check batch status
status = await session.call_tool("unifi_batch_status", {
    "jobIds": [j["jobId"] for j in batch["jobs"]]
})
```

**Three complete examples:**
- `query_tool_index.py` - Discover available tools
- `use_async_jobs.py` - Batch operations and status checking
- `programmatic_client.py` - Build custom Python clients

See [`examples/python/README.md`](examples/python/README.md) for complete examples.

### MCP Identity

The server advertises its capabilities via an MCP identity file at [`.well-known/mcp-server.json`](.well-known/mcp-server.json):

```json
{
  "name": "unifi-network-mcp",
  "version": "0.2.0",
  "transports": ["stdio", "http+sse"],
  "capabilities": {
    "tools": true,
    "tool_index": true,
    "batch_operations": true
  },
  "features": {
    "tool_index": {
      "tool": "unifi_tool_index"
    },
    "execution": {
      "tool": "unifi_execute"
    },
    "batch_operations": {
      "start_tool": "unifi_batch",
      "status_tool": "unifi_batch_status"
    }
  }
}
```

This enables:
- Programmatic capability discovery
- Future MCP registry integration
- Client auto-configuration

---

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
| `UNIFI_MCP_HOST` | HTTP SSE bind address (default `0.0.0.0`) |
| `UNIFI_MCP_PORT` | HTTP SSE bind port (default `3000`) |
| `UNIFI_AUTO_CONFIRM` | Set `true` to auto-confirm all mutating operations (skips preview step). Ideal for workflow automation (n8n, Make, Zapier). Default `false` |
| `UNIFI_TOOL_REGISTRATION_MODE` | Tool loading mode: `lazy` (default), `eager`, or `meta_only`. See [Context Optimization](#context-optimization) |
| `UNIFI_ENABLED_CATEGORIES` | Comma-separated list of tool categories to load (eager mode). See table below |
| `UNIFI_ENABLED_TOOLS` | Comma-separated list of specific tool names to register (eager mode) |
| `UNIFI_MCP_ALLOWED_HOSTS` | Comma-separated list of allowed hostnames for reverse proxy support. Required when running behind Nginx/Cloudflare/etc. Default `localhost,127.0.0.1` |

### Tool Categories (for UNIFI_ENABLED_CATEGORIES)

When using eager mode with category filtering, these are the valid category names:

| Category | Description | Example Tools |
|----------|-------------|---------------|
| `clients` | Client listing, blocking, guest auth | `unifi_list_clients`, `unifi_block_client` |
| `config` | Configuration management | - |
| `devices` | Device listing, reboot, locate, upgrade | `unifi_list_devices`, `unifi_reboot_device` |
| `events` | Events and alarms | `unifi_list_events`, `unifi_list_alarms` |
| `firewall` | Firewall rules and groups | `unifi_list_firewall_rules`, `unifi_create_firewall_rule` |
| `hotspot` | Vouchers for guest network | `unifi_list_vouchers`, `unifi_create_voucher` |
| `network` | Network/VLAN management | `unifi_list_networks`, `unifi_create_network` |
| `port_forwards` | Port forwarding rules | `unifi_list_port_forwards` |
| `qos` | QoS/traffic shaping rules | `unifi_list_qos_rules`, `unifi_create_qos_rule` |
| `routing` | Static routes (V1 API) | `unifi_list_routes`, `unifi_create_route` |
| `stats` | Statistics and metrics | `unifi_get_client_stats`, `unifi_get_device_stats` |
| `system` | System info, health, settings | `unifi_get_system_info`, `unifi_get_network_health` |
| `traffic_routes` | Policy-based routing (V2 API) | `unifi_list_traffic_routes` |
| `usergroups` | Bandwidth profiles/user groups | `unifi_list_usergroups`, `unifi_create_usergroup` |
| `vpn` | VPN servers and clients | `unifi_list_vpn_servers`, `unifi_list_vpn_clients` |

**Example usage:**
```bash
# Load only client and system tools
export UNIFI_TOOL_REGISTRATION_MODE=eager
export UNIFI_ENABLED_CATEGORIES=clients,system

# Or load specific tools only
export UNIFI_ENABLED_TOOLS=unifi_list_clients,unifi_list_devices,unifi_get_system_info
```

**Note:** Tools may also be filtered by the `permissions` section in config.yaml (e.g., `clients.update: false` blocks mutating client tools).

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
* **Shows ALL tools** (including those disabled by permissions) with status indicators.
* On selection, shows a schema hint (when available) and prompts for JSON arguments.
* Executes the tool via the MCP server and prints the JSON result.
* Prevents execution of disabled tools with helpful permission guidance.

**New in v0.2.0:** The dev console now displays all 64 tools regardless of permission settings:
* Enabled tools are marked with ✓
* Disabled tools are marked with ✗ [DISABLED]
* Attempting to run a disabled tool shows permission instructions
* See [docs/permissions.md](docs/permissions.md) for how to enable specific tools

Tips:

* Combine with Diagnostics for deep visibility: set `UNIFI_MCP_DIAGNOSTICS=true` (or enable in `src/config/config.yaml`).
* For mutating tools, set `{"confirm": true}` in the JSON input when prompted.
* To enable disabled tools, set environment variables like `UNIFI_PERMISSIONS_NETWORKS_CREATE=true` before running the console.

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

These tools will give any LLM or agent configured to use them full access to your UniFi Network Controller. While this can be very useful for analysis and configuration of your network, there is potential for abuse if not configured correctly. By default, all tools that can modify state or disrupt availability are disabled and must be explicitly enabled via **environment variables**. The tools are built directly on the UniFi Network Controller API, so they can operate with similar functionality to the UniFi web interface.

### Permission System 🔐 **NEW in v0.2.0**

The server includes a comprehensive permission system with **safe defaults**:

**Disabled by Default (High-Risk):**
- Network creation/modification (`unifi_create_network`, `unifi_update_network`)
- Wireless configuration (`unifi_create_wlan`, `unifi_update_wlan`)
- Device operations (`unifi_adopt_device`, `unifi_upgrade_device`, `unifi_reboot_device`)
- Client operations (`unifi_block_client`, `unifi_authorize_guest`)

**Enabled by Default (Lower Risk):**
- Firewall policies, traffic routes, port forwards, QoS rules
- All read-only operations

**How to Enable Permissions:**

**Recommended: Environment Variables** (works with Docker, PyPI installs, uvx)

```bash
# For Claude Desktop - add to env section:
"env": {
  "UNIFI_PERMISSIONS_NETWORKS_CREATE": "true",
  "UNIFI_PERMISSIONS_DEVICES_UPDATE": "true"
}

# For command line:
export UNIFI_PERMISSIONS_NETWORKS_CREATE=true
export UNIFI_PERMISSIONS_DEVICES_UPDATE=true

# For Docker:
docker run -e UNIFI_PERMISSIONS_NETWORKS_CREATE=true ...
```

**Alternative: Config File** (only for local git clone development)

If you're running from a local git clone, you can modify `src/config/config.yaml` and regenerate the manifest:

```bash
# Edit permissions in src/config/config.yaml
make manifest  # Regenerate tool manifest
# Restart the server
```

**Note:** Most users should use environment variables. Config file changes require rebuilding the manifest and are primarily for local development.

See [docs/permissions.md](docs/permissions.md) for complete documentation including all permission variables.

### General Recommendations

* Use LM Studio or Ollama to run tool-capable models locally if possible. This is the recommended and safest way to use these tools.
* If you opt to use cloud-based LLMs like Claude, Gemini, and ChatGPT for analysis, stick with read-only tools (the default configuration).
* **Review permissions carefully** before enabling high-risk operations. Use environment variables for runtime control.
* Create, update, and delete tools should be used with caution and only enabled when necessary.
* Do not host outside of your network unless using a secure reverse proxy like Cloudflare Tunnel or Ngrok. Even then, an additional layer of authentication is recommended.
* **Reverse Proxy Configuration:** When running behind a reverse proxy, set `UNIFI_MCP_ALLOWED_HOSTS` to include your external domain (e.g., `localhost,127.0.0.1,unifi-mcp.example.com`) to bypass FastMCP's DNS rebinding protection.

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
* `unifi_set_client_ip_settings`

### Events & Alarms

* `unifi_list_events`
* `unifi_list_alarms`
* `unifi_archive_alarm`
* `unifi_archive_all_alarms`
* `unifi_get_event_types`

### Routing (Static Routes)

* `unifi_list_routes`
* `unifi_get_route_details`
* `unifi_create_route`
* `unifi_update_route`
* `unifi_list_active_routes`

### Hotspot (Vouchers)

* `unifi_list_vouchers`
* `unifi_get_voucher_details`
* `unifi_create_voucher`
* `unifi_revoke_voucher`

### User Groups

* `unifi_list_usergroups`
* `unifi_get_usergroup_details`
* `unifi_create_usergroup`
* `unifi_update_usergroup`

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

## 📖 Documentation

Comprehensive documentation is available in the [docs/](docs/) directory:

### Quick Links

- **[Documentation Index](docs/README.md)** - Complete documentation overview
- **[Quick Start Guide](QUICKSTART.md)** - Get started in 5 minutes

### Key Guides

- **[Context Optimization](docs/context-optimization-comparison.md)** - Visual comparison of modes
- **[Tool Index API](docs/tool-index.md)** - Programmatic tool discovery

---

## Testing

The project includes comprehensive unit and integration tests for all features, including async jobs and lazy tool loading.

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

### Option 1: Using Docker

Test with Docker and Claude Desktop:

```bash
docker compose up --build
```

Then configure Claude Desktop to use the Docker container (see [Configuration](#configuration) above).

### Option 2: Using Python/uv (Recommended for Development)

For local development and testing without Docker:

**1. Install dependencies:**

```bash
# Install UV (if not already installed)
curl -fsSL https://astral.sh/uv/install.sh | bash

# Clone and setup
git clone https://github.com/sirkirby/unifi-network-mcp.git
cd unifi-network-mcp

# Install dependencies
uv sync
```

**2. Configure environment:**

```bash
# Create .env file (or set environment variables)
cat > .env << EOF
UNIFI_HOST=your-controller-ip
UNIFI_USERNAME=your-username
UNIFI_PASSWORD=your-password
UNIFI_PORT=443
UNIFI_SITE=default
UNIFI_VERIFY_SSL=false
EOF
```

**3. Test with the dev console (interactive):**

```bash
# Launch interactive tool tester
uv run python devtools/dev_console.py

# You'll see a menu of all tools including:
# - unifi_tool_index (list all tools with schemas)
# - unifi_execute (run any discovered tool)
# - unifi_batch / unifi_batch_status (parallel operations)
# - All 80+ UniFi tools (clients, devices, networks, etc.)
```

**4. Test with Python examples:**

```bash
# Query the tool index
uv run python examples/python/query_tool_index.py

# Test async jobs
uv run python examples/python/use_async_jobs.py

# Use the programmatic client
uv run python examples/python/programmatic_client.py
```

**5. Test with Claude Desktop (local Python server):**

Update your Claude Desktop config to use the local Python server instead of Docker:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/unifi-network-mcp",
        "run",
        "python",
        "-m",
        "src.main"
      ],
      "env": {
        "UNIFI_HOST": "your-controller-ip",
        "UNIFI_USERNAME": "your-username",
        "UNIFI_PASSWORD": "your-password"
      }
    }
  }
}
```

Then restart Claude Desktop and test:
- "What UniFi tools are available?" (uses `unifi_tool_index`)
- "Show me my top 10 wireless clients" (uses code execution mode)
- "List all my UniFi devices"

**6. Test with LM Studio or other local LLMs:**

For testing with local LLMs that support MCP, you can run the server in stdio mode:

```bash
# Start the MCP server
uv run python -m src.main

# The server will listen on stdin/stdout for MCP protocol messages
# Configure your LLM client to use this as an MCP server
```

**7. Run unit tests:**

```bash
# Run all tests
uv run pytest tests/ -v

# Run just async job tests (new in v0.2.0)
uv run pytest tests/test_async_jobs.py -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing
```

### Alternative: Traditional venv

If you prefer not to use uv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python devtools/dev_console.py
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
