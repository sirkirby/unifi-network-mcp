---
name: myco:release-package-version
description: |
  Activate after any PR that changes package code in the unifi-mcp monorepo, or
  when a release version needs to be published to PyPI or npm. Covers operational
  release execution: identifying which packages need tagging (packages/unifi-core/,
  packages/unifi-mcp-shared/, apps/network|protect|access|api,
  packages/unifi-mcp-relay/), correct tag namespace per package (core/v*, shared/v*,
  network/v*, protect/v*, access/v*, api/v*, relay/v*), no-batch push sequence with
  dependency ordering, why PR merge does not trigger PyPI (hatch-vcs resolves version
  from git tags at build time), verifying OIDC-triggered CI publish runs, publishing
  the worker npm package from ~/Repos/unifi-mcp-worker, and diagnosing/fixing
  hatch-vcs cross-tag contamination when a broad --match pattern picks up a sibling
  app tag. For pipeline wiring, OIDC setup, or release notes config, see
  monorepo-release-pipeline. Apply even if the user only asks "why didn't PyPI
  update?" or "how do I release the network package?"
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Releasing a Package Version in unifi-mcp

After a PR is merged, version publication is **not automatic**. `hatch-vcs` resolves
the version from the nearest matching git tag at **build time** — PyPI stays at the
prior version until a tag is pushed to `origin`. The OIDC GitHub Actions publish
workflow fires only when a matching tag lands on `origin`. PR merge alone does nothing.

For pipeline infrastructure (wiring new publish workflows, OIDC trusted publisher
registration, release notes path config), see the `monorepo-release-pipeline` skill.
This skill covers the **operational execution** of each release.

## Prerequisites

- PR is merged to `main`
- Working tree is clean: `git status` shows nothing staged or modified
- Remote is current: `git fetch origin && git log origin/main..HEAD` shows nothing
- You know which packages had code changes (see Procedure A)
- Push access to `origin` (upstream unifi-mcp repo)
- For worker releases: access to `~/Repos/unifi-mcp-worker`

## Procedure A: Identify Which Packages Need Tagging

Each package that had **code changes** in the merged PR needs its own tag push.
Packages with only dependency bumps in `pyproject.toml` may or may not need a tag —
use judgment on whether the consumer-visible behavior changed.

```bash
# Files changed in the most recent merge commit
git log --name-only -1 main

# Or diff against the PR's merge base
git diff --name-only <merge-base>..main
```

**Package → directory mapping:**

| Package | Directory | Tag namespace |
|---|---|---|
| `unifi-core` | `packages/unifi-core/` | `core/v*` |
| `unifi-mcp-shared` | `packages/unifi-mcp-shared/` | `shared/v*` |
| `unifi-mcp-network` | `apps/network/` | `network/v*` |
| `unifi-mcp-protect` | `apps/protect/` | `protect/v*` |
| `unifi-mcp-access` | `apps/access/` | `access/v*` |
| `unifi-mcp-api` | `apps/api/` | `api/v*` |
| `unifi-mcp-relay` | `packages/unifi-mcp-relay/` | `relay/v*` |
| Worker (npm) | `~/Repos/unifi-mcp-worker` | plain semver `v*` |

**Dependency graph:**

```
unifi-core  →  unifi-mcp-shared  →  unifi-mcp-network
                                  →  unifi-mcp-protect
                                  →  unifi-mcp-access
                                  →  unifi-mcp-api
                                  →  unifi-mcp-relay
```

`unifi-mcp-shared` underpins all app servers. If shared bumps, any app that pins it
may need a version bump too.

**Scoped security patches:** If a Dependabot alert affects only one app (e.g., Pillow
via `uiprotect` → `apps/protect/`), only that app needs a tag. Do not tag unaffected
apps.

## Procedure B: Push Tags in Dependency Order

**Rule: no batching. Push one tag at a time, wait for CI green, then push the next.**

**Tag format:**

```
{tag-namespace}/v{semver}
```

Examples:

```bash
git tag core/v0.2.0
git tag shared/v1.2.0        # NOT unifi-mcp-shared/v1.2.0 — namespace is "shared"
git tag network/v0.4.0
git tag protect/v0.3.2
git tag access/v0.2.1
git tag relay/v0.1.0
```

**Correct push order** (upstream before downstream):

1. `unifi-core` (if changed) — upstream foundation for everything
2. `unifi-mcp-shared` (if changed) — all app servers depend on it
3. App servers — `network`, `protect`, `access`, `api`, `relay` (after shared/core)
4. Worker npm — after server packages are live on PyPI

**Tag and push sequence (shared + network example):**

```bash
git tag shared/v1.2.0
git push origin shared/v1.2.0
# WAIT: confirm https://pypi.org/project/unifi-mcp-shared/ shows 1.2.0 before continuing

git tag network/v0.4.0
git push origin network/v0.4.0
```

> **Silent failure gotcha (Session 3):** Pushing a server tag before its upstream
> dependency is live on PyPI causes the server's CI build to resolve the old version
> and publish a stale or broken release. The tag push succeeds with exit 0 but the
> published artifact is wrong. Always confirm upstream CI is green and PyPI reflects
> the new version before pushing the downstream tag.

> **No batching:** Do NOT use `git push --tags` or push multiple tags in a single
> push command. Each tag triggers a separate CI build that must resolve the correct
> upstream versions on PyPI. Racing builds cause silent version mismatches.

## Procedure C: Verify PyPI Publishing

After each tag push:

1. Go to the repo's **Actions** tab on GitHub
2. Find the tag-triggered publish workflow (e.g., `publish-network.yml`)
3. Confirm it completed with a green check
4. Verify: `pip index versions <pypi-package-name>` or `https://pypi.org/project/<name>/`

**Why tag push = release trigger:** `hatch-vcs` calls
`git describe --tags --match <pattern>` at build time to generate the version. Until
the tag exists on `origin` when the CI build runs, the build sees the prior version.
Pushing the tag is the release — not opening the PR, not merging it.

## Procedure D: Publish the Worker (npm)

The Cloudflare MCP Worker lives in a **separate repo**: `~/Repos/unifi-mcp-worker`.
It follows the same tag-triggered OIDC pattern but publishes to npm.

```bash
cd ~/Repos/unifi-mcp-worker

# Worker uses plain semver tags (no package prefix)
git tag v1.2.3
git push origin v1.2.3
```

The Actions workflow fires on the tag and publishes to npm via OIDC trusted publishing.

> **npm self-upgrade gotcha:** Do NOT run `npm install -g npm@latest` in the worker
> CI pipeline. On Node 22, the arborist rebuild during npm's self-upgrade drops the
> `promise-retry` dependency, breaking the entire global npm installation. Node 22
> ships with a working npm (v10.x) — leave it as-is. This caused a silent publish
> failure in the worker pipeline.

## Procedure E: Fix hatch-vcs Cross-Tag Contamination

If a CI version test fails with a version string from a sibling app, the
`pyproject.toml` match pattern is too broad.

**Symptom:**
```
AssertionError: expected network/v0.4.0, got protect/v0.3.2-5-gabcdef
```

**Diagnosis — check the match pattern:**
```bash
grep -n "git_describe_command" apps/network/pyproject.toml
```

**Broken pattern** (matches all tags including siblings):
```toml
raw-options.git_describe_command = ["git", "describe", "--dirty", "--tags", "--long", "--match", "v[0-9]*"]
```

**Fix** — scope the match to this app only:
```toml
raw-options.git_describe_command = ["git", "describe", "--dirty", "--tags", "--long", "--match", "network/v*"]
```

**Correct `--match` value per package:**

| Package | `--match` pattern |
|---|---|
| `unifi-core` | `core/v*` |
| `unifi-mcp-shared` | `shared/v*` |
| `unifi-mcp-network` | `network/v*` |
| `unifi-mcp-protect` | `protect/v*` |
| `unifi-mcp-access` | `access/v*` |
| `unifi-mcp-api` | `api/v*` |
| `unifi-mcp-relay` | `relay/v*` |

`access` was already correctly scoped; `network` needed the fix (Session 17). Audit
`protect`, `relay`, and any app created when the monorepo had only one app — any
package carrying a legacy broad pattern like `v[0-9]*` will break as soon as a
sibling tag is pushed.

**After editing `pyproject.toml`, verify locally:**
```bash
cd apps/network
hatch version        # should show network's own tag-derived version
python -m pytest tests/test_version_matches_git_tag.py -v
```

**Why this happens:** A broad `v[0-9]*` pattern was fine in a single-app repo. When
new apps were added with prefixed tags (`protect/v0.3.2`), `git describe` still matches
because the tag name *contains* a `v0.x.y` fragment. The newest matching tag wins,
which may be a sibling's.

## Quick Reference

```
Tag format:     {namespace}/v{semver}     e.g. network/v0.4.0, shared/v1.2.0
Worker tags:    plain semver              e.g. v1.2.3 (in ~/Repos/unifi-mcp-worker)
Push order:     core → shared → servers/relay → worker
No batching:    one tag, wait for green CI + PyPI confirms, then next
PyPI trigger:   tag push via OIDC GitHub Actions
npm trigger:    tag push in ~/Repos/unifi-mcp-worker
hatch-vcs fix:  --match must be app-scoped: network/v*, shared/v*, access/v*, etc.
```
