# unifi-network-mcp Development Guidelines

**Constitution:** `oak/constitution.md` is the single source of truth for all project rules, architecture invariants, and golden paths. Consult it before making non-trivial changes.

## Quick Reference

- **Tech Stack:** Python 3.13+, FastMCP, aiounifi, aiohttp, OmegaConf, jsonschema
- **Linter/Formatter:** ruff (line-length: 120, rules: E, F, I)
- **Tests:** pytest + pytest-asyncio
- **Package Manager:** uv

## Architecture (Hard Rules)

- **Layering:** Tool functions (thin wrappers) -> Manager methods (domain logic) -> ConnectionManager -> UniFi API
- **Singletons:** All shared objects created via `@lru_cache` factories in `src/runtime.py`
- **Async:** All I/O operations MUST be async. No blocking calls in tools or managers.
- **Responses:** All tools return `{"success": bool, ...}` dicts. Exceptions MUST NOT escape.
- **Permissions:** Checked at registration time. Delete always denied. Read allowed by default. See `src/utils/permissions.py`.
- **Mutations:** MUST use preview-then-confirm pattern (`confirm=False` for preview, `confirm=True` to execute).

## Golden Path: Adding a Tool

1. Add manager method in `src/managers/<domain>_manager.py`
2. Add tool function in `src/tools/<category>.py` (copy pattern from `src/tools/clients.py`)
3. Add to `TOOL_MODULE_MAP` in `src/utils/lazy_tool_loader.py`
4. Run `make manifest` (commit the regenerated `src/tools_manifest.json`)
5. Add tests, verify in all three modes: `make run-lazy`, `make run-eager`, `make run-meta`

## Commands

```bash
make pre-commit    # format + lint + test (run before committing)
make manifest      # regenerate tools_manifest.json (after tool changes)
make console       # interactive dev console (eager mode)
make pre-release   # full release validation
```

## Key Files

| File | Purpose |
|------|---------|
| `src/runtime.py` | Singleton factories (server, config, managers) |
| `src/main.py` | Entry point, permissioned_tool decorator, transport dispatch |
| `src/config/config.yaml` | All configuration defaults (OmegaConf) |
| `src/utils/permissions.py` | Permission checking logic |
| `src/utils/lazy_tool_loader.py` | TOOL_MODULE_MAP, lazy loading |
| `src/tools_manifest.json` | Pre-generated tool metadata (MUST be committed) |

## Full Details

See `oak/constitution.md` for:
- Complete anchor index with line references
- Architecture invariants and layering rules
- No-magic-literals policy
- Quality gates and checklists
- Environment variable reference
