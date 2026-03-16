# Architecture

## Monorepo Structure

```
unifi-mcp/
  apps/
    network/              # UniFi Network MCP server
  packages/
    unifi-core/           # Shared UniFi controller connectivity
    unifi-mcp-shared/     # Shared MCP server patterns
  docs/                   # Ecosystem-level docs and plans
  docker/                 # Docker compose for network server
  .well-known/            # MCP identity file
```

The workspace is managed by [uv](https://docs.astral.sh/uv/) with `pyproject.toml` at the root defining workspace members. Each app and package is an independent Python package with its own `pyproject.toml`.

## Package Responsibilities

### unifi-core

Low-level UniFi controller connectivity. No MCP dependency.

| Module | Purpose |
|--------|---------|
| `auth.py` | Authentication (local credentials, API key, dual auth) |
| `connection.py` | Connection manager (aiohttp session, auto-reconnect) |
| `detection.py` | Controller type detection (UniFi OS vs standalone) |
| `retry.py` | Retry logic with exponential backoff |
| `exceptions.py` | Shared exception types |

Used by: `apps/network`, and future `apps/protect`, `apps/access`.

### unifi-mcp-shared

Shared MCP server patterns. Depends on `mcp` SDK and `omegaconf`.

| Module | Purpose |
|--------|---------|
| `permissions.py` | Permission checking (category/action, env var overrides) |
| `confirmation.py` | Preview-then-confirm flow for mutations |
| `lazy_tools.py` | Lazy tool loading (on-demand registration) |
| `tool_loader.py` | Tool module import and registration |
| `meta_tools.py` | Meta-tools (tool_index, execute, batch) |
| `config.py` | OmegaConf config loading with env var interpolation |
| `formatting.py` | Response formatting helpers |

Used by: `apps/network`, and future server apps.

### apps/network

The UniFi Network MCP server. 91 tools across 16 categories covering firewall, clients, devices, networks, VPNs, routing, stats, and more.

- `src/unifi_network_mcp/` — server code
  - `main.py` — entry point, tool registration, transport dispatch
  - `runtime.py` — singleton factories (`@lru_cache`)
  - `managers/` — domain logic (one per category)
  - `tools/` — thin tool wrappers (delegate to managers)
  - `config/config.yaml` — default configuration
  - `tools_manifest.json` — pre-generated tool metadata
- `tests/` — unit and integration tests
- `Makefile` — app-level development commands
- `Dockerfile` — container build

## Layering

```
MCP Client (Claude Desktop, LM Studio, automation)
    |
    v  MCP Protocol (stdio / Streamable HTTP / SSE)
    |
FastMCP Server (main.py)
    |
    v  Tool registration (permissioned_tool decorator)
    |
Tool Functions (tools/*.py)           <- thin wrappers
    |
    v  Manager method calls
    |
Manager Layer (managers/*.py)         <- domain logic
    |
    v  unifi-core API calls
    |
Connection Manager (unifi-core)
    |
    v  aiohttp + controller detection
    |
UniFi Controller (REST API)
```

Rules:
- Tool functions must not contain business logic
- Managers must not import from tools (no circular deps)
- All controller communication flows through the connection manager
- All shared objects use `@lru_cache` singleton factories in `runtime.py`

## Adding a New Server

To add a new UniFi application server (e.g., Protect):

1. **Create app directory:** `apps/protect/`
2. **Create `pyproject.toml`** depending on `unifi-core` and `unifi-mcp-shared`
3. **Add to workspace** in root `pyproject.toml` (`apps/*` is already a glob)
4. **Follow the network server pattern:**
   - `src/unifi_protect_mcp/main.py` — entry point
   - `src/unifi_protect_mcp/managers/` — domain logic
   - `src/unifi_protect_mcp/tools/` — tool wrappers
   - `src/unifi_protect_mcp/config/config.yaml` — defaults
5. **Reuse shared packages:**
   - `unifi_core` for controller connectivity and auth
   - `unifi_mcp_shared` for permissions, confirmation, lazy loading, config
6. **Add Makefile** targets (test, lint, format, manifest)
7. **Add to root Makefile** delegation targets
8. **Add Dockerfile** following the network server pattern

## Shared Patterns

All servers share these patterns via `unifi-mcp-shared`:

- **Permissions:** Category/action model with env var overrides, safe defaults
- **Confirmation:** Preview-then-confirm for all mutations, auto-confirm for automation
- **Lazy tool loading:** Meta-tools registered first, others loaded on demand (~200 vs ~5000 tokens)
- **Config:** OmegaConf YAML with `${oc.env:VAR,default}` interpolation
- **Tool response contract:** `{"success": bool, "data": ...}` or `{"success": false, "error": "..."}`
