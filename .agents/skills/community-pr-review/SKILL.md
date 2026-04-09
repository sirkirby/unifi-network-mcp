---
name: myco:community-pr-review
description: |
  Use this skill when reviewing or merging any community PR in unifi-mcp — even if the user
  just says "take a look at this PR" or "can we merge this." Covers the complete quality gate
  checklist (f-string logger ban, validator registry registration, doc site update ordering),
  the fork-edit model for trusted contributors, org-fork push limitations, the dual-subagent
  review pattern, and PR body standards. Apply this skill before approving any externally-authored
  PR, before running the merge command, and when auditing recently merged PRs for compliance.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Community PR Review and Merge

Community PRs go through a fixed quality checklist before merge. For trusted contributors
(level99 has 7+ merged PRs), the maintainer commits fixes directly to the contributor's fork
branch rather than requesting round-trip revisions — this preserves attribution while eliminating
latency. This skill documents the full workflow from first look to merge commit.

## Prerequisites

- PR is open and CI is green (or failures are understood)
- You have push access to the contributor's fork (needed for the fork-edit model)
- `AGENTS.md` is current — it is the canonical source for hard bans

---

## Subagent Decomposition (For Complex PRs)

For PRs with significant code changes or security implications, split the review across two
subagents rather than doing a single-pass review:

1. **Code review subagent** — correctness, security, quality gates (this skill's Gates 1–3)
2. **Test coverage subagent** — test completeness, coverage gaps, test pattern compliance

Before dispatching either, check out the branch locally and run `git log origin/main..HEAD`
to enumerate commits. This gives both subagents a shared commit list for scoped analysis.

PR #135 (`fix/acl-create-mac-passthrough`) established this split — it caught both a code
correctness issue and a test coverage gap that a single-pass review would have missed.

---

## Step 1 — Run the Quality Gate Checklist

Work through all three gates in order. Each is blocking.

### Gate 1: F-String Logger — Hard Blocker

**Primary target:** Every `*_manager.py` file the PR touches.

Scan for f-string logger calls:

```bash
grep -rn 'logger\.\(debug\|info\|warning\|error\|critical\)(f"' \
  $(git diff --name-only origin/main...HEAD)
```

Replace any hits with `%s`-style lazy formatting:

```python
# BLOCKED
logger.info(f"Found {count} devices on {network}")

# REQUIRED
logger.info("Found %s devices on %s", count, network)
```

**Why the manager layer is the blind spot:** Tool files (`*_tools.py`) tend to get this right
because they're reviewed more often. Manager files (`*_manager.py`) are where f-string loggers
keep appearing. In PR #119, level99's tool layer used `%s` correctly but introduced 23 f-string
calls in `device_manager.py` (14), `network_manager.py` (7), and `tools/network.py` (2). Always
check manager files explicitly.

**Implicit concatenation is invisible to grep:** Adjacent string literals (`"foo" "bar"`) cannot
be reliably caught by automated scripts. This survived a 481-call automated migration in PR #122
and was only caught by manual review. Scan manually for this pattern when logger calls span lines.

**Why this is a hard ban and not a suggestion:** F-string loggers eagerly evaluate all arguments
even when the log level is suppressed. On deployments with debug logging disabled, this creates
unnecessary overhead on every suppressed call.

---

### Gate 2: Validator Registry — Silent Failure Risk

**Target:** Any PR introducing a new tool or manager.

New tools must be registered in the validator registry. An unregistered tool silently skips
validation at runtime — no error, no warning, just unvalidated data passing through.

Check that each new tool has a corresponding entry. Verify the registration file exists and
the new tool's name appears in it. If the contributor added a tool but not a registry entry,
add it before merging.

**The `validated_data` gotcha (from PR #123):** When a validator exists but the tool accesses
`request.params` directly instead of `validated_data`, validation runs but its output is
silently discarded. After confirming a tool is registered, also confirm it reads from
`validated_data`, not from the raw params object.

---

### Gate 3: Doc Site Update — Ordering Gate

**Target:** Any PR that adds, renames, or removes tools.

The doc site must be updated as part of the same PR — not as a follow-up. The ordering matters:
the doc site should be updated *after* the tool code is finalized but *before* merge, so the
published docs stay in sync with the merged code at every point in history.

For PR #126, this gate was explicitly enforced — the PR wasn't merged until doc counts matched.

Verify: does the PR update the doc site entry count and tool listing to match what's being
merged? If not, either request the update or make it yourself before merging (see Step 2).

---

## Step 2 — Apply Fixes (Fork-Edit Model)

If you found gaps in Step 1, don't request changes — fix them directly on the contributor's
fork branch. This is the established model for trusted contributors.

```bash
# Add the contributor's fork as a remote (one-time setup)
git remote add <contributor> https://github.com/<contributor>/unifi-mcp.git

# Fetch and check out their branch
git fetch <contributor>
git checkout -b review/<pr-branch> <contributor>/<pr-branch>

# Make your fixes, then commit with attribution context
git commit -m "fix: address review gaps from PR #NNN

- Replace f-string loggers in device_manager.py (14 instances)
- Register new validator in registry
Co-authored-by: Contributor Name <email>"

# Push back to their fork
git push <contributor> HEAD:<pr-branch>
```

**Why fork-edit instead of review comments:** For contributors with a track record, a review
comment requesting changes introduces a multi-hour latency (timezone, notification lag, second
review round). Fixing directly and crediting in the commit message is faster and maintains
the contributor's name in the merge commit. Use judgment — this model is appropriate when
the gap is mechanical and the fix is unambiguous.

**Trusted contributor definition:** Level99 qualifies (7+ merged PRs). For first-time or
low-history contributors, prefer review comments so they learn the patterns.

### Org Forks — Push Limitation

**The fork-edit model only works for personal forks.** Org forks (e.g., `vigrai/unifi-mcp`
from contributor fgallese in PR #133) block `git push` back to the contributor's branch even
when "Allow edits from maintainers" is checked on the PR. That checkbox is scoped to personal
accounts — GitHub does not honor it for org-owned forks.

Decision matrix:

| Fork type | Can push fixes? | Action |
|-----------|----------------|--------|
| Personal fork (e.g., `level99/unifi-mcp`) | ✅ Yes | Fork-edit model as described above |
| Org fork (e.g., `vigrai/unifi-mcp`) | ❌ No | Merge PR as-is, then commit cleanup directly to `main` in a follow-up commit |

When merging an org-fork PR as-is and fixing on main, record what was fixed and why in the
follow-up commit message so the history is traceable.

---

## Step 3 — Verify PR Body Standards

Before merging, confirm the PR body includes:

- **What changed** — which tools or managers were added/modified
- **Why** — the use case or problem being solved
- **Testing notes** — how to verify the change works

If the PR body is sparse, edit it before merging. The PR body becomes part of the git log
context and is referenced in future sessions when diagnosing regressions.

**When a PR surfaces broader scope:** If reviewing a PR uncovers a pattern that warrants a
wider architectural fix (beyond what this contributor's PR should carry), open a separate
GitHub issue rather than expanding the PR. Link the issue in the PR body for context. This
keeps the PR focused and creates community visibility for the broader discussion.

---

## Step 4 — Merge

Once all gates pass and any fixes are committed to the fork branch:

```bash
# Merge with a merge commit (not squash) to preserve contributor commits
gh pr merge <PR-number> --merge
```

Prefer merge commits over squash so individual commits from the contributor remain visible
in history. Squash only if the branch history is genuinely noisy.

---

## Post-Merge Audit Pattern

If a PR was merged without running this checklist (e.g., merged by a contributor directly),
run a retroactive audit:

```bash
# Find files changed in the merge commit
git diff --name-only <merge-commit>^1 <merge-commit>
```

Then run Gates 1–3 against those files. If gaps are found, open a follow-up PR immediately.
Don't let an unreviewed merge sit — the pattern compounds. PR #122 was audited retroactively
using this exact approach and a fix PR was opened the same session.

---

## Quick Reference — Gate Summary

| Gate | Blocker level | Where to look | Common miss |
|------|--------------|---------------|-------------|
| F-string loggers | Hard block | `*_manager.py` | Manager layer even when tool layer is clean |
| Validator registry | Critical (silent) | Registry file + `validated_data` usage | Tool registered but reads raw params |
| Doc site count | Ordering gate | Doc site entry count | Updated after merge instead of before |
