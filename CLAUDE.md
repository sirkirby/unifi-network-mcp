## Metadata

- **Project:** unifi-network-mcp (monorepo)
- **Status:** Adopted
- **Version:** 1.0.0
- **Last Updated:** 2026-03-16
- **Tech Stack:** Python 3.13+, FastMCP, aiounifi, aiohttp, OmegaConf, jsonschema, ruff, pytest, Docker
- **License:** MIT
- **Repository:** https://github.com/sirkirby/unifi-network-mcp

---

## 0. Monorepo Layout

This repository is a **uv workspace monorepo** with one application and two shared packages:

```
unifi-network-mcp/
  apps/
    network/                          # MCP server application
      src/unifi_network_mcp/          # Main package
      tests/                          # Network server tests
      Makefile                        # App-level targets
      pyproject.toml                  # App build config
  packages/
    unifi-core/                       # Low-level controller abstractions
      src/unifi_core/                 # auth, connection, detection, retry
      tests/
    unifi-mcp-shared/                 # Shared MCP utilities
      src/unifi_mcp_shared/           # permissions, confirmation, meta_tools, lazy_tools
      tests/
  Makefile                            # Root: delegates to app/package targets
  pyproject.toml                      # Workspace root
  uv.lock                             # Single lockfile for all packages
```

**Import patterns:**
- `from unifi_network_mcp.<module>` -- network server code
- `from unifi_mcp_shared.<module>` -- shared MCP utilities (permissions, confirmation, tool loading)
- `from unifi_core.<module>` -- low-level controller abstractions (auth, connection, retry)

**Build commands (root Makefile delegates):**
```bash
make test              # Run ALL tests (core + shared + network)
make core-test         # Run unifi-core tests only
make shared-test       # Run unifi-mcp-shared tests only
make network-test      # Run network server tests only
make lint              # Lint network server
make format            # Format network server
make network-manifest  # Regenerate tools manifest
make pre-commit        # format + lint + test
```

---

## 1. Scope and Non-Goals (Hard Constraints)

### 1.1 Purpose

unifi-network-mcp is a **Model Context Protocol (MCP) server** that exposes UniFi Network Controller functionality as 80+ structured tools. It enables LLMs, agents, and automation platforms to query, analyze, and (when authorized) modify network configuration through the MCP protocol.

### 1.2 Explicit Non-Goals

unifi-network-mcp is **not**:

- a general-purpose network management framework
- a UniFi controller replacement or admin dashboard
- a real-time monitoring or alerting service
- a CI/CD pipeline runner or deployment tool
- a web application with a frontend UI (the dev console is a debugging REPL only)
- a database or persistent storage layer (all state lives on the UniFi controller)

### 1.3 Key Definitions

**"Secure by default"** means:
- High-risk operations (network/device/client modification) are disabled unless explicitly enabled via environment variables or config
- All mutations require a two-step preview-then-confirm flow
- Delete operations are denied by default and require explicit opt-in via environment variable or config
- Read-only actions are allowed by default

**"Context-optimized"** means:
- Lazy tool loading is the default mode (~200 tokens vs ~5,000 for eager)
- Tools are discoverable via meta-tools without being registered
- The pre-generated manifest (`apps/network/src/unifi_network_mcp/tools_manifest.json`) avoids runtime import overhead
- Tool responses minimize token usage with essential fields only

**"Async throughout"** means:
- All I/O-bound operations MUST use `async`/`await`
- No synchronous blocking calls in tool implementations or managers
- `asyncio.run()` MUST NOT be called from within an async context

---

## 2. Golden Paths (Copy These Patterns)

All changes MUST follow a golden path. If no path applies, ask before inventing a new pattern.

### 2.1 Golden Paths

- Add a new tool to an existing category
- Add a new tool category (new manager + tool module)
- Add a configuration value
- Modify the permission system
- Add or modify an HTTP transport
- Add shared functionality (new module in a shared package)

### 2.2 Canonical Anchor Index (Single Source of Truth)

If an anchor doesn't fit, ask. Do not invent new patterns.

#### Add a new tool to an existing category

1. Add the manager method in `apps/network/src/unifi_network_mcp/managers/<domain>_manager.py`
   - **Anchor:** `apps/network/src/unifi_network_mcp/managers/client_manager.py` (read-only method pattern)
   - **Anchor:** `apps/network/src/unifi_network_mcp/managers/firewall_manager.py` (mutating method pattern)
2. Add the tool function in `apps/network/src/unifi_network_mcp/tools/<category>.py`
   - **Anchor (read-only tool):** `apps/network/src/unifi_network_mcp/tools/clients.py:lookup_by_ip`
   - **Anchor (permissioned tool):** `apps/network/src/unifi_network_mcp/tools/firewall.py:create_simple_firewall_policy`
3. Add the tool name to `TOOL_MODULE_MAP` in `apps/network/src/unifi_network_mcp/categories.py`
4. Run `make network-manifest` to regenerate `apps/network/src/unifi_network_mcp/tools_manifest.json`
5. Add tests in `apps/network/tests/unit/test_<category>.py`
6. Add MCP `ToolAnnotations` to the `@server.tool()` decorator (readOnlyHint, destructiveHint, etc.)
7. Commit code + manifest + tests together

#### Add a new tool category

1. Create `apps/network/src/unifi_network_mcp/managers/<domain>_manager.py`
   - **Anchor:** `apps/network/src/unifi_network_mcp/managers/routing_manager.py` (small, clean manager)
2. Add manager factory to `apps/network/src/unifi_network_mcp/runtime.py` following the `@lru_cache` factory + alias pattern
3. Create `apps/network/src/unifi_network_mcp/tools/<category>.py` importing from `unifi_network_mcp.runtime`
   - **Anchor:** `apps/network/src/unifi_network_mcp/tools/clients.py` (module structure, imports, decorator usage)
4. Add tool names to `TOOL_MODULE_MAP` in `apps/network/src/unifi_network_mcp/categories.py`
5. Add permission config block to `apps/network/src/unifi_network_mcp/config/config.yaml` under `permissions:`
6. Add category mapping to `NETWORK_CATEGORY_MAP` in `apps/network/src/unifi_network_mcp/categories.py`
7. Run `make network-manifest`
8. Add tests, update `docs/` and README as needed
9. Commit everything together

#### Add a configuration value

1. Add the default to `apps/network/src/unifi_network_mcp/config/config.yaml` with OmegaConf `${oc.env:VAR_NAME,default}` syntax
   - **Anchor:** `apps/network/src/unifi_network_mcp/config/config.yaml` (full file)
2. Add the env var to `env.example` with a comment
3. Document in README.md under the configuration section
4. Access via `config.server.get("key")` or `config.unifi.key` in code

#### Modify the permission system

1. Shared permission logic lives in `packages/unifi-mcp-shared/src/unifi_mcp_shared/permissions.py`
   - **Anchor:** `packages/unifi-mcp-shared/src/unifi_mcp_shared/permissions.py` (PermissionChecker class)
2. Network-specific category mappings live in `NETWORK_CATEGORY_MAP` in `apps/network/src/unifi_network_mcp/categories.py`
3. Enforcement happens in `apps/network/src/unifi_network_mcp/main.py:permissioned_tool` decorator
4. Config defaults live in `apps/network/src/unifi_network_mcp/config/config.yaml` under `permissions:`
5. Tests in `packages/unifi-mcp-shared/tests/` and `apps/network/tests/unit/` cover permission edge cases

#### Add shared functionality

1. Decide which package: `unifi-core` (controller abstractions) or `unifi-mcp-shared` (MCP utilities)
2. Add the module to the appropriate `packages/<pkg>/src/<pkg_name>/` directory
3. Add tests in `packages/<pkg>/tests/`
4. Run `make core-test` or `make shared-test` to verify
5. Import from consuming code: `from unifi_core.<module>` or `from unifi_mcp_shared.<module>`

---

## 3. Architecture Invariants (Hard Rules)

### 3.1 Layering (Do Not Break)

```
MCP Client (Claude Desktop, LM Studio, automation platforms)
    |
    v  MCP Protocol (JSON-RPC over stdio / Streamable HTTP / SSE)
    |
FastMCP Server (apps/network/src/unifi_network_mcp/main.py)
    |
    v  Tool Registration (permissioned_tool decorator)
    |
Tool Functions (apps/network/.../tools/*.py)     <-- thin wrappers, 5-30 lines
    |
    v  Manager method calls
    |
Manager Layer (apps/network/.../managers/*.py)   <-- domain logic, 30-200 lines
    |
    v  aiounifi API calls
    |
Connection Manager (apps/network/.../managers/connection_manager.py)
    |                    uses unifi_core.auth (API key / local credential auth)
    v  aiohttp + auto-detection (UniFi OS vs standalone)
    |
UniFi Network Controller (REST API)
```

**Shared package layers:**
- `unifi_core` -- auth strategies, connection detection, retry policies (no MCP dependency)
- `unifi_mcp_shared` -- permissions, confirmation, meta-tools, lazy loading, config (MCP-aware, server-agnostic)

**Rules:**
- Tool functions MUST NOT contain business logic beyond argument validation and response formatting
- Tool functions MUST delegate to manager methods for all controller interactions
- Manager methods MUST NOT import from `unifi_network_mcp.tools` (no circular dependencies)
- All controller communication MUST flow through `ConnectionManager`
- Tool modules MUST import singletons from `unifi_network_mcp.runtime`, never instantiate directly
- Shared packages MUST NOT import from `unifi_network_mcp` (dependency flows downward only)

### 3.2 Singleton Pattern (Do Not Duplicate)

- All shared objects (server, config, managers) MUST be created via `@lru_cache` factories in `apps/network/src/unifi_network_mcp/runtime.py`
- Module-level aliases (e.g., `config = get_config()`) provide convenient import-time access
- Tests MUST monkey-patch the factory or alias before importing tool modules
- There MUST be exactly one `ConnectionManager` instance per server process

### 3.3 Tool Response Contract

All tools MUST return a `Dict[str, Any]` with this structure:

```python
# Success
{"success": True, "data": <result>}

# Error
{"success": False, "error": "<specific, actionable message>"}

# Mutation preview (confirm=False)
{"success": True, "requires_confirmation": True, "preview": <payload>}
```

- Exceptions MUST NOT escape tool functions. Catch, log with `exc_info=True`, return error dict.
- Error messages MUST be specific and actionable, never raw tracebacks.
- Error messages MUST include the operation that failed (e.g., "Failed to list devices: ..." not just `str(e)`).

### 3.4 Permission Enforcement

- Permissions are checked at **tool registration time** (fail-fast), not at call time
- Priority order: Environment variable > config YAML > default section > hardcoded fallback
- `delete` actions are **denied by default** and require explicit opt-in via `UNIFI_PERMISSIONS_<CATEGORY>_DELETE=true` or config
- `read` actions are **allowed by default** when not explicitly configured
- High-risk categories (networks, devices, clients, WLANs) default to `false` for create/update
- Tools denied by permissions are still registered in the tool index (for discovery) but NOT callable via MCP

### 3.5 Confirmation System for Mutations

All state-changing tools MUST implement the preview-then-confirm pattern:

- Default call (`confirm=False`): validate input, return preview payload
- Explicit call (`confirm=True`): execute the mutation on the controller
- `UNIFI_AUTO_CONFIRM=true` bypasses for automation workflows
- **Anchor:** `packages/unifi-mcp-shared/src/unifi_mcp_shared/confirmation.py`

### 3.6 MCP Tool Annotations

All tools MUST include `annotations=ToolAnnotations(...)` in the `@server.tool()` decorator:

- Read-only tools: `readOnlyHint=True, openWorldHint=False`
- Mutating tools: `readOnlyHint=False, destructiveHint=<bool>, idempotentHint=<bool>, openWorldHint=False`
- `destructiveHint=True` for delete, block, reboot, revoke operations
- `idempotentHint=True` for update/rename (same args = same result)
- All tools use `openWorldHint=False` (closed UniFi controller domain)

### 3.7 Extension Over Patching

- Prefer adding new tool modules and managers over modifying existing ones
- New tool categories get their own manager + tool module (vertical slice)
- Fix root causes, not symptoms. No shortcuts, no monkey-patches in production code.

---

## 4. No-Magic-Literals (Hard Ban)

### 4.1 Configuration Values

All runtime-configurable values MUST live in:
- `apps/network/src/unifi_network_mcp/config/config.yaml` with OmegaConf interpolation for env var support
- Environment variables with `UNIFI_` or `UNIFI_MCP_` prefix

Hardcoding host, port, credentials, or feature flags in Python source is **banned**.

### 4.2 Permission Categories

All permission category strings MUST be defined in:
- `NETWORK_CATEGORY_MAP` in `apps/network/src/unifi_network_mcp/categories.py` (tool shorthand to config key mapping)
- `permissions:` section of `apps/network/src/unifi_network_mcp/config/config.yaml` (defaults)

### 4.3 Tool Registration

All tool-to-module mappings MUST be defined in:
- `TOOL_MODULE_MAP` in `apps/network/src/unifi_network_mcp/categories.py`
- `apps/network/src/unifi_network_mcp/tools_manifest.json` (auto-generated, MUST be committed)

### 4.4 Validation Schemas

Input validation schemas MUST be defined in:
- `apps/network/src/unifi_network_mcp/schemas.py` (JSON Schema definitions)
- `apps/network/src/unifi_network_mcp/validators.py` / `apps/network/src/unifi_network_mcp/validator_registry.py` (validation logic)

Never inline JSON schema dicts inside tool functions.

---

## 5. CLI and Server Behavior

### 5.1 Transport Modes

The server supports three transport modes:

| Transport | Config | Use Case |
|-----------|--------|----------|
| **stdio** | Always active | Claude Desktop, local LLMs, primary transport |
| **Streamable HTTP** | `UNIFI_MCP_HTTP_ENABLED=true`, `UNIFI_MCP_HTTP_TRANSPORT=streamable-http` | Remote clients, automation platforms |
| **HTTP SSE** (legacy) | `UNIFI_MCP_HTTP_ENABLED=true`, `UNIFI_MCP_HTTP_TRANSPORT=sse` | Backwards compatibility only |

- stdio and HTTP MAY run concurrently (`asyncio.gather`)
- HTTP transport SHOULD default to Streamable HTTP (MCP spec 2025-03-26)
- HTTP binding is skipped for non-PID-1 processes unless `UNIFI_MCP_HTTP_FORCE=true`

### 5.2 Tool Registration Modes

| Mode | Tokens | Behavior |
|------|--------|----------|
| **lazy** (default) | ~200 | Meta-tools registered; others loaded on first use |
| **eager** | ~5,000 | All tools registered immediately; supports category/tool filtering |
| **meta_only** | ~200 | Only meta-tools; requires `unifi_execute` for all operations |

- `lazy` is the RECOMMENDED mode for LLM clients
- `eager` is for the dev console, automation scripts, and local testing
- All three modes MUST be tested when adding new tools

### 5.3 Error Handling

- Errors MUST be logged to stderr (never stdout, which is reserved for JSON-RPC in stdio mode)
- Errors MUST include specific, actionable messages with the failed operation name
- Raw tracebacks MUST NOT be exposed to MCP clients (log with `exc_info=True`, return clean message)
- Configuration errors SHOULD fail fast at startup with clear guidance

### 5.4 Logging Conventions

```python
logger = logging.getLogger("unifi-network-mcp")

# Prefix conventions:
logger.info("[permissions] Skipping MCP registration of tool '%s'", name)
logger.info("[diagnostics] Tool '%s' completed in %.2fs", name, duration)
```

- All log output MUST go to stderr
- Use the `"unifi-network-mcp"` logger name (or `__name__` for module-level)
- Use `%s` format strings in logger calls (not f-strings) for lazy evaluation

---

## 6. Upgrade and Migrations

### 6.1 Versioning

- Version is derived from git tags via `hatch-vcs` (e.g., `v0.4.0` -> `0.4.0`)
- MUST NOT manually edit version in `pyproject.toml` (it uses `dynamic = ["version"]`)
- `apps/network/src/unifi_network_mcp/tools_manifest.json` MUST be regenerated and committed before release

### 6.2 Manifest Ownership

- `apps/network/src/unifi_network_mcp/tools_manifest.json` is auto-generated by `apps/network/scripts/generate_tool_manifest.py`
- It MUST be committed to git (allows lazy loading without build tools)
- Run `make network-manifest` after adding, removing, or renaming any tool

### 6.3 Dependency Management

- Dependencies are managed via `uv` (workspace lockfile: `uv.lock`)
- Each package has its own `pyproject.toml` with version ranges; `uv.lock` pins exact versions for all
- Shared packages use path dependencies: `unifi-core = { path = "../../packages/unifi-core", editable = true }`
- Update with `uv lock --upgrade`, verify with `make test`

---

## 7. Quality Gates (Definition of Done)

A change is not done unless ALL of the following pass:

### 7.1 Code Quality

```bash
make format       # Code formatted with ruff (line-length: 120)
make lint         # ruff check passes (E, F, I rules)
make test         # All pytest tests pass (core + shared + network)
```

Or equivalently: `make pre-commit`

### 7.2 Tool Changes Checklist

When adding or modifying tools:

- [ ] Tool function follows the anchor pattern (thin wrapper, delegates to manager)
- [ ] Tool returns standardized `{"success": bool, ...}` response
- [ ] Tool is added to `TOOL_MODULE_MAP` in `apps/network/src/unifi_network_mcp/categories.py`
- [ ] `make network-manifest` has been run and `tools_manifest.json` is committed
- [ ] Mutating tools implement preview-then-confirm pattern
- [ ] Permission category and action are set via decorator kwargs
- [ ] MCP `ToolAnnotations` added (readOnlyHint, destructiveHint, idempotentHint, openWorldHint)
- [ ] Tests cover success path, error path, and permission denial
- [ ] Tool works in all three registration modes (lazy, eager, meta_only)

### 7.3 Configuration Changes Checklist

When adding config values:

- [ ] Default added to `apps/network/src/unifi_network_mcp/config/config.yaml` with `${oc.env:VAR,default}` syntax
- [ ] `env.example` updated
- [ ] README.md configuration table updated

### 7.4 Release Gate

```bash
make pre-commit   # format + lint + test
```

---

## 8. Execution Model

### 8.1 Plan First (Hard Rule)

Before non-trivial changes, produce a short plan covering:
- Approach and impacted files
- Which anchor patterns apply
- New tests needed
- Verification steps

**Trivial exception** (all conditions must be true):
- Single-file edit
- No new behavior or tools
- No config, permission, or schema changes
- No new tests required

### 8.2 Test in All Modes

After any tool change, verify in all three registration modes:

```bash
# From apps/network/ directory:
make run-lazy    # Default mode (lazy loading)
make run-eager   # All tools loaded
make run-meta    # Meta-only mode
```

### 8.3 Conflict Resolution

- When unsure which pattern to follow, consult the anchor index in section 2.2
- If no anchor applies, ask before inventing a new pattern
- If adopting a genuinely new pattern, update this constitution first

---

## Appendix A: Key File Reference

### Network Server (apps/network/)

| File | Purpose |
|------|---------|
| `src/unifi_network_mcp/main.py` | Entry point, tool registration, transport dispatch |
| `src/unifi_network_mcp/bootstrap.py` | Config loading, logging setup, env var processing |
| `src/unifi_network_mcp/runtime.py` | Singleton factories, global objects (single source of truth) |
| `src/unifi_network_mcp/categories.py` | `NETWORK_CATEGORY_MAP`, `TOOL_MODULE_MAP`, lazy loading setup |
| `src/unifi_network_mcp/tool_index.py` | Tool registry and discovery |
| `src/unifi_network_mcp/config/config.yaml` | All configuration defaults (OmegaConf) |
| `src/unifi_network_mcp/tools/*.py` | Tool modules (one per category) |
| `src/unifi_network_mcp/managers/*.py` | Domain logic managers |
| `src/unifi_network_mcp/schemas.py` | JSON Schema definitions |
| `src/unifi_network_mcp/validators.py` | Base validator class |
| `src/unifi_network_mcp/validator_registry.py` | Validation dispatch |
| `src/unifi_network_mcp/tools_manifest.json` | Pre-generated tool metadata (committed) |
| `Makefile` | App-level development commands |

### Shared Packages

| File | Purpose |
|------|---------|
| `packages/unifi-core/src/unifi_core/auth.py` | Auth strategies (local credentials, API key) |
| `packages/unifi-core/src/unifi_core/connection.py` | HTTP session management |
| `packages/unifi-core/src/unifi_core/detection.py` | UniFi OS vs standalone detection |
| `packages/unifi-core/src/unifi_core/retry.py` | Retry policies for transient failures |
| `packages/unifi-core/src/unifi_core/exceptions.py` | Core exception types |
| `packages/unifi-mcp-shared/src/unifi_mcp_shared/permissions.py` | PermissionChecker class |
| `packages/unifi-mcp-shared/src/unifi_mcp_shared/confirmation.py` | Preview-then-confirm helpers |
| `packages/unifi-mcp-shared/src/unifi_mcp_shared/meta_tools.py` | Meta-tools: tool_index, execute, batch |
| `packages/unifi-mcp-shared/src/unifi_mcp_shared/lazy_tools.py` | LazyToolLoader, TOOL_MODULE_MAP builder |
| `packages/unifi-mcp-shared/src/unifi_mcp_shared/tool_loader.py` | Eager tool auto-discovery |
| `packages/unifi-mcp-shared/src/unifi_mcp_shared/config.py` | Shared config helpers |
| `packages/unifi-mcp-shared/src/unifi_mcp_shared/formatting.py` | Response formatting utilities |

### Root

| File | Purpose |
|------|---------|
| `Makefile` | Root targets (delegates to app/package) |
| `pyproject.toml` | Workspace root config |
| `uv.lock` | Single lockfile for all packages |
| `env.example` | Environment variable template |
| `CONTRIBUTING.md` | Contributor workflow |

## Appendix B: Environment Variable Quick Reference

### Server-specific prefix pattern

Each server supports its own prefixed variables that take priority over the shared `UNIFI_*` fallback:

- **Network server:** `UNIFI_NETWORK_*` > `UNIFI_*`
- **Protect server:** `UNIFI_PROTECT_*` > `UNIFI_*`

For single-controller setups, the shared `UNIFI_*` variables are all you need.

### Connection variables

| Shared (fallback) | Network server | Protect server | Default | Purpose |
|--------------------|----------------|----------------|---------|---------|
| `UNIFI_HOST` | `UNIFI_NETWORK_HOST` | `UNIFI_PROTECT_HOST` | (required) | Controller IP/hostname |
| `UNIFI_USERNAME` | `UNIFI_NETWORK_USERNAME` | `UNIFI_PROTECT_USERNAME` | (required*) | Admin username (*required for local auth) |
| `UNIFI_PASSWORD` | `UNIFI_NETWORK_PASSWORD` | `UNIFI_PROTECT_PASSWORD` | (required*) | Admin password (*required for local auth) |
| `UNIFI_API_KEY` | `UNIFI_NETWORK_API_KEY` | `UNIFI_PROTECT_API_KEY` | (optional) | API key for UniFi OS API key auth |
| `UNIFI_PORT` | `UNIFI_NETWORK_PORT` | `UNIFI_PROTECT_PORT` | 443 | Controller HTTPS port |
| `UNIFI_SITE` | `UNIFI_NETWORK_SITE` | — | default | UniFi site name |
| `UNIFI_VERIFY_SSL` | `UNIFI_NETWORK_VERIFY_SSL` | `UNIFI_PROTECT_VERIFY_SSL` | false | SSL certificate verification |

### Server and transport settings (shared)

| Variable | Default | Purpose |
|----------|---------|---------|
| `UNIFI_CONTROLLER_TYPE` | auto | Controller type detection (auto/proxy/direct) |
| `UNIFI_TOOL_REGISTRATION_MODE` | lazy | Tool loading mode (lazy/eager/meta_only) |
| `UNIFI_MCP_HTTP_ENABLED` | false | Enable HTTP transport |
| `UNIFI_MCP_HTTP_TRANSPORT` | streamable-http | HTTP transport type (streamable-http/sse) |
| `UNIFI_MCP_HOST` | 0.0.0.0 | HTTP bind address |
| `UNIFI_MCP_PORT` | 3000 | HTTP bind port |
| `UNIFI_MCP_LOG_LEVEL` | INFO | Logging level |
| `UNIFI_AUTO_CONFIRM` | false | Auto-confirm mutations |
| `UNIFI_MCP_ALLOWED_HOSTS` | localhost,127.0.0.1 | Allowed HTTP hosts |
| `UNIFI_MCP_ENABLE_DNS_REBINDING_PROTECTION` | true | DNS rebinding protection |
| `UNIFI_PERMISSIONS_<CAT>_<ACTION>` | (varies) | Per-category permission override |
