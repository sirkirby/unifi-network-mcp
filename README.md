# UniFi MCP

MCP servers that expose UniFi controller functionality as structured tools for LLMs, agents, and automation platforms.

[![PyPI](https://img.shields.io/pypi/v/unifi-network-mcp)](https://pypi.org/project/unifi-network-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)

## Servers

| Server | Status | Tools | Package |
|--------|--------|-------|---------|
| [Network](apps/network/) | Stable | 91 | [`unifi-network-mcp`](https://pypi.org/project/unifi-network-mcp/) |
| [Protect](apps/protect/) | Beta | 34 | `unifi-protect-mcp` |
| Access | Planned | — | — |

## What is this?

UniFi MCP is a collection of [Model Context Protocol](https://modelcontextprotocol.io/) servers that let AI assistants and automation tools interact with Ubiquiti UniFi controllers. Each server targets a specific UniFi application (Network, Protect, Access) and exposes its functionality as MCP tools — queryable, composable, and safe by default.

## Quick Start

The fastest way to run the servers:

```bash
# Network server
uvx unifi-network-mcp

# Protect server
uvx unifi-protect-mcp
```

For Claude Desktop, add to your `claude_desktop_config.json`:

```jsonc
{
  "mcpServers": {
    "unifi-network": {
      "command": "uvx",
      "args": ["unifi-network-mcp"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "your-password"
      }
    },
    "unifi-protect": {
      "command": "uvx",
      "args": ["unifi-protect-mcp"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "your-password"
      }
    }
  }
}
```

## Configuration

Set these environment variables (or use a `.env` file):

| Variable | Required | Description |
|----------|----------|-------------|
| `UNIFI_HOST` | Yes | Controller IP or hostname |
| `UNIFI_USERNAME` | Yes | Local admin username |
| `UNIFI_PASSWORD` | Yes | Admin password |
| `UNIFI_API_KEY` | No | Official UniFi API key (dual auth) |

For the full configuration reference including permissions, transports, and advanced options, see the [Network server docs](apps/network/docs/configuration.md).

## Architecture

This is a monorepo with shared packages:

```
apps/
  network/          # UniFi Network MCP server (stable, 91 tools)
  protect/          # UniFi Protect MCP server (beta, 34 tools)
packages/
  unifi-core/       # Shared UniFi connectivity (auth, detection, retry)
  unifi-mcp-shared/ # Shared MCP patterns (permissions, confirmation, lazy loading)
docs/               # Ecosystem-level documentation
```

Each server in `apps/` is an independent Python package that depends on the shared packages. The shared packages ensure consistent behavior across all servers — same permission model, same confirmation flow, same lazy tool loading.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Roadmap

The Protect server is in beta. An Access server is planned for a future phase. See the [ecosystem design spec](docs/superpowers/specs/) for the full roadmap.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow, including how to work with the monorepo, run tests, and submit PRs.

## License

[MIT](LICENSE)
