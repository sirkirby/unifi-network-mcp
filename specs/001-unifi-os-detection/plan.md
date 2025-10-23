# Implementation Plan: UniFi API Path Detection and Adaptation

**Branch**: `001-unifi-os-detection` | **Date**: 2025-10-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-unifi-os-detection/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement automatic detection of required API path structure (proxy vs direct) and URI adjustment for `/proxy/network/api` path compatibility across UniFi controller variations. The system will use empirical probe-based detection to test both direct `/api` and `/proxy/network/api` paths during initial connection, cache the successful result, and apply a request path interceptor to modify ApiRequest objects before they're sent to the controller. This eliminates 404 errors on newer UniFi OS controllers (Cloud Gateway, self-hosted UniFi OS 4.x+) without requiring manual configuration.

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**:
- aiounifi >= 83.0.0 (UniFi controller API client)
- MCP SDK (mcp[cli] == 1.13.1)
- aiohttp >= 3.8.5 (async HTTP client)
- pyyaml >= 6.0 (config management)
- python-dotenv >= 1.0.0 (environment variables)

**Storage**: In-memory caching (detection results stored in connection manager state, no persistence required)
**Testing**: pytest with pytest-asyncio for async test support
**Target Platform**: Local server deployment (Linux/macOS/Windows with Python 3.13+)
**Project Type**: Single project (MCP server with FastMCP)
**Performance Goals**:
- Detection completes within 5 seconds during initial connection
- Detection adds no more than 2 seconds to connection time vs current implementation
- Zero overhead on subsequent API requests after detection (cached result)

**Constraints**:
- Must work with unpredictable controller variations (cannot rely on device type/version detection)
- Must integrate with aiounifi library without modifying library code (request interceptor pattern)
- Must maintain backward compatibility when aiounifi adds native path detection support
- Must operate within existing MCP server architecture (managers layer for logic, tools layer for MCP adapters)
- Detection must use a known endpoint that responds consistently across controller types

**Scale/Scope**:
- Single feature implementation affecting connection initialization
- Request path interceptor applies to all ~50+ existing MCP tools
- Supports diverse controller fleet (standalone, Cloud Gateway, self-hosted UniFi OS)
- Primary codebase modification in managers/connection_manager.py and bootstrap flow

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### MCP-First Architecture
✅ **PASS**: Feature integrates with existing MCP tools via connection manager modification. No new MCP tools required (path interception is transparent to tools). All existing `unifi_` prefixed tools will benefit from automatic path detection.

### Security by Default
✅ **PASS**: Feature is read-only infrastructure change. No mutating operations introduced. Detection probes use existing authentication credentials. Manual override via `UNIFI_CONTROLLER_TYPE` environment variable follows existing configuration precedence. No new confirmation requirements needed.

### Python Idiomatic Code
✅ **PASS**: Implementation will use Python 3.13+ with type hints. String constants will be module-level CONST naming. Will follow aiounifi async patterns for detection probes. No violations of idiomatic Python expected.

### Dependency Discipline
✅ **PASS**: Uses existing aiounifi library (already at >= 83.0.0). No new external dependencies required. Leverages existing MCP SDK patterns. Uses `uv` for development (already established). Request interceptor pattern integrates with aiounifi's ApiRequest objects without modification.

### Local-First Operation
✅ **PASS**: Feature operates within existing local-first deployment model. Detection probes use local network connectivity to UniFi controller. No changes to remote access patterns. No new network exposure.

### Tool Organization
✅ **PASS**: Implementation follows established architecture. Business logic in managers/connection_manager.py (existing file). No new tools required. Existing tools benefit transparently. Detection logic encapsulated in connection manager, not scattered across tool implementations.

### Configuration Management
✅ **PASS**: Manual override follows existing configuration precedence: environment variables > `.env` > config.yaml. New `UNIFI_CONTROLLER_TYPE` setting integrates with existing config system. No changes to precedence hierarchy.

### Permissions System
✅ **PASS**: No new permissions required. Detection is infrastructure-level operation during connection initialization. Does not expose new MCP tools that require permission gating. Existing permission model unchanged.

### Diagnostics & Observability
✅ **PASS**: Detection results will be logged via existing diagnostics system. Will capture probe attempts, responses, and final path requirement decision. Integrates with existing structured logging in connection manager. Detection outcome visible in dev_console.py output.

### Overall Assessment
**Status**: ✅ ALL GATES PASSED

No constitutional violations identified. Feature aligns with all core principles and architectural constraints. No complexity exceptions required.

## Project Structure

### Documentation (this feature)

```text
specs/001-unifi-os-detection/
├── spec.md              # Feature specification (input)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (technology research)
├── data-model.md        # Phase 1 output (detection state model)
├── quickstart.md        # Phase 1 output (developer guide)
├── contracts/           # Phase 1 output (detection API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── main.py                      # Entry point (unchanged)
├── runtime.py                   # Global singletons (unchanged)
├── bootstrap.py                 # Environment loading (may add UNIFI_CONTROLLER_TYPE config)
├── config/
│   └── config.yaml              # Configuration (may add controller_type setting)
├── managers/
│   ├── connection_manager.py    # PRIMARY MODIFICATION: add detection logic and path interceptor
│   └── [other managers...]      # Unchanged
├── tools/                       # Unchanged (transparent to tools)
├── utils/
│   ├── diagnostics.py           # May add detection event logging
│   └── [other utils...]
└── schemas.py                   # May add detection result schema

devtools/
└── dev_console.py               # May add detection result display in connection output

tests/                           # New tests for this feature
├── unit/
│   └── test_path_detection.py  # Unit tests for detection logic
└── integration/
    └── test_path_interceptor.py # Integration tests with mock controllers
```

**Structure Decision**: Single project structure (Option 1). This is an infrastructure enhancement to the existing MCP server, not a new application. Primary modification occurs in `src/managers/connection_manager.py` with supporting changes to configuration loading and diagnostics. The request path interceptor pattern allows transparent integration without modifying existing tool implementations.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A - No constitutional violations. All gates passed.
