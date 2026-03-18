# UniFi Network MCP Server

<p align="center">
  <img src="../../assets/hero-network.svg" alt="UniFi Network MCP Server" width="720">
</p>

MCP server exposing 91 UniFi Network Controller tools for LLMs, agents, and automation platforms. Query clients, devices, firewall rules, VLANs, VPNs, stats, and more — with safe-by-default permissions and preview-before-confirm for all mutations.

## Install

### Claude Code (recommended)

The plugin installs the MCP server, an agent skill for tool discovery, and a guided setup command:

```
/plugin marketplace add sirkirby/unifi-mcp
/plugin install unifi-network@unifi-plugins
```

Then run the interactive setup to configure your controller connection:

```
/unifi-network:setup
```

This walks you through entering your controller host, credentials, and permission preferences — then writes everything to `.claude/settings.json` so it persists across sessions. Restart Claude Code after setup to connect.

### PyPI / Docker

```bash
# PyPI
uvx unifi-network-mcp
# or: pip install unifi-network-mcp

# Docker
docker pull ghcr.io/sirkirby/unifi-network-mcp:latest

# From source
git clone https://github.com/sirkirby/unifi-mcp.git
cd unifi-mcp && uv sync
```

## Configure

Set these environment variables (or create a `.env` file). If you used `/unifi-network:setup`, this is already done.

```bash
# Server-specific variables (recommended)
UNIFI_NETWORK_HOST=192.168.1.1      # Controller IP or hostname
UNIFI_NETWORK_USERNAME=admin         # Local admin username
UNIFI_NETWORK_PASSWORD=your-password # Admin password
# Optional:
# UNIFI_NETWORK_API_KEY=             # UniFi API key (experimental — read-only, subset of tools)
# UNIFI_NETWORK_PORT=443             # Controller HTTPS port
# UNIFI_NETWORK_SITE=default         # UniFi site name
# UNIFI_NETWORK_VERIFY_SSL=false     # SSL certificate verification
```

**Fallback:** Existing `UNIFI_*` variables (e.g., `UNIFI_HOST`) continue to work. The server checks for `UNIFI_NETWORK_*` first and falls back to `UNIFI_*` if the server-specific variable is not set. For single-controller setups, the shared variables are all you need.

## Run

```bash
# stdio transport (default — for Claude Desktop, LM Studio, etc.)
unifi-network-mcp

# Docker
docker run -i --rm \
  -e UNIFI_NETWORK_HOST=192.168.1.1 \
  -e UNIFI_NETWORK_USERNAME=admin \
  -e UNIFI_NETWORK_PASSWORD=secret \
  ghcr.io/sirkirby/unifi-network-mcp:latest
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```jsonc
{
  "mcpServers": {
    "unifi": {
      "command": "uvx",
      "args": ["unifi-network-mcp"],
      "env": {
        "UNIFI_NETWORK_HOST": "192.168.1.1",
        "UNIFI_NETWORK_USERNAME": "admin",
        "UNIFI_NETWORK_PASSWORD": "your-password"
      }
    }
  }
}
```

## Documentation

- [Configuration](docs/configuration.md) — Full env var reference, YAML config, controller type detection
- [Permissions](docs/permissions.md) — Permission system, category defaults, how to enable high-risk tools
- [Tool Catalog](docs/tools.md) — All 91 tools organized by category
- [Transports](docs/transports.md) — stdio, Streamable HTTP, and SSE setup
- [Troubleshooting](docs/troubleshooting.md) — Connection issues, SSL, missing tools

## Development

```bash
cd apps/network
make test         # Run tests
make lint         # Lint
make format       # Format
make manifest     # Regenerate tools_manifest.json
make pre-commit   # All of the above
```

See the root [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full monorepo workflow.

## License

[MIT](../../LICENSE)
