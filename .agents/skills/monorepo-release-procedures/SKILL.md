---
name: myco:monorepo-release-procedures
description: |
  Use this skill when releasing any package in the unifi-mcp monorepo —
  network, protect, access, relay, unifi-core, or unifi-mcp-shared — even
  if the user doesn't explicitly ask about release procedures. Covers:
  hatch-vcs tag scoping per app (app-name/v* patterns, never broad v[0-9]*
  wildcards that cause cross-package contamination); multi-package release
  ordering with dependency version pinning before the tag wave; release notes
  automation via scripts/generate_release_notes.py instead of GitHub's
  --generate-notes (which leaks unrelated cross-package PRs); path scoping
  configuration required for every new package before its first publish;
  publish workflow anatomy for OIDC trusted publishing (PyPI vs. npm); and
  app vs. library versioning semantics including when writeback to plugin.json
  and server.json occurs vs. when dynamic hatch-vcs versioning applies.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Monorepo Package Release Pipeline

The unifi-mcp repository is a multi-package monorepo containing app packages
(network, protect, access), library packages (unifi-core, unifi-mcp-shared),
and the relay package. Each package has its own tag namespace, publish workflow,
and versioning semantics. Single-repo tooling assumptions — broad tag globs,
GitHub's built-in release notes, uniform writeback workflows — all fail silently
in this context. This skill covers every step required for a correct release.

## Prerequisites

- You are on `main` with a clean working tree.
- All PRs touching the package(s) being released are merged.
- You have write access to push tags and trigger GitHub Actions.
- For library package releases: no downstream app changes are in flight that
  depend on the new library version (coordinate timing to avoid broken windows).

## Procedure A: hatch-vcs Tag Scoping Per Package

Every app's `pyproject.toml` must use a strict, app-scoped `git_describe_command`.
The broad wildcard `v[0-9]*` matches **any** tag starting with `v` — including tags
from sibling apps — causing `git describe` to compute version strings from the wrong
app's history. This fails silently in local dev but breaks `test_version_matches_git_tag`
in CI after a sibling tag is pushed.

### Correct patterns per package

| Package | Match pattern |
|---|---|
| network | `network/v*` |
| protect | `protect/v*` |
| access | `access/v*` |
| relay | `relay/v*` |
| unifi-core | `core/v*` |
| unifi-mcp-shared | `shared/v*` |

### pyproject.toml configuration

```toml
# apps/network/pyproject.toml  (and analogous files for other packages)
[tool.hatch.version]
source = "vcs"

[tool.hatch.version.raw-options]
git_describe_command = [
  "git", "describe", "--dirty", "--tags", "--long",
  "--match", "network/v*"   # ← MUST be app-scoped, never "v[0-9]*"
]
```

To verify a package's pattern before tagging:

```bash
grep -A3 "git_describe_command" apps/network/pyproject.toml
```

If the match field is missing or uses a broad pattern, fix it and commit before
creating the release tag.

## Procedure B: App vs. Library Versioning and Writeback Behavior

Understanding writeback is essential because the `bump-plugin-versions.yml` workflow
behaves differently for apps vs. libraries, and a "No version changes to commit"
message means two completely different things depending on package type.

### Library packages (unifi-core, unifi-mcp-shared, relay)

These packages use `dynamic = ["version"]` in `pyproject.toml` with hatch-vcs.
Version is derived from the git tag **at build time** — no `_version.py` is ever
committed to the repo. When a library tag is pushed:

- `bump-plugin-versions.yml` runs and outputs: `No version changes to commit`
- This is **correct and expected** — not a bug or a missed step.

### App packages (network, protect, access)

These packages have writable manifest assets that get updated on tag:

- `plugins/unifi-network/.claude-plugin/plugin.json`
- `plugins/unifi-protect/.claude-plugin/plugin.json`
- `plugins/unifi-access/.claude-plugin/plugin.json`
- `apps/{network,protect,access}/server.json`

When an app tag is pushed, the workflow commits a version writeback to these files.
If the writeback commit is missing, the manifests will be stale.

**Rule:** Never expect writeback from a library package tag. Never accept a
missing writeback from an app package tag.

## Procedure C: Multi-Package Release Ordering and Dependency Pinning

When releasing multiple packages in the same wave (e.g., a coordinated security
update touching core, shared, and all apps), ordering matters. Downstream packages
must be built against the published upstream version — not an unpublished in-flight tag.

### Release order

```
1. unifi-core          (leaf — no internal dependencies)
2. unifi-mcp-shared    (depends on unifi-core)
3. network             (depends on unifi-mcp-shared + unifi-core)
   protect             (independent of network/access — can be parallel)
   access              (independent of network/protect — can be parallel)
4. relay               (npm, independent ordering within Python wave)
```

### Pin version bounds before the tag wave

Before tagging any downstream package, update its `pyproject.toml` to pin the
new upstream version and commit to main:

```toml
# apps/network/pyproject.toml — after unifi-core v1.2.0 and shared v0.5.0 published
dependencies = [
  "unifi-core>=1.2.0",
  "unifi-mcp-shared>=0.5.0",
]
```

Commit the version bump, then push the downstream tag. If you tag before the
upstream is live on PyPI, the publish workflow fails on dependency resolution.

### Tag format per package

```bash
git tag core/v1.2.0
git tag shared/v0.5.0
git tag network/v2.1.0
git tag protect/v1.4.0
git tag access/v0.8.0
git tag relay/v0.1.4
git push origin <tag>   # one at a time, in dependency order — no batching
```

No batching, always push in dependency order, always tag upstream packages when
their code changes (see `gotcha_batch_tag_push.md` in memory).

## Procedure D: Release Notes — Use the Custom Script, Not GitHub's Flag

GitHub's `--generate-notes` flag includes **all PRs merged between two tags on main**,
regardless of which files they touched. In a monorepo, a `relay/v0.1.2...relay/v0.1.3`
tag range will include every Network and Protect PR merged during that window.
GitHub's `.github/release.yml` config can categorize by label or author but
**cannot filter by file path** — there is no built-in fix.

### The fix: `scripts/generate_release_notes.py`

All four publish workflows (`publish-network.yml`, `publish-protect.yml`,
`publish-access.yml`, `publish-relay.yml`) call this script instead of
`gh release create --generate-notes`. The script:

1. Parses the current tag to identify the package namespace (e.g., `relay`)
2. Finds the previous tag in that namespace as the range start
3. Filters commits to only those touching package-relevant paths
4. Omits version-sync commits (`chore(plugins): sync plugin versions...`)
5. Renders grouped Markdown with an "omitted N unrelated commits" note

### Path scoping per package

The script uses `APP_CONFIGS` — a dict of `PackageConfig` objects with `PathGroup`
tuples. Each `PathGroup` is a named collection of directory-prefix strings:

```
Relay:
  packages/unifi-mcp-relay/
  packages/unifi-mcp-shared/
  packages/unifi-core/
  uv.lock, pyproject.toml
  .github/workflows/publish-relay.yml, docker workflows

Network:
  apps/network/
  plugins/unifi-network/
  packages/unifi-mcp-shared/
  packages/unifi-core/
  uv.lock, pyproject.toml
  .github/workflows/publish-network.yml, bump-plugin-versions.yml

Protect / Access: (analogous to Network, with their own app/plugin paths)
```

### Dry-run verification

```bash
python scripts/generate_release_notes.py --tag relay/v0.1.4 --dry-run
```

Verify the output includes only relay-relevant commits before the workflow fires.

## Procedure E: Adding a New Package (Pre-Publish Gate)

Before a new package's first publish, complete this checklist. Skipping any item
causes a silent failure on first release.

### Checklist

1. **hatch-vcs tag pattern** — add `--match newpkg/v*` to the package's
   `pyproject.toml` `git_describe_command`. Verify with a local `git describe` test.

2. **Release notes path scoping** — add a `PackageConfig` entry for the new
   package in `scripts/generate_release_notes.py`'s `APP_CONFIGS` dict. This is
   a hard pre-publish gate: if path scoping is absent, the first release will
   include every unrelated PR merged since the repo's creation.

   ```python
   # scripts/generate_release_notes.py — add entry to APP_CONFIGS
   APP_CONFIGS = {
       ...,
       "newpkg": PackageConfig(
           key="newpkg",
           display_name="UniFi NewPkg MCP",
           pypi_package="unifi-newpkg-mcp",
           install_command="uvx unifi-newpkg-mcp=={version}",
           path_groups=(
               PathGroup("NewPkg MCP", ("packages/unifi-newpkg/",)),
               PathGroup("Shared Libraries", ("packages/unifi-core/", "packages/unifi-mcp-shared/")),
               PathGroup(
                   "Release Infrastructure",
                   (
                       ".github/workflows/publish-newpkg.yml",
                       *COMMON_PACKAGE_PATHS,
                   ),
               ),
           ),
       ),
   }
   ```

3. **Publish workflow** — create `.github/workflows/publish-newpkg.yml` following
   the pattern of an existing workflow for the same type (PyPI vs. npm OIDC).
   The tag trigger must match the package namespace: `on: push: tags: ["newpkg/v*"]`.

4. **Version bounds in dependents** — if other packages depend on the new package,
   add pinned version bounds to their `pyproject.toml` before their next release.

5. **Dry-run verification** — after creating the first tag locally (do not push yet),
   run `scripts/generate_release_notes.py --tag newpkg/v0.1.0 --dry-run` to confirm
   path scoping is working.

## Procedure F: Publish Workflow Anatomy and OIDC Publishing

### PyPI packages (network, protect, access, unifi-core, unifi-mcp-shared)

Workflows use OIDC trusted publishing — no stored PyPI token. The workflow must:

- Declare `permissions: id-token: write` at the job level
- Use `pypa/gh-action-pypi-publish` with no explicit token
- Be triggered by the correct tag pattern (e.g., `on: push: tags: ["network/v*"]`)

If the tag pattern doesn't match, the workflow silently does not fire. After
pushing a tag, check the Actions tab within 30 seconds — if no run appears,
the tag glob is wrong.

### relay (npm via GitHub Actions OIDC)

The relay package lives at `packages/unifi-mcp-relay/` and publishes to npm.
It uses GitHub Actions OIDC (not PyPI OIDC). See `reference_worker_npm_publishing.md`
in memory for the worker repo's OIDC setup — the relay workflow follows the same pattern.

Key difference: relay's workflow triggers on `relay/v*` tags and uses
`actions/setup-node` with `registry-url: https://registry.npmjs.org`.

### Workflow-to-tag mapping

| Tag pushed | Workflow that fires |
|---|---|
| `network/v*` | `publish-network.yml` |
| `protect/v*` | `publish-protect.yml` |
| `access/v*` | `publish-access.yml` |
| `relay/v*` | `publish-relay.yml` |
| `core/v*` | `publish-core.yml` |
| `shared/v*` | `publish-shared.yml` |

Confirm each workflow's `on.push.tags` array before a coordinated release wave.

## Cross-Cutting Gotchas

**Tag glob contamination is silent until CI.** A broad `v[0-9]*` pattern in
`git_describe_command` won't cause local build failures. It only surfaces when
a sibling app tags after you do — at which point your app's version test fails
in CI with no obvious cause. Audit all packages' tag patterns before any
coordinated release.

**Dependency ordering is a hard constraint, not a preference.** If you push a
downstream tag before the upstream package is live on PyPI, the publish workflow's
`uv sync` or `pip install` step fails. There is no retry mechanism — delete the
tag, wait for upstream to propagate (~2 min), and re-push.

**Release notes path scoping is a one-time setup with permanent consequences.**
A new package published without path scoping in `scripts/generate_release_notes.py`
will produce release notes including the entire repo's history from day one.
Treat the path scoping step as a merge blocker for any new-package PR.
