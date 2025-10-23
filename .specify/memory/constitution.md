<!--
Sync Impact Report - Constitution v1.1.0
========================================
Version Change: 1.0.0 → 1.1.0
Modified Principles: N/A
Added Sections:
  - Project Structure (new section)
  - Code Style & Standards (integrated from general-rules.mdc)
  - Documentation Standards (integrated from general-rules.mdc)
  - Resources & References (integrated from general-rules.mdc)

Templates Status:
  ✅ plan-template.md - Validated (no updates needed)
  ✅ spec-template.md - Validated (no updates needed)
  ✅ tasks-template.md - Validated (no updates needed)
  ✅ Command templates - Validated (no updates needed)

Migration Notes:
  - .cursor/rules/general-rules.mdc should now reference this constitution
  - Constitution is now the single source of truth for all development standards

Follow-up TODOs: Update .cursor/rules/general-rules.mdc to reference constitution
-->

# UniFi Network MCP Server Constitution

## Core Principles

### I. MCP-First Architecture

All functionality MUST be exposed via Model Context Protocol (MCP) tools. Every tool MUST be
prefixed with `unifi_` for clear namespace identification. The server operates primarily via
stdio transport (FastMCP) with optional HTTP SSE endpoint that MUST be explicitly enabled.

**Rationale**: MCP provides a standardized interface for AI agents to interact with the UniFi
Network Controller. The `unifi_` prefix prevents naming collisions and provides clear tool
categorization. Stdio-first ensures secure, local-only operation by default.

### II. Security by Default

All tools that modify state or disrupt availability MUST require explicit confirmation to execute
via a `confirm=true` parameter. Mutating operations MUST be disabled by default in configuration
and explicitly enabled per-tool. Sensitive credentials MUST be loaded via environment variables
or `.env` files, never hardcoded.

**Rationale**: Network infrastructure is critical. Accidental modifications can cause outages or
security vulnerabilities. Explicit confirmation provides a safety gate. Disabled-by-default
mutating operations follow the principle of least privilege and require conscious enablement.

### III. Python Idiomatic Code

Use idiomatic Python 3.13+ with type hints. String literals MUST be defined as module-level
constants (CONST naming). Follow established patterns from the aiounifi library for UniFi
Network Controller connectivity and the official MCP Python SDK for tool implementations.

**Rationale**: Consistency improves maintainability and reduces cognitive load. Type hints
enable static analysis and IDE support. Following established library patterns ensures
compatibility and leverages battle-tested code paths.

### IV. Dependency Discipline

Use `uv` for virtual environment and package dependency management. Leverage the aiounifi
library for all UniFi controller operations. Leverage the official MCP SDK for Python and
its established patterns for tool registration and lifecycle management.

**Rationale**: `uv` provides fast, reliable dependency resolution. aiounifi abstracts the
UniFi controller API complexity. The MCP SDK ensures compliance with the protocol
specification and handles transport concerns.

### V. Local-First Operation

The server is designed for local installation and deployment. All operations assume local
network access to the UniFi Network Controller. Remote access MUST be secured via reverse
proxy (Cloudflare Tunnel, Ngrok) with additional authentication layers.

**Rationale**: Local-first minimizes attack surface and network latency. Sensitive network
infrastructure should not be exposed directly to the internet. When remote access is
required, defense-in-depth through multiple security layers is mandatory.

## Project Structure

### Repository Layout

```text
unifi-network-mcp/
├── src/                          # Source code
│   ├── main.py                   # Entry point, FastMCP server setup
│   ├── runtime.py                # Global singletons (server, managers, config)
│   ├── bootstrap.py              # Environment loading, logging, config initialization
│   ├── config/                   # Configuration
│   │   └── config.yaml           # Default configuration with permissions
│   ├── managers/                 # Business logic layer
│   ├── tools/                    # MCP tool adapters
│   ├── utils/                    # Utilities
│   │   ├── diagnostics.py        # Diagnostics and logging wrappers
│   │   ├── permissions.py        # Permission checking
│   │   └── tool_loader.py        # Dynamic tool loading
├── devtools/                     # Development tools
│   └── dev_console.py            # Interactive tool testing console
├── tests/                        # Test suite (when implemented)
│   ├── contract/                 # Contract tests
│   ├── integration/              # Integration tests
│   └── unit/                     # Unit tests
├── .specify/                     # SpecKit framework
│   ├── memory/                   # Project memory
│   │   └── constitution.md       # This file - source of truth
│   └── templates/                # Templates for workflows
├── .cursor/                      # Cursor IDE configuration
│   ├── commands/                 # Slash commands
│   └── rules/                    # IDE rules (references constitution)
├── .env.example                  # Example environment variables
├── pyproject.toml                # Python project configuration
├── docker-compose.yml            # Docker composition for local dev
├── Dockerfile                    # Container image definition
└── README.md                     # User-facing documentation
```

### Architectural Layers

1. **Entry Point** (`main.py`): Server initialization, tool registration with permission checks
2. **Runtime** (`runtime.py`): Global singleton instances shared across the application
3. **Bootstrap** (`bootstrap.py`): Configuration loading with precedence hierarchy
4. **Tools Layer** (`tools/`): Thin MCP adapters that validate inputs and delegate to managers
5. **Managers Layer** (`managers/`): Business logic, UniFi API interactions, error handling
6. **Utilities** (`utils/`): Cross-cutting concerns (diagnostics, permissions, loading)
7. **Configuration** (`config/`): Declarative settings with environment overrides

## Architecture & Design Constraints

### Tool Organization

Tools MUST be organized by functional domain (clients, devices, firewall, network, port
forwards, QoS, statistics, system, traffic routes, VPN). Each domain SHOULD have a
corresponding manager class that encapsulates business logic, with tools acting as thin
MCP adapters that delegate to managers.

### Configuration Management

Configuration MUST support multiple sources with clear precedence:

1. Environment variables (highest precedence)
2. `.env` file
3. Custom YAML file via `CONFIG_PATH` environment variable
4. Relative `config/config.yaml` in current working directory
5. Bundled default `src/config/config.yaml` (lowest precedence)

### Permissions System

A declarative permissions system MUST control which tools are registered. Tools declare
their permission requirements via `permission_category` and `permission_action` decorator
parameters. Tools not granted permission MUST NOT be registered with the MCP server.

### Diagnostics & Observability

Optional diagnostics mode MUST be available for debugging. When enabled, structured logs
MUST capture tool invocations (with redacted sensitive parameters), execution timing, and
controller API requests/responses (with redacted credentials). Diagnostics MUST default
to disabled to avoid log verbosity in production.

## Code Style & Standards

### Python Style

- Use idiomatic Python 3.13+ syntax and features
- Use CONST naming (UPPER_SNAKE_CASE) for module-level string constants
- All functions and classes MUST have type hints
- Follow PEP 8 style guidelines with modern Python conventions
- Prefer dataclasses with slots=True for data containers
- Use f-strings for string formatting
- Use pathlib.Path for file path operations
- Use type annotations from typing and typing_extensions

### Library Patterns

- **aiounifi Library**: Follow established patterns from aiounifi for UniFi controller connectivity
  - Use async/await patterns consistently
  - Leverage aiounifi's connection management
  - Follow aiounifi's error handling conventions

- **MCP SDK**: Follow official MCP Python SDK patterns and best practices
  - Use FastMCP for server implementation
  - Use @server.tool decorator for tool registration
  - Follow MCP protocol specifications for tool schemas
  - Use proper async handlers for tool implementations

### Tool Implementation Standards

- All MCP tools MUST be prefixed with `unifi_`
- Tools MUST be thin adapters that delegate to manager classes
- Tools MUST validate inputs using Pydantic schemas where applicable
- Tools MUST handle errors gracefully and return meaningful error messages
- Mutating tools MUST check for `confirm=true` parameter
- Tools MUST respect permission configuration before registration

### Code Organization

- Separate concerns into layers: tools → managers → API calls
- Keep business logic in manager classes, not in tool functions
- Use dependency injection via global singletons (runtime.py)
- Avoid circular imports by using proper module organization
- Group related functionality into domain modules

## Security & Operations

### Credential Management

UniFi controller credentials (host, username, password, port, site, SSL verification)
MUST be provided via environment variables or `.env` files. Credentials MUST NEVER be
committed to version control. The `.env.example` file SHOULD document required variables
without containing actual secrets.

### Confirmation Requirements

All mutating operations (create, update, delete, reboot, block, adopt, etc.) MUST check
for a `confirm` parameter set to boolean `true`. Operations invoked without confirmation
MUST fail with a clear error message explaining the requirement.

### Permission Model

Permissions MUST be configured in `src/config/config.yaml` under the `permissions` key.
Each tool category (clients, devices, firewall, etc.) MUST have separate read/write
permission toggles. Write permissions MUST default to `false`.

### SSL/TLS Handling

The server MUST support connecting to UniFi controllers with self-signed certificates via
the `verify_ssl` configuration option. This option SHOULD default to `false` for local
network deployments where self-signed certificates are common.

## Documentation Standards

### Code Documentation

- Do NOT add unnecessary comments to code
- Code SHOULD be self-documenting through clear naming and structure
- Use docstrings for public APIs, functions, and classes
- Document complex algorithms or non-obvious logic with brief inline comments
- If extensive comments are needed for reference, maintain a changelog.md file in the
  root of the project and ensure it's added to .gitignore

### README Maintenance

- Keep README.md up to date with all changes
- Document new tools in the Tool Catalog section
- Update configuration examples when new settings are added
- Ensure Quick Start instructions remain accurate
- Document security implications of new features

### API Documentation

- All MCP tools MUST have clear, descriptive names
- Tool descriptions MUST explain what the tool does and when to use it
- Tool parameters MUST be documented with type information and examples
- Return value schemas MUST be clear and consistent

### Change Documentation

- Significant changes MUST be documented in git commit messages
- Breaking changes MUST be clearly identified
- Configuration changes MUST be documented with migration guidance
- Security-relevant changes MUST be highlighted

## Resources & References

### Official Documentation

- **Model Context Protocol (MCP) SDK for Python**
  - Repository: <https://github.com/modelcontextprotocol/python-sdk>
  - Use for: MCP server implementation, tool registration, protocol compliance

- **aiounifi Library for Python**
  - Repository: <https://github.com/Kane610/aiounifi>
  - Use for: UniFi Network Controller API interactions, async patterns

### Development Tools

- **uv**: Fast Python package installer and resolver
  - Use for: Virtual environment management, dependency installation
  - Installation: `curl -fsSL https://astral.sh/uv/install.sh | bash`

### Related Documentation

- UniFi Network Controller API documentation (vendor-specific)
- FastMCP documentation and examples
- Python 3.13+ language reference and PEP standards

## Governance

### Constitution Authority

This constitution supersedes all other development practices and patterns. Any code,
documentation, or tooling that conflicts with these principles MUST be updated to comply
or explicitly justified via amendment to this document.

### Amendment Process

1. Proposed changes MUST be documented with rationale
2. Impact analysis MUST identify affected templates, tools, and workflows
3. Version MUST be incremented following semantic versioning:
   - MAJOR: Backward-incompatible changes to principles or governance
   - MINOR: New principles or materially expanded guidance
   - PATCH: Clarifications, wording fixes, non-semantic refinements
4. Dependent templates (plan, spec, tasks) MUST be updated for consistency
5. Amendment MUST be committed with clear changelog entry

### Compliance Review

All pull requests MUST verify compliance with constitutional principles. Code reviews
SHOULD explicitly reference relevant principles when approving or requesting changes.
Architectural decisions that deviate from principles MUST be justified and documented.

### Source of Truth

This constitution is the single source of truth for all development standards, patterns,
and practices. Other documentation files (including `.cursor/rules/general-rules.mdc`)
SHOULD reference this document rather than duplicate its content. When conflicts arise,
this constitution takes precedence.

**Version**: 1.1.0 | **Ratified**: 2025-10-23 | **Last Amended**: 2025-10-23
