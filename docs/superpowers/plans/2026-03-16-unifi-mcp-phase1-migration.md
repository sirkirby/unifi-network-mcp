# UniFi MCP Ecosystem — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate unifi-network-mcp into a multi-product monorepo (unifi-mcp) with shared packages, dual auth, and improved documentation.

**Architecture:** Monorepo with `apps/network/` (existing server), `packages/unifi-core/` (auth, connection, detection), and `packages/unifi-mcp-shared/` (MCP patterns). Each PR leaves tests green. No release until all 7 PRs land.

**Tech Stack:** Python 3.13+, FastMCP, aiounifi, aiohttp, OmegaConf, uv workspaces, hatch-vcs, ruff, pytest

**Spec:** `docs/superpowers/specs/2026-03-16-unifi-mcp-ecosystem-phase1-design.md`

---

## Pre-requisite: GitHub Repo Rename

Before starting PR 1, rename the repo on GitHub: `sirkirby/unifi-network-mcp` → `sirkirby/unifi-mcp` via Settings. This is a manual GitHub operation. GitHub automatically creates a 301 redirect from the old URL.

---

## Chunk 1: PR 1 — Monorepo Scaffold

### Task 1: Create monorepo directory structure

**Files:**
- Create: `apps/` (directory)
- Create: `packages/unifi-core/pyproject.toml`
- Create: `packages/unifi-core/src/unifi_core/__init__.py`
- Create: `packages/unifi-mcp-shared/pyproject.toml`
- Create: `packages/unifi-mcp-shared/src/unifi_mcp_shared/__init__.py`
- Create: `docker/` (directory)

- [ ] **Step 1: Create the directory scaffold**

```bash
mkdir -p apps
mkdir -p packages/unifi-core/src/unifi_core
mkdir -p packages/unifi-mcp-shared/src/unifi_mcp_shared
mkdir -p docker
```

- [ ] **Step 2: Create `packages/unifi-core/pyproject.toml`**

```toml
[project]
name = "unifi-core"
version = "0.1.0"
description = "UniFi controller connectivity: auth, detection, retry, exceptions"
requires-python = ">=3.13"
dependencies = [
    "aiohttp>=3.8.5",
    "pyyaml>=6.0",
]

[dependency-groups]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "aioresponses>=0.7.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/unifi_core"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3: Create `packages/unifi-core/src/unifi_core/__init__.py`**

```python
"""UniFi controller connectivity: auth, detection, retry, exceptions."""
```

- [ ] **Step 4: Create `packages/unifi-mcp-shared/pyproject.toml`**

```toml
[project]
name = "unifi-mcp-shared"
version = "0.1.0"
description = "Shared MCP server patterns: permissions, confirmation, lazy loading, config"
requires-python = ">=3.13"
dependencies = [
    "mcp[cli]>=1.26.0,<2",
    "omegaconf>=2.3.0",
    "pyyaml>=6.0",
]

[dependency-groups]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/unifi_mcp_shared"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 5: Create `packages/unifi-mcp-shared/src/unifi_mcp_shared/__init__.py`**

```python
"""Shared MCP server patterns: permissions, confirmation, lazy loading, config."""
```

- [ ] **Step 6: Commit scaffold**

```bash
git add apps/ packages/ docker/
git commit -m "chore: create monorepo directory scaffold

Placeholder directories for apps/, packages/unifi-core/,
packages/unifi-mcp-shared/, and docker/. No code changes."
```

### Task 2: Create root workspace `pyproject.toml`

**Files:**
- Create: `pyproject.toml` (root workspace — rename existing to `apps/network/pyproject.toml` in PR 2)

**Important:** The existing `pyproject.toml` at the root is the network server's package config. We do NOT overwrite it yet — that happens in PR 2. For now, create a separate `pyproject.workspace.toml` that we'll swap in during PR 2.

- [ ] **Step 1: Create `pyproject.workspace.toml` (staging file)**

This file will become the root `pyproject.toml` in PR 2 when the existing one moves to `apps/network/`.

```toml
[project]
name = "unifi-mcp"
version = "0.0.0"
description = "UniFi MCP ecosystem workspace"
requires-python = ">=3.13"

[tool.uv.workspace]
members = [
    "apps/*",
    "packages/*",
]

[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I"]
```

- [ ] **Step 2: Commit workspace config**

```bash
git add pyproject.workspace.toml
git commit -m "chore: add uv workspace config (staged for PR 2 swap)"
```

### Task 3: Move `docker-compose.yml` to `docker/`

**Files:**
- Move: `docker-compose.yml` → `docker/docker-compose.yml`

- [ ] **Step 1: Move the file**

```bash
git mv docker-compose.yml docker/docker-compose.yml
```

- [ ] **Step 2: Update any references in `Makefile`**

Read the Makefile for `docker-compose` references and update paths. Currently at line ~155:

```makefile
# Before
docker compose up -d
# After
docker compose -f docker/docker-compose.yml up -d
```

- [ ] **Step 3: Verify docker compose still works**

```bash
docker compose -f docker/docker-compose.yml config
```

- [ ] **Step 4: Commit**

```bash
git add docker/ Makefile
git commit -m "chore: move docker-compose.yml to docker/ directory"
```

### Task 4: Verify everything still works

- [ ] **Step 1: Run existing tests**

```bash
make test
```
Expected: All tests pass — no code was changed.

- [ ] **Step 2: Run lint**

```bash
make lint
```
Expected: Clean.

- [ ] **Step 3: Commit PR 1 complete message (tag for squash)**

Create the PR. All changes are additive — new directories, placeholder packages, staged workspace config. Existing code untouched.

---

## Chunk 2: PR 2 — Move Network Code into `apps/network/`

This is the highest-risk PR. Every source file moves and every import changes. The strategy: move files first, then fix imports, then fix build config, then fix tests, then fix CI.

### Task 5: Move source code to `apps/network/`

**Files:**
- Move: `src/` → `apps/network/src/unifi_network_mcp/`
- Move: `tests/` → `apps/network/tests/`
- Move: `devtools/` → `apps/network/devtools/`
- Move: `scripts/` → `apps/network/scripts/`
- Move: `Dockerfile` → `apps/network/Dockerfile`
- Move: `.env.example` → `apps/network/.env.example`

- [ ] **Step 1: Create the network app directory**

```bash
mkdir -p apps/network/src
```

- [ ] **Step 2: Move source code with git mv**

```bash
git mv src apps/network/src/unifi_network_mcp
```

This renames the flat `src/` to a proper Python package namespace.

- [ ] **Step 3: Create `__init__.py` for the package**

```python
# apps/network/src/unifi_network_mcp/__init__.py
"""UniFi Network MCP Server."""
```

Note: If `src/__init__.py` already exists, it was moved. Update its content.

- [ ] **Step 4: Move supporting directories**

```bash
git mv tests apps/network/tests
git mv devtools apps/network/devtools
git mv scripts apps/network/scripts
git mv Dockerfile apps/network/Dockerfile
git mv .env.example apps/network/.env.example
```

- [ ] **Step 5: Commit the raw move (before fixing imports)**

```bash
git add -A
git commit -m "refactor: move network code into apps/network/ (imports broken)

Raw file move — imports will be fixed in the next commit.
This preserves git history for the moved files."
```

### Task 6: Rewrite all imports

**Files:**
- Modify: Every `.py` file under `apps/network/src/unifi_network_mcp/`
- Modify: Every `.py` file under `apps/network/tests/`

The import prefix changes from `src.` to `unifi_network_mcp.`. This is a mechanical find-and-replace but must be done carefully.

- [ ] **Step 1: Rewrite imports in all source files**

Use a targeted search-and-replace. The patterns to replace:

| Pattern | Replacement |
|---------|-------------|
| `from src.` | `from unifi_network_mcp.` |
| `import src.` | `import unifi_network_mcp.` |
| `"src.tools."` | `"unifi_network_mcp.tools."` |
| `"src.tools"` | `"unifi_network_mcp.tools"` |
| `"src.utils` | `"unifi_network_mcp.utils` |

Run these replacements across all `.py` files in `apps/network/src/` and `apps/network/tests/`.

**Critical files to verify manually after bulk replace:**

1. `apps/network/src/unifi_network_mcp/utils/lazy_tool_loader.py` line 77: module prefix in f-string `f"src.tools.{...}"` → `f"unifi_network_mcp.tools.{...}"` (f-string won't be caught by naive find-replace)
2. `apps/network/src/unifi_network_mcp/utils/meta_tools.py` line 277: `from src.utils.lazy_tool_loader` → `from unifi_network_mcp.utils.lazy_tool_loader`
3. `apps/network/src/unifi_network_mcp/utils/tool_loader.py` line 11: default `"src.tools"` → `"unifi_network_mcp.tools"`
4. `apps/network/src/unifi_network_mcp/runtime.py`: all manager imports
5. `apps/network/src/unifi_network_mcp/main.py`: all imports at top
6. `apps/network/scripts/generate_tool_manifest.py`: f-string references to `"src.tools."` (same f-string pattern as lazy_tool_loader.py — requires manual editing)

- [ ] **Step 2: Update `hatch-vcs` version file path**

The current `pyproject.toml` generates `src/_version.py`. After the move, it should generate `apps/network/src/unifi_network_mcp/_version.py`. This is handled in Task 7 (pyproject.toml update).

- [ ] **Step 3: Update ruff `known-first-party` config**

In the network app's pyproject.toml (created in Task 7):

```toml
[tool.ruff.lint.isort]
known-first-party = ["unifi_network_mcp"]
```

- [ ] **Step 4: Commit import rewrites**

```bash
git add -A
git commit -m "refactor: rewrite all imports from src.* to unifi_network_mcp.*"
```

### Task 7: Create network app `pyproject.toml` and swap workspace root

**Files:**
- Create: `apps/network/pyproject.toml` (from existing root `pyproject.toml`, adapted)
- Modify: Root `pyproject.toml` (swap in workspace config from `pyproject.workspace.toml`)

- [ ] **Step 1: Create `apps/network/pyproject.toml`**

Adapt the existing root `pyproject.toml` for the network app:

```toml
[project]
name = "unifi-network-mcp"
dynamic = ["version"]
description = "UniFi Network MCP Server — 90+ tools for LLMs and agents"
requires-python = ">=3.13"
license = "MIT"
dependencies = [
    "mcp[cli]>=1.26.0,<2",
    "aiohttp>=3.8.5",
    "aiounifi>=88",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "omegaconf>=2.3.0",
    "jsonschema>=4.17.0",
    "typing-extensions>=4.4.0",
]

[project.scripts]
unifi-network-mcp = "unifi_network_mcp.main:main"

[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"
raw-options.root = "../.."
tag-pattern = "network/v*"

[tool.hatch.build.hooks.vcs]
version-file = "src/unifi_network_mcp/_version.py"

[tool.hatch.build.targets.wheel]
packages = ["src/unifi_network_mcp"]

[tool.hatch.build.targets.wheel.force-include]
"src/unifi_network_mcp/config/config.yaml" = "unifi_network_mcp/config/config.yaml"
"src/unifi_network_mcp/tools_manifest.json" = "unifi_network_mcp/tools_manifest.json"

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.ruff.lint.isort]
known-first-party = ["unifi_network_mcp"]
```

Key changes from original:
- Entry point: `"unifi_network_mcp.main:main"` (was `"src.main:main"`)
- `hatch.version.raw-options.root = "../.."` (git root is two levels up)
- `tag-pattern = "network/v*"` (prefixed tags)
- Version file: `src/unifi_network_mcp/_version.py`
- Packages: `["src/unifi_network_mcp"]`
- Force-include paths updated
- `known-first-party = ["unifi_network_mcp"]`

**Important:** This template is a starting point. The implementer MUST derive the full `apps/network/pyproject.toml` from the actual existing root file, preserving ALL sections including: `[dependency-groups] dev` (pytest, ruff, aioresponses, etc.), `[tool.hatch.build.targets.sdist]`, `[tool.hatch.build.targets.wheel.shared-data]` for `.well-known` (path becomes `../../.well-known`), and `[tool.ruff] exclude`. Without the dev dependencies, tests won't run.

- [ ] **Step 2: Replace root `pyproject.toml` with workspace config**

```bash
mv pyproject.workspace.toml pyproject.toml
```

The root `pyproject.toml` is now the uv workspace definition.

- [ ] **Step 3: Commit**

```bash
git add apps/network/pyproject.toml pyproject.toml
git rm pyproject.workspace.toml 2>/dev/null || true
git commit -m "refactor: create network app pyproject.toml, set up uv workspace root"
```

### Task 8: Create network app Makefile

**Files:**
- Create: `apps/network/Makefile`
- Modify: Root `Makefile` (add delegation targets)

- [ ] **Step 1: Create `apps/network/Makefile`**

Adapt the existing root Makefile for the network app. Key differences: paths are relative to `apps/network/`, `uv run` commands reference the app's pyproject.toml.

```makefile
.PHONY: help test lint format manifest run run-lazy run-eager run-meta clean

help:
	@echo "UniFi Network MCP — Development Commands"
	@echo ""
	@echo "  make test       Run tests"
	@echo "  make lint       Lint with ruff"
	@echo "  make format     Format with ruff"
	@echo "  make manifest   Regenerate tools_manifest.json"
	@echo "  make run        Run server (default: lazy mode)"
	@echo "  make clean      Remove build artifacts"

test:
	cd ../.. && uv run --package unifi-network-mcp pytest apps/network/tests -v

test-cov:
	cd ../.. && uv run --package unifi-network-mcp pytest apps/network/tests -v --cov=unifi_network_mcp --cov-report=term-missing

lint:
	cd ../.. && uv run ruff check apps/network/src apps/network/tests

format:
	cd ../.. && uv run ruff format apps/network/src apps/network/tests

format-check:
	cd ../.. && uv run ruff format --check apps/network/src apps/network/tests

manifest:
	cd ../.. && uv run --package unifi-network-mcp python apps/network/scripts/generate_tool_manifest.py

run:
	cd ../.. && UNIFI_TOOL_REGISTRATION_MODE=lazy uv run --package unifi-network-mcp unifi-network-mcp

run-lazy:
	cd ../.. && UNIFI_TOOL_REGISTRATION_MODE=lazy uv run --package unifi-network-mcp unifi-network-mcp

run-eager:
	cd ../.. && UNIFI_TOOL_REGISTRATION_MODE=eager uv run --package unifi-network-mcp unifi-network-mcp

run-meta:
	cd ../.. && UNIFI_TOOL_REGISTRATION_MODE=meta_only uv run --package unifi-network-mcp unifi-network-mcp

pre-commit: format lint test

clean:
	rm -rf build/ dist/ *.egg-info src/unifi_network_mcp/_version.py
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

- [ ] **Step 2: Update root Makefile with delegation targets**

Replace the existing root Makefile with a delegating version:

```makefile
.PHONY: help network-test network-lint network-format network-manifest test lint format

help:
	@echo "UniFi MCP Ecosystem — Top-Level Commands"
	@echo ""
	@echo "  make test              Run all tests"
	@echo "  make lint              Lint all packages"
	@echo "  make format            Format all packages"
	@echo "  make network-test      Run network server tests"
	@echo "  make network-lint      Lint network server"
	@echo "  make network-manifest  Regenerate network tools manifest"

# Delegating targets
network-test:
	$(MAKE) -C apps/network test

network-lint:
	$(MAKE) -C apps/network lint

network-format:
	$(MAKE) -C apps/network format

network-manifest:
	$(MAKE) -C apps/network manifest

# Aggregate targets
test: network-test

lint: network-lint

format: network-format

pre-commit: format lint test
```

- [ ] **Step 3: Commit**

```bash
git add apps/network/Makefile Makefile
git commit -m "refactor: create network app Makefile, update root to delegate"
```

### Task 9: Update `tests/conftest.py` and test imports

**Files:**
- Modify: `apps/network/tests/conftest.py`
- Modify: All test files in `apps/network/tests/`

- [ ] **Step 1: Update `conftest.py` sys.path**

The current `conftest.py` adds the project root to `sys.path`. After the move, it needs to add the workspace root so that `unifi_network_mcp` is importable.

```python
# apps/network/tests/conftest.py
import sys
from pathlib import Path

# Add workspace root to path so unifi_network_mcp is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

- [ ] **Step 2: Update test imports**

Replace `from src.` with `from unifi_network_mcp.` in all test files. This should have been covered in Task 6, but verify no test files were missed.

```bash
grep -r "from src\." apps/network/tests/ || echo "All clean"
grep -r "import src\." apps/network/tests/ || echo "All clean"
```

- [ ] **Step 3: Commit**

```bash
git add apps/network/tests/
git commit -m "refactor: update test imports and conftest for new package paths"
```

### Task 10: Update `scripts/generate_tool_manifest.py`

**Files:**
- Modify: `apps/network/scripts/generate_tool_manifest.py`

- [ ] **Step 1: Update manifest generation script**

Read the current script and update:
- Tool discovery path: `src/tools/` → `apps/network/src/unifi_network_mcp/tools/`
- Module prefix in manifest: `src.tools.` → `unifi_network_mcp.tools.`
- Output path: `src/tools_manifest.json` → `apps/network/src/unifi_network_mcp/tools_manifest.json`

- [ ] **Step 2: Regenerate manifest**

```bash
make network-manifest
```

- [ ] **Step 3: Verify manifest content**

Check that the generated manifest uses `unifi_network_mcp.tools.*` module paths.

- [ ] **Step 4: Commit**

```bash
git add apps/network/scripts/ apps/network/src/unifi_network_mcp/tools_manifest.json
git commit -m "refactor: update manifest generation for new package paths"
```

### Task 11: Update Dockerfile

**Files:**
- Modify: `apps/network/Dockerfile`

- [ ] **Step 1: Update Dockerfile build context and paths**

The Dockerfile needs to:
- Set build context to workspace root (for `uv` workspace resolution)
- Install the network app specifically
- Update entry point to `unifi-network-mcp` (console script should still work)

Read the current Dockerfile and adapt. Key changes:
- `COPY` paths now reference `apps/network/` and `packages/`
- `pip install .` → `pip install ./apps/network`
- Or better: use `uv` for installation

- [ ] **Step 2: Test Docker build**

```bash
docker build -f apps/network/Dockerfile -t unifi-network-mcp:test .
```

- [ ] **Step 3: Commit**

```bash
git add apps/network/Dockerfile
git commit -m "refactor: update Dockerfile for monorepo layout"
```

### Task 12: Update GitHub Actions workflows

**Files:**
- Modify: `.github/workflows/test.yml`
- Modify: `.github/workflows/docker-publish.yml`
- Modify: `.github/workflows/publish-to-pypi.yml`

- [ ] **Step 1: Update `test.yml`**

- Change working directory to workspace root
- Update pytest path: `pytest apps/network/tests -v`
- Update uv install to use workspace: `uv sync --package unifi-network-mcp`

- [ ] **Step 2: Update `docker-publish.yml`**

- Update Dockerfile path: `apps/network/Dockerfile`
- Build context remains workspace root

- [ ] **Step 3: Update `publish-to-pypi.yml`**

- Build from `apps/network/`: `cd apps/network && python -m build`
- Or use `uv build --package unifi-network-mcp`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/
git commit -m "ci: update workflows for monorepo directory layout"
```

### Task 13: Verify PR 2 — full test suite

- [ ] **Step 1: Install workspace dependencies**

```bash
uv sync
```

- [ ] **Step 2: Run all tests**

```bash
make test
```
Expected: All tests pass at new paths.

- [ ] **Step 3: Run lint**

```bash
make lint
```
Expected: Clean (no import order issues with new first-party config).

- [ ] **Step 4: Run format check**

```bash
make format
```

- [ ] **Step 5: Verify manifest**

```bash
make network-manifest
git diff  # Should show no changes if manifest is up to date
```

- [ ] **Step 6: Verify all three registration modes**

```bash
make -C apps/network run-lazy   # Ctrl-C after startup
make -C apps/network run-eager  # Ctrl-C after startup
make -C apps/network run-meta   # Ctrl-C after startup
```

Each should start without import errors.

---

## Chunk 3: PR 3 — Extract `unifi-mcp-shared`

Extract generic MCP patterns from the network app into the shared package. The network app then imports from `unifi_mcp_shared` instead of its own utils.

### Task 14: Extract `permissions.py` to shared package

**Files:**
- Create: `packages/unifi-mcp-shared/src/unifi_mcp_shared/permissions.py`
- Modify: `apps/network/src/unifi_network_mcp/utils/permissions.py` (becomes thin re-export or deleted)
- Modify: `apps/network/src/unifi_network_mcp/main.py` (update import)

- [ ] **Step 1: Write the failing test for parameterized PermissionChecker**

```python
# packages/unifi-mcp-shared/tests/test_permissions.py
import pytest
from unifi_mcp_shared.permissions import PermissionChecker


def test_permission_checker_with_custom_category_map():
    """Category map is injected, not hardcoded."""
    category_map = {"my_category": "my_config_key"}
    permissions_config = {"my_config_key": {"read": True, "create": False}}
    checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
    assert checker.check("my_category", "read") is True
    assert checker.check("my_category", "create") is False


def test_permission_checker_env_var_override(monkeypatch):
    """Env vars take priority over config."""
    category_map = {"firewall": "firewall_policies"}
    permissions_config = {"firewall_policies": {"create": False}}
    checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
    monkeypatch.setenv("UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE", "true")
    assert checker.check("firewall", "create") is True


def test_permission_checker_default_fallback():
    """Falls back to default section when category not configured."""
    category_map = {"unknown": "unknown_category"}
    permissions_config = {"default": {"read": True, "create": False}}
    checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
    assert checker.check("unknown", "read") is True
    assert checker.check("unknown", "create") is False


def test_permission_checker_read_default_true():
    """Read is allowed by default when nothing is configured."""
    checker = PermissionChecker(category_map={}, permissions={})
    assert checker.check("anything", "read") is True


def test_permission_checker_delete_default_false():
    """Delete is denied by default."""
    checker = PermissionChecker(category_map={}, permissions={})
    assert checker.check("anything", "delete") is False
```

- [ ] **Step 2: Create shared tests directory and run test to verify it fails**

```bash
mkdir -p packages/unifi-mcp-shared/tests
```

```bash
uv run pytest packages/unifi-mcp-shared/tests/test_permissions.py -v
```
Expected: FAIL — `unifi_mcp_shared.permissions` has no `PermissionChecker`.

- [ ] **Step 3: Implement `PermissionChecker` in shared package**

Create `packages/unifi-mcp-shared/src/unifi_mcp_shared/permissions.py`:

Adapt from `apps/network/src/unifi_network_mcp/utils/permissions.py` (113 lines). Key changes:
- Replace module-level `CATEGORY_MAP` dict with constructor parameter
- Replace `parse_permission(permissions, category, action)` function with `PermissionChecker.check(category, action)` method
- Keep the same priority logic: env var > config category > config default > hardcoded fallback
- Keep the env var format: `UNIFI_PERMISSIONS_{CATEGORY}_{ACTION}`

```python
"""Permission checking with configurable category mappings."""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PERMISSIONS_KEY = "default"


class PermissionChecker:
    """Check tool permissions against config and env vars.

    Priority order:
    1. Environment variable UNIFI_PERMISSIONS_<CATEGORY>_<ACTION>
    2. Config permissions.<category>.<action>
    3. Config permissions.default.<action>
    4. Hardcoded: read=True, everything else=False
    """

    def __init__(self, category_map: dict[str, str], permissions: dict[str, Any] | None = None):
        self.category_map = category_map
        self.permissions = permissions or {}

    def check(self, category: str, action: str) -> bool:
        config_key = self.category_map.get(category, category)

        # 1. Environment variable override
        env_key = f"UNIFI_PERMISSIONS_{config_key.upper()}_{action.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            result = env_val.lower() in ("true", "1", "yes", "on")
            logger.info("[permissions] Env override %s=%s → %s", env_key, env_val, result)
            return result

        # 2. Category-specific config
        cat_perms = self.permissions.get(config_key, {})
        if isinstance(cat_perms, dict) and action in cat_perms:
            result = bool(cat_perms[action])
            logger.debug("[permissions] Config %s.%s=%s", config_key, action, result)
            return result

        # 3. Default section
        defaults = self.permissions.get(DEFAULT_PERMISSIONS_KEY, {})
        if isinstance(defaults, dict) and action in defaults:
            result = bool(defaults[action])
            logger.debug("[permissions] Default %s=%s", action, result)
            return result

        # 4. Hardcoded fallback
        if action == "read":
            return True
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest packages/unifi-mcp-shared/tests/test_permissions.py -v
```
Expected: All 5 tests PASS.

- [ ] **Step 5: Update network app to import from shared package**

In `apps/network/src/unifi_network_mcp/main.py`, replace the permission import and update usage. The `parse_permission()` call sites need to use the new `PermissionChecker` instance.

Read `main.py` lines 43-169 (the `permissioned_tool` decorator) to find where `parse_permission` is called. Update to use `PermissionChecker.check()`.

Create a network-specific categories module:

```python
# apps/network/src/unifi_network_mcp/categories.py
"""Network server permission category mappings."""

NETWORK_CATEGORY_MAP = {
    "firewall": "firewall_policies",
    "firewall_policy": "firewall_policies",
    "qos": "qos_rules",
    "traffic_route": "traffic_routes",
    "port_forward": "port_forwards",
    "vpn_client": "vpn_clients",
    "vpn_server": "vpn_servers",
    "vpn": "vpn",
    "network": "networks",
    "wlan": "wlans",
    "device": "devices",
    "client": "clients",
    "guest": "guests",
    "event": "events",
    "hotspot": "vouchers",
    "voucher": "vouchers",
    "usergroup": "usergroups",
    "route": "routes",
    "acl": "acl_rules",
    "system": "snmp",
    "snmp": "snmp",
}
```

- [ ] **Step 6: Run network tests to verify nothing broke**

```bash
make test
```
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add packages/unifi-mcp-shared/src/unifi_mcp_shared/permissions.py \
       packages/unifi-mcp-shared/tests/test_permissions.py \
       apps/network/src/unifi_network_mcp/categories.py \
       apps/network/src/unifi_network_mcp/main.py
git commit -m "refactor: extract permissions.py to unifi-mcp-shared

PermissionChecker class accepts configurable category_map instead
of hardcoded CATEGORY_MAP. Network app provides NETWORK_CATEGORY_MAP.
Same priority logic: env var > config > default > hardcoded fallback."
```

### Task 15: Extract `confirmation.py` to shared package

**Files:**
- Create: `packages/unifi-mcp-shared/src/unifi_mcp_shared/confirmation.py`
- Modify: Network app imports

- [ ] **Step 1: Write failing test**

```python
# packages/unifi-mcp-shared/tests/test_confirmation.py
import pytest
from unifi_mcp_shared.confirmation import preview_response, should_auto_confirm


def test_preview_response_returns_success_true():
    """Preview is a successful operation awaiting confirmation."""
    result = preview_response(
        action="create",
        resource_type="firewall_policy",
        resource_id="new",
        current_state={},
        proposed_changes={"name": "test"},
    )
    assert result["success"] is True
    assert result["requires_confirmation"] is True
    assert result["action"] == "create"


def test_should_auto_confirm_default_false():
    assert should_auto_confirm() is False


def test_should_auto_confirm_env_true(monkeypatch):
    monkeypatch.setenv("UNIFI_AUTO_CONFIRM", "true")
    assert should_auto_confirm() is True
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest packages/unifi-mcp-shared/tests/test_confirmation.py -v
```

- [ ] **Step 3: Copy and adapt `confirmation.py`**

Copy from `apps/network/src/unifi_network_mcp/utils/confirmation.py`. Key change: fix the preview response contract — `preview_response()` should return `"success": True` (not `False`) per spec reconciliation. This is the canonical behavior going forward.

- [ ] **Step 4: Run tests**

```bash
uv run pytest packages/unifi-mcp-shared/tests/test_confirmation.py -v
```

- [ ] **Step 5: Update network app imports**

Replace `from unifi_network_mcp.utils.confirmation import ...` with `from unifi_mcp_shared.confirmation import ...` across all tool modules.

- [ ] **Step 6: Run full test suite**

```bash
make test
```

Fix any tests that assert `success: False` for previews — they now expect `success: True`.

- [ ] **Step 7: Commit**

```bash
git add packages/unifi-mcp-shared/src/unifi_mcp_shared/confirmation.py \
       packages/unifi-mcp-shared/tests/test_confirmation.py \
       apps/network/
git commit -m "refactor: extract confirmation.py to unifi-mcp-shared

Fixes preview response contract: previews now return success=True
with requires_confirmation=True (previews are successful operations)."
```

### Task 16: Extract `lazy_tools.py` to shared package

**Files:**
- Create: `packages/unifi-mcp-shared/src/unifi_mcp_shared/lazy_tools.py`
- Modify: Network app `utils/lazy_tool_loader.py` (becomes thin wrapper or deleted)

- [ ] **Step 1: Write failing test**

```python
# packages/unifi-mcp-shared/tests/test_lazy_tools.py
from unifi_mcp_shared.lazy_tools import build_tool_module_map


def test_build_tool_module_map_from_manifest(tmp_path):
    """Builds map from manifest file when tools directory doesn't exist."""
    import json

    manifest = {
        "tools": {
            "my_tool": {"module": "my_package.tools.category", "name": "my_tool"},
        }
    }
    manifest_path = tmp_path / "tools_manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    result = build_tool_module_map(
        tools_package="nonexistent.tools",
        manifest_path=str(manifest_path),
    )
    assert result == {"my_tool": "my_package.tools.category"}
```

- [ ] **Step 2: Run test to verify failure, implement, verify pass**

Extract the map-building logic from `lazy_tool_loader.py`. The shared version accepts `tools_package` and `manifest_path` parameters instead of hardcoding `"src.tools."` and the manifest location.

- [ ] **Step 3: Extract `LazyToolLoader` class**

The class itself is generic — it takes `server` and `tool_decorator`. Move it to the shared package. The network app's `setup_lazy_loading` function now imports from `unifi_mcp_shared.lazy_tools`.

- [ ] **Step 4: Update network app imports and run tests**

```bash
make test
```

- [ ] **Step 5: Commit**

```bash
git commit -m "refactor: extract lazy_tools.py to unifi-mcp-shared

LazyToolLoader and build_tool_module_map accept tools_package and
manifest_path parameters instead of hardcoded src.tools paths."
```

### Task 17: Extract `meta_tools.py` to shared package

**Files:**
- Create: `packages/unifi-mcp-shared/src/unifi_mcp_shared/meta_tools.py`
- Modify: Network app `main.py`

- [ ] **Step 1: Extract with dependency injection**

The key change: `register_load_tools()` at line 277 has `from src.utils.lazy_tool_loader import TOOL_MODULE_MAP`. This becomes an injected parameter:

```python
def register_load_tools(server, tool_decorator, lazy_loader, register_tool, tool_module_map: dict):
    # tool_module_map passed in, not imported
```

- [ ] **Step 2: Update network app `main.py` to pass `tool_module_map`**

```python
from unifi_mcp_shared.meta_tools import register_meta_tools, register_load_tools
from unifi_network_mcp.utils.lazy_tool_loader import TOOL_MODULE_MAP

register_load_tools(server, tool_decorator, lazy_loader, register_tool, TOOL_MODULE_MAP)
```

Wait — after Task 16, `TOOL_MODULE_MAP` is built via the shared package. So the network app builds its map and passes it to `register_load_tools`.

- [ ] **Step 3: Run tests**

```bash
make test
```

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor: extract meta_tools.py to unifi-mcp-shared

register_load_tools accepts tool_module_map as parameter via
dependency injection instead of importing from a hardcoded path."
```

### Task 18: Extract `tool_loader.py` to shared package

**Files:**
- Create: `packages/unifi-mcp-shared/src/unifi_mcp_shared/tool_loader.py`

- [ ] **Step 1: Extract with `tools_package` parameter**

The `auto_load_tools()` function's `base_package` parameter (currently defaulting to `"src.tools"`) becomes required — no default.

```python
def auto_load_tools(base_package: str, enabled_categories=None, enabled_tools=None, server=None):
```

- [ ] **Step 2: Update network app to pass package name**

```python
auto_load_tools("unifi_network_mcp.tools", ...)
```

- [ ] **Step 3: Run tests, commit**

```bash
make test
git commit -m "refactor: extract tool_loader.py to unifi-mcp-shared

auto_load_tools requires base_package parameter (no default)."
```

### Task 19: Extract config loading to shared package

**Files:**
- Create: `packages/unifi-mcp-shared/src/unifi_mcp_shared/config.py`
- Modify: `apps/network/src/unifi_network_mcp/bootstrap.py`

- [ ] **Step 1: Extract the OmegaConf loading machinery**

From `bootstrap.py`, extract the generic parts:
- `load_yaml_config(path)` — loads YAML via OmegaConf
- `setup_logging(logger_name, level)` — creates handler, returns logger
- Config path resolution logic (env var → relative → bundled)

Keep in the network app:
- `UniFiSettings` dataclass (network-specific)
- `load_dotenv()` call (app-specific `.env` location)
- UniFi-specific env var merging (UNIFI_HOST, etc.)

- [ ] **Step 2: Run tests, commit**

```bash
make test
git commit -m "refactor: extract config loading to unifi-mcp-shared

Generic OmegaConf loading and logging setup. Network app keeps
UniFiSettings, dotenv, and UniFi-specific env var handling."
```

### Task 20: Create `formatting.py` response helpers

**Files:**
- Create: `packages/unifi-mcp-shared/src/unifi_mcp_shared/formatting.py`

- [ ] **Step 1: Write failing test**

```python
# packages/unifi-mcp-shared/tests/test_formatting.py
from unifi_mcp_shared.formatting import success_response, error_response


def test_success_response():
    result = success_response(data={"clients": 42})
    assert result == {"success": True, "data": {"clients": 42}}


def test_error_response():
    result = error_response("Something went wrong")
    assert result == {"success": False, "error": "Something went wrong"}
```

- [ ] **Step 2: Implement minimal helpers**

```python
"""Standardized tool response formatting."""

from typing import Any


def success_response(data: Any = None, **kwargs) -> dict[str, Any]:
    result = {"success": True}
    if data is not None:
        result["data"] = data
    result.update(kwargs)
    return result


def error_response(error: str, **kwargs) -> dict[str, Any]:
    result = {"success": False, "error": error}
    result.update(kwargs)
    return result
```

- [ ] **Step 3: Run tests, commit**

```bash
uv run pytest packages/unifi-mcp-shared/tests/test_formatting.py -v
git commit -m "feat: add formatting.py response helpers to unifi-mcp-shared"
```

### Task 21: Clean up network app utils

**Files:**
- Modify/delete: `apps/network/src/unifi_network_mcp/utils/permissions.py`
- Modify/delete: `apps/network/src/unifi_network_mcp/utils/confirmation.py`
- Modify/delete: `apps/network/src/unifi_network_mcp/utils/lazy_tool_loader.py`
- Modify/delete: `apps/network/src/unifi_network_mcp/utils/meta_tools.py`
- Modify/delete: `apps/network/src/unifi_network_mcp/utils/tool_loader.py`

- [ ] **Step 1: Remove extracted files from network utils**

If any network-specific code still depends on the old imports (e.g., test files), update those imports to use `unifi_mcp_shared.*` first.

Only `diagnostics.py` and `config_helpers.py` should remain in `apps/network/src/unifi_network_mcp/utils/`.

- [ ] **Step 2: Run full test suite**

```bash
make test
```

- [ ] **Step 3: Commit**

```bash
git commit -m "refactor: remove extracted utils from network app

Only network-specific utils remain: diagnostics.py, config_helpers.py.
All generic MCP patterns now imported from unifi_mcp_shared."
```

### Task 22: Verify PR 3

- [ ] **Step 1: Full test suite**

```bash
make test
```

- [ ] **Step 2: Lint and format**

```bash
make lint && make format
```

- [ ] **Step 3: Verify all registration modes**

```bash
make -C apps/network run-lazy
make -C apps/network run-eager
make -C apps/network run-meta
```

---

## Chunk 4: PR 4 — Extract `unifi-core` + PR 5 — Dual Auth

### Task 23: Create `exceptions.py` in `unifi-core`

**Files:**
- Create: `packages/unifi-core/src/unifi_core/exceptions.py`

- [ ] **Step 1: Write test**

```python
# packages/unifi-core/tests/test_exceptions.py
from unifi_core.exceptions import UniFiError, UniFiAuthError, UniFiConnectionError


def test_exception_hierarchy():
    assert issubclass(UniFiAuthError, UniFiError)
    assert issubclass(UniFiConnectionError, UniFiError)


def test_exception_message():
    err = UniFiAuthError("Invalid credentials")
    assert str(err) == "Invalid credentials"
```

- [ ] **Step 2: Implement**

```python
"""Shared exception hierarchy for UniFi MCP servers."""


class UniFiError(Exception):
    """Base exception for all UniFi errors."""


class UniFiAuthError(UniFiError):
    """Authentication failed."""


class UniFiConnectionError(UniFiError):
    """Connection to controller failed."""


class UniFiRateLimitError(UniFiError):
    """Rate limit exceeded."""


class UniFiPermissionError(UniFiError):
    """Insufficient permissions for operation."""
```

- [ ] **Step 3: Run tests, commit**

```bash
mkdir -p packages/unifi-core/tests
uv run pytest packages/unifi-core/tests/test_exceptions.py -v
git commit -m "feat: add unifi-core exceptions module"
```

### Task 24: Create `retry.py` in `unifi-core`

**Files:**
- Create: `packages/unifi-core/src/unifi_core/retry.py`

- [ ] **Step 1: Write test**

```python
# packages/unifi-core/tests/test_retry.py
import pytest
from unifi_core.retry import RetryPolicy, retry_with_backoff
from unifi_core.exceptions import UniFiConnectionError


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    call_count = 0

    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise UniFiConnectionError("Connection failed")
        return "success"

    policy = RetryPolicy(max_retries=3, base_delay=0.01)
    result = await retry_with_backoff(flaky_operation, policy)
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted_raises():
    async def always_fails():
        raise UniFiConnectionError("Connection failed")

    policy = RetryPolicy(max_retries=2, base_delay=0.01)
    with pytest.raises(UniFiConnectionError):
        await retry_with_backoff(always_fails, policy)
```

- [ ] **Step 2: Implement**

```python
"""Retry logic with exponential backoff."""

import asyncio
import logging
from dataclasses import dataclass

from unifi_core.exceptions import UniFiError

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    retryable_exceptions: tuple = (UniFiError,)


async def retry_with_backoff(operation, policy: RetryPolicy | None = None):
    """Execute operation with exponential backoff retry."""
    if policy is None:
        policy = RetryPolicy()

    last_error = None
    for attempt in range(policy.max_retries + 1):
        try:
            return await operation()
        except policy.retryable_exceptions as e:
            last_error = e
            if attempt < policy.max_retries:
                delay = min(policy.base_delay * (policy.backoff_factor ** attempt), policy.max_delay)
                logger.warning("[retry] Attempt %d/%d failed: %s. Retrying in %.1fs", attempt + 1, policy.max_retries, e, delay)
                await asyncio.sleep(delay)

    raise last_error
```

- [ ] **Step 3: Run tests, commit**

```bash
uv run pytest packages/unifi-core/tests/test_retry.py -v
git commit -m "feat: add unifi-core retry module with exponential backoff"
```

### Task 25: Create `detection.py` in `unifi-core`

**Files:**
- Create: `packages/unifi-core/src/unifi_core/detection.py`

This is new code informed by existing logic in `connection_manager.py` (lines 16-207) and `bootstrap.py` (lines 173-185). Not a pure extraction.

- [ ] **Step 1: Write test**

```python
# packages/unifi-core/tests/test_detection.py
import pytest
from unittest.mock import AsyncMock, patch
from unifi_core.detection import ControllerType, detect_controller_type


def test_controller_type_enum():
    assert ControllerType.UNIFI_OS.value == "proxy"
    assert ControllerType.STANDALONE.value == "direct"
    assert ControllerType.AUTO.value == "auto"


def test_controller_type_from_config_proxy():
    result = ControllerType.from_config("proxy")
    assert result == ControllerType.UNIFI_OS


def test_controller_type_from_config_direct():
    result = ControllerType.from_config("direct")
    assert result == ControllerType.STANDALONE


def test_controller_type_from_config_auto():
    result = ControllerType.from_config("auto")
    assert result == ControllerType.AUTO


def test_controller_type_from_config_invalid_falls_back():
    result = ControllerType.from_config("invalid")
    assert result == ControllerType.AUTO
```

- [ ] **Step 2: Implement**

```python
"""UniFi controller type detection.

Determines whether the controller is a UniFi OS appliance (UDM, UDR, etc.)
or a standalone/self-hosted Network Application. This affects API path
routing: UniFi OS uses /proxy/network/... while standalone uses /api/...
"""

import enum
import logging

import aiohttp

logger = logging.getLogger(__name__)


class ControllerType(enum.Enum):
    UNIFI_OS = "proxy"
    STANDALONE = "direct"
    AUTO = "auto"

    @classmethod
    def from_config(cls, value: str) -> "ControllerType":
        mapping = {"proxy": cls.UNIFI_OS, "direct": cls.STANDALONE, "auto": cls.AUTO}
        result = mapping.get(value.lower(), cls.AUTO)
        if value.lower() not in mapping:
            logger.warning("[detection] Unknown controller type '%s', falling back to auto", value)
        return result


async def detect_controller_type_pre_login(
    host: str, port: int, verify_ssl: bool = False, timeout: float = 10.0
) -> ControllerType | None:
    """Probe the controller before login to detect type.

    Returns ControllerType or None if detection is inconclusive.
    """
    url = f"https://{host}:{port}"
    ssl_context = None if verify_ssl else False
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    try:
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            async with session.get(url, ssl=ssl_context, allow_redirects=False) as resp:
                headers = resp.headers
                if "x-csrf-token" in headers or resp.status == 200:
                    return ControllerType.UNIFI_OS
                if resp.status in (302, 301):
                    return ControllerType.STANDALONE
    except Exception as e:
        logger.debug("[detection] Pre-login probe failed: %s", e)

    return None


async def detect_controller_type_by_api_probe(
    session: aiohttp.ClientSession, host: str, port: int, verify_ssl: bool = False
) -> ControllerType | None:
    """Probe API endpoints to detect controller type (requires authenticated session)."""
    url_base = f"https://{host}:{port}"
    ssl_context = None if verify_ssl else False

    for path, expected_type in [
        ("/proxy/network/api/self/sites", ControllerType.UNIFI_OS),
        ("/api/self/sites", ControllerType.STANDALONE),
    ]:
        try:
            async with session.get(f"{url_base}{path}", ssl=ssl_context) as resp:
                if resp.status == 200:
                    logger.info("[detection] Detected %s via %s", expected_type.name, path)
                    return expected_type
        except Exception:
            continue

    return None
```

- [ ] **Step 3: Run tests, commit**

```bash
uv run pytest packages/unifi-core/tests/test_detection.py -v
git commit -m "feat: add unifi-core detection module for controller type"
```

### Task 26: Create `connection.py` base in `unifi-core`

**Files:**
- Create: `packages/unifi-core/src/unifi_core/connection.py`

- [ ] **Step 1: Write test for base connection config**

```python
# packages/unifi-core/tests/test_connection.py
import pytest
from unifi_core.connection import ConnectionConfig


def test_connection_config_defaults():
    config = ConnectionConfig(host="192.168.1.1")
    assert config.port == 443
    assert config.verify_ssl is False
    assert config.url_base == "https://192.168.1.1:443"


def test_connection_config_custom_port():
    config = ConnectionConfig(host="10.0.0.1", port=8443)
    assert config.url_base == "https://10.0.0.1:8443"
```

- [ ] **Step 2: Implement base connection primitives**

```python
"""Base async connection primitives for UniFi controllers."""

import ssl
from dataclasses import dataclass, field

import aiohttp


@dataclass
class ConnectionConfig:
    host: str
    port: int = 443
    verify_ssl: bool = False
    timeout: float = 30.0

    @property
    def url_base(self) -> str:
        return f"https://{self.host}:{self.port}"

    @property
    def ssl_context(self):
        if self.verify_ssl:
            return None  # Use default SSL verification
        return False  # Disable SSL verification
```

This is deliberately minimal. The network app's `ConnectionManager` extends this with aiounifi-specific session management, caching, and request routing. Protect and Access will similarly extend it.

- [ ] **Step 3: Run tests, commit**

```bash
uv run pytest packages/unifi-core/tests/test_connection.py -v
git commit -m "feat: add unifi-core connection base primitives"
```

### Task 27: Create `auth.py` in `unifi-core`

**Files:**
- Create: `packages/unifi-core/src/unifi_core/auth.py`

- [ ] **Step 1: Write test**

```python
# packages/unifi-core/tests/test_auth.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from unifi_core.auth import UniFiAuth, AuthMethod
from unifi_core.exceptions import UniFiAuthError


def test_auth_method_enum():
    assert AuthMethod.LOCAL_ONLY.value == "local_only"
    assert AuthMethod.API_KEY_ONLY.value == "api_key_only"
    assert AuthMethod.EITHER.value == "either"


def test_auth_method_from_string():
    assert AuthMethod.from_string("local_only") == AuthMethod.LOCAL_ONLY
    assert AuthMethod.from_string(None) == AuthMethod.LOCAL_ONLY  # default


def test_unifi_auth_has_api_key():
    auth = UniFiAuth(api_key="test-key")
    assert auth.has_api_key is True


def test_unifi_auth_no_api_key():
    auth = UniFiAuth()
    assert auth.has_api_key is False


@pytest.mark.asyncio
async def test_unifi_auth_api_key_session():
    auth = UniFiAuth(api_key="test-key-123")
    session = await auth.get_api_key_session()
    assert session._default_headers.get("X-API-Key") == "test-key-123"
    await session.close()


@pytest.mark.asyncio
async def test_unifi_auth_local_not_configured_raises():
    auth = UniFiAuth(api_key="key")
    with pytest.raises(UniFiAuthError, match="local authentication"):
        await auth.get_local_session()


@pytest.mark.asyncio
async def test_unifi_auth_api_key_not_configured_raises():
    auth = UniFiAuth()
    with pytest.raises(UniFiAuthError, match="API key"):
        await auth.get_api_key_session()
```

- [ ] **Step 2: Implement**

```python
"""Dual authentication strategy for UniFi controllers.

Supports API key auth (X-API-Key header) and local auth (username/password
via app-specific library). Each tool declares which auth method it requires.
"""

import enum
import logging
from typing import Protocol

import aiohttp

from unifi_core.exceptions import UniFiAuthError

logger = logging.getLogger(__name__)


class AuthMethod(enum.Enum):
    LOCAL_ONLY = "local_only"
    API_KEY_ONLY = "api_key_only"
    EITHER = "either"

    @classmethod
    def from_string(cls, value: str | None) -> "AuthMethod":
        if value is None:
            return cls.LOCAL_ONLY
        try:
            return cls(value)
        except ValueError:
            logger.warning("[auth] Unknown auth method '%s', defaulting to local_only", value)
            return cls.LOCAL_ONLY


class LocalAuthProvider(Protocol):
    """Contract that each app fulfills for local auth."""

    async def get_session(self) -> aiohttp.ClientSession: ...


class UniFiAuth:
    """Dual auth: API key and/or local auth provider."""

    def __init__(self, api_key: str | None = None, local_provider: LocalAuthProvider | None = None):
        self._api_key = api_key
        self._local_provider = local_provider

    @property
    def has_api_key(self) -> bool:
        return self._api_key is not None and self._api_key != ""

    @property
    def has_local(self) -> bool:
        return self._local_provider is not None

    def set_local_provider(self, provider: LocalAuthProvider) -> None:
        self._local_provider = provider

    async def get_api_key_session(self) -> aiohttp.ClientSession:
        if not self.has_api_key:
            raise UniFiAuthError(
                "API key authentication not configured. Set UNIFI_API_KEY environment variable."
            )
        return aiohttp.ClientSession(headers={"X-API-Key": self._api_key})

    async def get_local_session(self) -> aiohttp.ClientSession:
        if not self.has_local:
            raise UniFiAuthError(
                "Local authentication not configured. Set UNIFI_USERNAME and UNIFI_PASSWORD."
            )
        return await self._local_provider.get_session()

    async def get_session(self, method: AuthMethod) -> aiohttp.ClientSession:
        if method == AuthMethod.API_KEY_ONLY:
            return await self.get_api_key_session()
        elif method == AuthMethod.LOCAL_ONLY:
            return await self.get_local_session()
        elif method == AuthMethod.EITHER:
            if self.has_api_key:
                return await self.get_api_key_session()
            return await self.get_local_session()
        raise UniFiAuthError(f"Unknown auth method: {method}")
```

- [ ] **Step 3: Run tests, commit**

```bash
uv run pytest packages/unifi-core/tests/test_auth.py -v
git commit -m "feat: add unifi-core auth module with dual auth strategy

AuthMethod enum (local_only, api_key_only, either) for per-tool
annotation. LocalAuthProvider protocol for app-specific auth."
```

### Task 28: Update `unifi-core/__init__.py` exports and verify PR 4

- [ ] **Step 1: Update package exports**

```python
# packages/unifi-core/src/unifi_core/__init__.py
"""UniFi controller connectivity: auth, detection, retry, exceptions."""

from unifi_core.auth import AuthMethod, LocalAuthProvider, UniFiAuth
from unifi_core.connection import ConnectionConfig
from unifi_core.detection import ControllerType
from unifi_core.exceptions import (
    UniFiAuthError,
    UniFiConnectionError,
    UniFiError,
    UniFiPermissionError,
    UniFiRateLimitError,
)
from unifi_core.retry import RetryPolicy, retry_with_backoff

__all__ = [
    "AuthMethod",
    "ConnectionConfig",
    "ControllerType",
    "LocalAuthProvider",
    "RetryPolicy",
    "UniFiAuth",
    "UniFiAuthError",
    "UniFiConnectionError",
    "UniFiError",
    "UniFiPermissionError",
    "UniFiRateLimitError",
    "retry_with_backoff",
]
```

- [ ] **Step 2: Run all tests across all packages**

```bash
uv run pytest packages/unifi-core/tests -v
uv run pytest packages/unifi-mcp-shared/tests -v
make test  # network app tests
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: finalize unifi-core package exports"
```

### Task 29: Integrate dual auth into network server (PR 5)

**Files:**
- Modify: `apps/network/src/unifi_network_mcp/bootstrap.py` (add `api_key` to UniFiSettings)
- Modify: `apps/network/src/unifi_network_mcp/config/config.yaml` (add `api_key` config)
- Modify: `apps/network/src/unifi_network_mcp/runtime.py` (create UniFiAuth instance)
- Modify: `apps/network/src/unifi_network_mcp/main.py` (add `auth` kwarg to `permissioned_tool`)

- [ ] **Step 1: Add `api_key` to `UniFiSettings`**

In `bootstrap.py`, add to the dataclass:

```python
@dataclass(slots=True)
class UniFiSettings:
    host: str
    username: str
    password: str
    port: int = 443
    site: str = "default"
    verify_ssl: bool = False
    controller_type: str = "auto"
    api_key: str = ""  # New: optional API key
```

Update `from_omegaconf()` to read `api_key`.

- [ ] **Step 2: Add config**

In `config.yaml`, add under `unifi:`:

```yaml
api_key: ${oc.env:UNIFI_API_KEY,}
```

In `.env.example`:

```
# UNIFI_API_KEY=          # Optional: API key for official API access
```

- [ ] **Step 3: Create `UniFiAuth` instance in `runtime.py`**

```python
from unifi_core.auth import UniFiAuth

@lru_cache
def get_auth() -> UniFiAuth:
    settings = get_config().unifi
    return UniFiAuth(api_key=getattr(settings, "api_key", None) or os.environ.get("UNIFI_API_KEY"))
```

- [ ] **Step 4: Add `auth` kwarg to `permissioned_tool` decorator**

In `main.py`'s `permissioned_tool`, extract the `auth` kwarg alongside `permission_category` and `permission_action`:

```python
auth_method = d_kwargs.pop("auth", None)  # "local_only", "api_key_only", "either"
```

Default is `None` which maps to `local_only` (backward compatible). Store as metadata on the tool for future use by the auth routing layer.

For Phase 1, this is metadata-only — the actual auth routing per tool call comes when we integrate the API key request flow. The decorator stores the annotation, the network app's request layer can check it later.

- [ ] **Step 5: Write tests**

```python
# apps/network/tests/unit/test_auth_integration.py
import pytest
from unifi_core.auth import UniFiAuth, AuthMethod


def test_api_key_from_config(monkeypatch):
    monkeypatch.setenv("UNIFI_API_KEY", "test-key-123")
    auth = UniFiAuth(api_key="test-key-123")
    assert auth.has_api_key is True


def test_no_api_key_configured():
    auth = UniFiAuth()
    assert auth.has_api_key is False


def test_auth_method_default_is_local_only():
    method = AuthMethod.from_string(None)
    assert method == AuthMethod.LOCAL_ONLY
```

- [ ] **Step 6: Run full test suite**

```bash
make test
```

- [ ] **Step 7: Commit**

```bash
git commit -m "feat: integrate dual auth support into network server

API key configurable via UNIFI_API_KEY env var. Per-tool auth
annotation via auth= kwarg on permissioned_tool decorator.
Default is local_only for backward compatibility."
```

---

## Chunk 5: PR 6 — Documentation + PR 7 — Light-Touch Improvements

### Task 30: Write root README (PR 6)

**Files:**
- Rewrite: `README.md` (root — ecosystem landing page)

- [ ] **Step 1: Write the ecosystem landing page**

~100-150 lines. Structure:
1. Hero: "UniFi MCP — Model Context Protocol servers for the UniFi ecosystem"
2. Badges: PyPI version, license, Python version, tests status
3. Status table:

```markdown
| Server | Status | Tools | Package |
|--------|--------|-------|---------|
| **Network** | Stable | 91 | `unifi-network-mcp` |
| **Protect** | Coming Soon | — | — |
| **Access** | Planned | — | — |
```

4. What is this: 2-3 sentences
5. Quick start: `uvx unifi-network-mcp` or Docker
6. Configuration: common env vars, link to server docs
7. Roadmap: link to ecosystem plan
8. Contributing: link to CONTRIBUTING.md
9. License: MIT

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite root README as ecosystem landing page"
```

### Task 31: Write network app README

**Files:**
- Create: `apps/network/README.md`

- [ ] **Step 1: Write clean quick-start README**

Focus: what it is, how to install, how to run, links to docs/ for everything else. No wall of text.

- [ ] **Step 2: Commit**

```bash
git add apps/network/README.md
git commit -m "docs: add network server README with quick-start focus"
```

### Task 32: Create network app docs

**Files:**
- Create: `apps/network/docs/configuration.md`
- Create: `apps/network/docs/permissions.md`
- Create: `apps/network/docs/tools.md`
- Create: `apps/network/docs/transports.md`
- Create: `apps/network/docs/troubleshooting.md`

- [ ] **Step 1: Extract content from old README into individual docs**

Read the current README (which was the old root README, now likely at `apps/network/` or still at root). Move relevant sections into dedicated docs:

- **configuration.md**: Full config tables, env vars, YAML config, all `UNIFI_*` variables
- **permissions.md**: Permission system deep dive, category mappings, env var overrides
- **tools.md**: Tool catalog (can be auto-generated from manifest)
- **transports.md**: stdio, Streamable HTTP, SSE setup
- **troubleshooting.md**: Common issues, connection problems, permission errors

- [ ] **Step 2: Commit**

```bash
git add apps/network/docs/
git commit -m "docs: create detailed network server documentation

Extracted from monolithic README into focused docs:
configuration, permissions, tools, transports, troubleshooting."
```

### Task 33: Update root docs

**Files:**
- Create: `docs/ARCHITECTURE.md`
- Update: `docs/CONTRIBUTING.md` (or create if not exists at root)

- [ ] **Step 1: Write ARCHITECTURE.md**

Describe the monorepo structure, shared packages, how to add a new server. Keep it concise — a developer guide, not an essay.

- [ ] **Step 2: Update CONTRIBUTING.md for monorepo workflow**

Which Makefile to use, how to test across packages, PR conventions.

- [ ] **Step 3: Commit**

```bash
git add docs/
git commit -m "docs: add monorepo architecture and contributing guides"
```

### Task 34: Add MCP tool annotations (PR 7)

**Files:**
- Modify: All 16 tool modules in `apps/network/src/unifi_network_mcp/tools/`

- [ ] **Step 1: Audit each tool module and add annotations**

For each tool, add the appropriate MCP annotations to the `@permissioned_tool` decorator. This is a mechanical pass:

- Read-only tools: `read_only=True` (maps to `readOnlyHint=True`)
- Destructive tools (delete operations): `destructive=True`
- Idempotent tools (safe to retry): `idempotent=True`

Example:
```python
@permissioned_tool(
    name="unifi_list_clients",
    description="List all connected clients",
    permission_category="client",
    permission_action="read",
    read_only=True,       # New annotation
    idempotent=True,      # New annotation
)
```

Work through each module:
- `clients.py` (11 tools): list/lookup → read_only+idempotent, block/rename → not read_only
- `devices.py` (9 tools): list/details → read_only, reboot → destructive
- `firewall.py` (9 tools): list → read_only, create/update → not, delete → destructive
- Continue for all 16 modules...

- [ ] **Step 2: Run tests to verify no behavioral change**

```bash
make test
```

Annotations are metadata only — they should not change test outcomes.

- [ ] **Step 3: Commit**

```bash
git add apps/network/src/unifi_network_mcp/tools/
git commit -m "feat: add MCP tool annotations (readOnly, destructive, idempotent)

Metadata annotations on all 91 tools for improved MCP client
decision-making. No behavioral change."
```

### Task 35: Error message audit

**Files:**
- Modify: Selected tool modules (worst offenders only)

- [ ] **Step 1: Search for vague error messages**

```bash
grep -r "An error occurred" apps/network/src/
grep -r "Something went wrong" apps/network/src/
grep -r "except Exception as e:" apps/network/src/unifi_network_mcp/tools/
```

- [ ] **Step 2: Fix worst offenders**

Replace vague messages with specific, actionable ones. Example:

```python
# Before
except Exception as e:
    return {"success": False, "error": str(e)}

# After
except Exception as e:
    logger.error("[clients] Failed to list clients: %s", e, exc_info=True)
    return {"success": False, "error": f"Failed to list clients: {e}"}
```

Only fix the clearly bad ones. Don't rewrite working error handling.

- [ ] **Step 3: Run tests, commit**

```bash
make test
git commit -m "fix: improve vague error messages in tool modules"
```

### Task 36: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update for monorepo structure**

Key changes:
- File references: `src/main.py` → `apps/network/src/unifi_network_mcp/main.py`
- Import patterns: `from src.` → `from unifi_network_mcp.`
- Shared package imports: `from unifi_mcp_shared.` and `from unifi_core.`
- Makefile targets: root delegates to app-level
- New anchor patterns for shared packages
- Updated key file reference table
- Add shared package development workflow

- [ ] **Step 2: Run lint to verify no issues**

```bash
make lint
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for monorepo structure and shared packages"
```

### Task 37: Final verification

- [ ] **Step 1: Full test suite across all packages**

```bash
uv run pytest packages/unifi-core/tests -v
uv run pytest packages/unifi-mcp-shared/tests -v
make test
```

- [ ] **Step 2: Lint and format everything**

```bash
make lint && make format
```

- [ ] **Step 3: Regenerate manifest**

```bash
make network-manifest
```

- [ ] **Step 4: Verify all three registration modes**

```bash
make -C apps/network run-lazy
make -C apps/network run-eager
make -C apps/network run-meta
```

- [ ] **Step 5: Verify Docker build**

```bash
docker build -f apps/network/Dockerfile -t unifi-network-mcp:test .
```

After all verifications pass: tag `network/v0.5.0`, publish, announce.
