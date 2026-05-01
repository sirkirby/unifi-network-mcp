---
name: myco:monorepo-release-pipeline
description: |
  Covers the full release pipeline for the unifi-mcp Python monorepo: scoping
  hatch-vcs version tag globs per package to prevent sibling-tag contamination,
  pushing tags in strict dependency order (unifi-core → unifi-mcp-shared → app
  servers → relay), configuring scripts/generate_release_notes.py path scoping
  per package, wiring per-package publish workflows for OIDC trusted publishing,
  and coordinating cross-package version bumps in pyproject.toml. Apply this skill
  when cutting any release, adding a new package, bumping unifi-core, or debugging
  a versioning or publish-workflow failure — even if the user does not explicitly
  ask about tag ordering or release notes.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Monorepo Release Pipeline

The unifi-mcp repo ships six independently versioned Python packages: `unifi-core`
and `unifi-mcp-shared` live under `packages/`; `unifi-mcp-network`, `unifi-mcp-protect`,
and `unifi-mcp-access` live under `apps/`; `unifi-mcp-relay` lives under `packages/`
alongside core and shared. Each has its own PyPI identity, tag namespace, publish
workflow, and release-notes scope. Getting the release sequence wrong leaves downstream
packages referencing non-existent PyPI versions or produces contaminated release notes
that bleed across package boundaries.

## Prerequisites

- All feature PRs for the release are merged to `main`.
- Working tree is clean: `git status` shows nothing staged or modified.
- Remote is current: `git fetch origin && git log origin/main..HEAD` shows nothing.
- PyPI credentials are **not** stored locally — publishing is handled entirely by
  GitHub Actions OIDC trusted publishing (no `TWINE_PASSWORD`, no `PYPI_TOKEN`).
- Decide which packages are changing and their new versions before pushing any tag.

## Package Map

| Package | Directory | Tag namespace | Publish workflow |
|---|---|---|---|
| `unifi-core` | `packages/unifi-core/` | `core/v*` | `publish-core.yml` |
| `unifi-mcp-shared` | `packages/unifi-mcp-shared/` | `shared/v*` | `publish-shared.yml` |
| `unifi-mcp-network` | `apps/network/` | `network/v*` | `publish-network.yml` |
| `unifi-mcp-protect` | `apps/protect/` | `protect/v*` | `publish-protect.yml` |
| `unifi-mcp-access` | `apps/access/` | `access/v*` | `publish-access.yml` |
| `unifi-mcp-relay` | `packages/unifi-mcp-relay/` | `relay/v*` | `publish-relay.yml` |

When adding a new package, extend this table and complete the new-package checklist
in Procedure C before pushing any tag.

## Procedure A: hatch-vcs Tag Glob Scoping

hatch-vcs derives each package's version from git tags at build time. Without a
per-package `git_describe_command --match` glob, any tag reachable in the repo can
influence any package's version — a `network/v0.14.13` tag will contaminate
`protect`'s version if `protect`'s `git_describe_command` matches all tags.

### pyproject.toml configuration

Each package must declare both a `tag_regex` (to extract the version number) and a
`git_describe_command` scoped to its own prefix:

```toml
# packages/unifi-core/pyproject.toml
[tool.hatch.version]
source = "vcs"
raw-options.root = "../.."
raw-options.tag_regex = "^core/v(?P<version>\\d+(?:\\.\\d+)*)(?:\\S*)$"
raw-options.git_describe_command = ["git", "describe", "--dirty", "--tags", "--long", "--match", "core/v*"]
raw-options.fallback_version = "0.0.0"

# apps/network/pyproject.toml
[tool.hatch.version]
source = "vcs"
raw-options.root = "../.."
raw-options.tag_regex = "^(?:network/v|v)(?P<version>\\d+(?:\\.\\d+)*)(?:\\S*)$"
raw-options.git_describe_command = ["git", "describe", "--dirty", "--tags", "--long", "--match", "network/v*"]
raw-options.fallback_version = "0.0.0"
```

Each package's `--match` pattern must be scoped to its own tag prefix from the
Package Map. Never share or widen the `--match` pattern across packages.

### Verification before tagging

```bash
cd apps/network
pip install -e ".[dev]"
python -c "import importlib.metadata; print(importlib.metadata.version('unifi-mcp-network'))"
```

The reported version must match the tag you're about to push. A result like
`0.0.post1.dev3` or a version from a sibling package means the glob is still wrong.

**Gotcha — tag resolution is at build time, not install time.** hatch-vcs reads
tags when the package is built (during CI), not when it is installed. The tag must
be reachable on the exact commit being built. If CI triggers before the tag propagates
to GitHub, the version will be wrong even if the tag exists locally.

## Procedure B: Dependency-Ordered Tag Pushing

The dependency graph:

```
unifi-core  →  unifi-mcp-shared  →  unifi-mcp-network
                                  →  unifi-mcp-protect
                                  →  unifi-mcp-access
                                  →  unifi-mcp-relay
```

**Rule:** Push upstream tags first. Wait for PyPI to confirm the package is live
before pushing downstream tags. Downstream packages declare a minimum version of their
upstream dependencies in `pyproject.toml`; if the upstream version is not yet on PyPI
when the downstream workflow runs, pip will fail to resolve the dependency.

### Tag push sequence

```bash
# Step 1 — upstream foundation
git tag core/v0.2.0
git push origin core/v0.2.0
# WAIT: confirm https://pypi.org/project/unifi-core/ shows 0.2.0 before continuing

# Step 2 — shared layer
git tag shared/v0.4.0
git push origin shared/v0.4.0
# WAIT: confirm https://pypi.org/project/unifi-mcp-shared/ shows 0.4.0

# Step 3 — app servers (siblings; order among them doesn't matter)
git tag network/v0.14.13
git tag protect/v0.3.5
git tag access/v0.2.4
git push origin network/v0.14.13 protect/v0.3.5 access/v0.2.4
# Siblings can be pushed together — same dependency level

# Step 4 — relay
git tag relay/v0.1.0
git push origin relay/v0.1.0
```

**Never batch tags across dependency levels.** Running
`git push origin core/v0.2.0 network/v0.14.13` in a single push fires both publish
workflows simultaneously. The network workflow may start before the core package is
indexed on PyPI (~2–5 minutes after the core workflow completes).

**Worker repo:** `unifi-mcp-worker` (at `~/Repos/unifi-mcp-worker`) has a separate
npm release flow using OIDC via GitHub Actions. Apply the same ordering principle:
if the worker depends on a Python package version, confirm PyPI is updated before
pushing the worker tag.

## Procedure C: generate_release_notes.py Path Configuration

GitHub's built-in `--generate-notes` option includes every PR merged between the
previous tag and the current tag in the entire repo — regardless of which files
changed. In a monorepo, a `network/v0.14.13` release would absorb protect and access
PRs. The custom script `scripts/generate_release_notes.py` filters PRs to only those
touching paths relevant to each package.

### Per-package path configuration

Open `scripts/generate_release_notes.py` and locate the `APP_CONFIGS` dict. Each
entry is a `PackageConfig` with `path_groups` — a tuple of `PathGroup` objects that
group related paths under a label. For app servers, the structure is:

```python
APP_CONFIGS = {
    "network": PackageConfig(
        key="network",
        display_name="UniFi Network MCP",
        pypi_package="unifi-network-mcp",
        install_command="uvx unifi-network-mcp=={version}",
        path_groups=(
            PathGroup("Network MCP", ("apps/network/", "plugins/unifi-network/")),
            PathGroup("Shared Libraries", ("packages/unifi-core/", "packages/unifi-mcp-shared/")),
            PathGroup(
                "Release Infrastructure",
                (
                    ".github/workflows/publish-network.yml",
                    ".github/workflows/docker-network.yml",
                    ".github/workflows/test-network.yml",
                    ".github/workflows/bump-plugin-versions.yml",
                    *COMMON_PACKAGE_PATHS,  # pyproject.toml, uv.lock
                ),
            ),
        ),
    ),
    # ... one entry per package
}
```

Note: paths are directory prefixes (e.g., `"apps/network/"`) — not `**` globs.

Each app server entry should include:
1. Its own app/package directory as the primary `PathGroup`
2. Shared dependency directories (`packages/unifi-core/`, `packages/unifi-mcp-shared/`)
3. Its own publish/test/docker workflows as Release Infrastructure

### New-package checklist

When adding a new package, before pushing the first tag:

1. Add an entry to `APP_CONFIGS` in `scripts/generate_release_notes.py`.
2. Add the package to the Package Map table in this skill.
3. Wire the publish workflow (see Procedure D).
4. Add `tag_regex` and `git_describe_command` to `pyproject.toml` (see Procedure A).
5. Register the OIDC trusted publisher on PyPI (see Procedure D).

Skipping step 1 produces empty or cross-contaminated release notes on first publish.

### Script invocation

The script is called from within publish workflows as:

```bash
python3 scripts/generate_release_notes.py --tag "$TAG" --output /tmp/release-notes.md
```

where `$TAG` is the full tag string (e.g., `network/v0.14.13`). The script derives
the package key from the tag prefix.

## Procedure D: Publish Workflow Wiring (OIDC)

Each package has a dedicated workflow in `.github/workflows/`. The workflow triggers
on a tag push matching the package's prefix and publishes via OIDC (no stored secrets).

### Workflow template

```yaml
# .github/workflows/publish-{name}.yml
name: "{PackageName}: Publish to PyPI"

on:
  push:
    tags:
      - "{name}/v*.*.*"      # e.g., network/v*.*.* — must match tag namespace exactly

permissions:
  contents: read

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    environment:
      name: pypi              # must match the PyPI trusted publisher environment name
      url: https://pypi.org/p/{pypi-package-name}
    permissions:
      id-token: write         # required for OIDC
      contents: write         # required to create GitHub Release

    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0      # REQUIRED — hatch-vcs needs full history to find tags
          fetch-tags: true

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.13"

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Build package
        run: uv build --package {pypi-package-name}
        # e.g., uv build --package unifi-network-mcp
        # Run from repo root — uv workspace-aware build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1

      - name: Create GitHub release
        env:
          GH_TOKEN: ${{ secrets.PUSH_TOKEN }}
        run: |
          TAG="${GITHUB_REF#refs/tags/}"
          VERSION="${TAG#*/v}"
          python3 scripts/generate_release_notes.py --tag "$TAG" --output /tmp/release-notes.md
          gh release create "$TAG" \
            --title "{Display Name} v${VERSION}" \
            --notes-file /tmp/release-notes.md \
            --latest=false \
            --verify-tag
```

**`fetch-depth: 0` and `fetch-tags: true` are both mandatory.** A shallow clone
produces `0.0.post1.dev0` instead of the real version because hatch-vcs cannot walk
back to the tag.

**Do NOT use `generate_release_notes: true`** in `softprops/action-gh-release` or
any other GitHub native mechanism — that triggers GitHub's bleed behavior. Always call
`scripts/generate_release_notes.py` directly.

### PyPI trusted publisher setup (new package)

Before the first tag push for a new package:

1. Navigate to PyPI → your package → Publishing → "Add a new publisher".
2. Set: owner = your GitHub org, repo = `unifi-mcp`,
   workflow = `publish-{name}.yml`, environment = `pypi`.
3. The package must already exist on PyPI before OIDC publishing works. Create it
   manually with a `0.0.1.dev0` upload if the package is brand new.

## Procedure E: Cross-Package Version Bump Coordination

When bumping `unifi-core`, every package that declares `unifi-core` as a dependency
must have its `pyproject.toml` version constraint updated in the same PR as the code
change. Partial bumps leave packages pointing at a constraint that resolves to old
behavior — or worse, a version that no longer exists on PyPI if the old tag was
never pushed.

### Cascade audit

```bash
# Find all downstream references before bumping
grep -rn "unifi-core>=" apps/*/pyproject.toml packages/unifi-mcp-shared/pyproject.toml

# Expected output for a bump from 0.1.x → 0.2:
# apps/network/pyproject.toml:    "unifi-core>=0.2,<0.3",
# apps/protect/pyproject.toml:    "unifi-core>=0.2,<0.3",
# apps/access/pyproject.toml:     "unifi-core>=0.2,<0.3",
# packages/unifi-mcp-shared/pyproject.toml: (if present)
```

Update every version constraint to the new minimum in the same PR as the upstream
changes. Do not merge until all references are updated.

The same pattern applies to `unifi-mcp-shared` bumps — grep all app server
`pyproject.toml` files for `unifi-mcp-shared>=` and cascade.

### Bump PR content checklist

- Upstream package code changes
- All downstream `pyproject.toml` version constraints updated
- No tags in this PR — tags are pushed only after the PR merges and CI is green

## Cross-Cutting Gotchas

**Sibling tag contamination.** If `git_describe_command` `--match` is too broad
(e.g., `v*`), hatch-vcs picks up a sibling package's tag and reports the wrong
version. Symptom: `pip install unifi-mcp-network==0.14.13` installs a package that
prints `0.3.5` from `importlib.metadata`. Fix: tighten the `--match` pattern in
`raw-options.git_describe_command` in `pyproject.toml` and rebuild.

**Missing tag causes broken downstream install.** If `unifi-core` code is merged but
`core/vX.Y.Z` is never pushed, downstream packages requesting `unifi-core>=X.Y.Z`
will fail to install — pip resolver error, not a code error. Check PyPI before
debugging code. The fix is to push the missing tag and wait for the publish workflow.

**GitHub `--generate-notes` PR bleed.** Never use `generate_release_notes: true` in
workflow YAML. GitHub's native implementation ignores file paths and includes every
PR merged between the two nearest tags repo-wide. Always call
`scripts/generate_release_notes.py` instead.

**Relay Dockerfile transitive COPY.** The relay package may have a Dockerfile that
COPYs shared package source. If `packages/unifi-mcp-shared/` is restructured as part
of a coordinated release, update the Dockerfile COPY paths in the same PR — otherwise
the relay Docker image build fails at the COPY step even though the Python package
builds and publishes successfully.

**setuptools-scm version frozen at build time.** Changing the tag after the build has
run will not retroactively fix the published version. If a tag was pushed to the wrong
commit, yank the bad PyPI release, delete the tag, re-tag the correct commit, and
re-run the publish workflow.
