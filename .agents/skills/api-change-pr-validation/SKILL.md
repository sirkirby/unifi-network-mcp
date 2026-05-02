---
name: myco:api-change-pr-validation
description: |
  Activate this skill whenever preparing or reviewing a PR that touches
  UniFi MCP tool implementations, API integrations, or handler code —
  even if the user doesn't explicitly ask for validation guidance. Covers
  the full submission pipeline: running live controller smoke tests across
  all tools and categories, executing mutating cycles (create → update →
  verify → delete), composing PR descriptions with embedded raw test output,
  scoping commits to avoid unrelated changes, and applying the reviewer
  self-sufficiency standard. Apply to both community PRs and first-party
  changes alike.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# API-Touching PR Validation and Submission

PRs that modify UniFi MCP tool implementations, fix API integration bugs, or add new handlers carry elevated regression risk because the UniFi controller is stateful and mock-based tests do not catch real-world edge cases. This skill defines the validation bar and PR composition requirements that protect reviewers and prevent regressions from reaching main.

## Prerequisites

- A **live UniFi controller** must be reachable from the dev machine or CI environment. Mock-only runs do not satisfy the validation requirement.
- Know which tools and categories the PR touches. Enumerate them before starting smoke tests.
- All changed files must be committed (or staged) so the test run reflects the actual diff.

## Procedure A: Live Controller Smoke Tests

Run `scripts/live_smoke.py` against a live controller — not a mock — before opening a PR.

**Coverage requirement:** All touched tools must pass, and you must also run the full cross-category sweep to confirm no lateral regressions across the ~37 tools / 15 categories.

```bash
# Run read-only + preview smoke tests against the network server
python scripts/live_smoke.py --server network --phase safe

# Run all servers (network + protect + access)
python scripts/live_smoke.py --server all --phase safe
```

**What "passing" means:**
- Each tool returns a structurally valid response (correct keys, expected types).
- No unexpected errors or stack traces in the output.
- Tools that list resources return at least the expected schema shape even when the controller has no objects of that type.

**Gotcha:** A tool that was already broken before your PR is still your responsibility to flag. Don't silently skip known-broken tools — note them explicitly in the PR description so the reviewer knows the scope of the damage.

**Gotcha:** Mock tests give false confidence. The UniFi controller is quirky — response shapes differ between controller versions, and some fields only appear when specific configuration exists. A test that passes against a mock may fail silently against a real controller.

## Procedure B: Mutating Cycle Tests

For any PR that touches create, update, or delete handlers, run a full mutating cycle using `--phase approved` — not just the happy path.

**Full cycle:**
1. **Create** — create the resource via the tool; capture the returned ID.
2. **Partial update** — update only a subset of fields using the tool.
3. **Verify field preservation** — read back the resource and confirm fields you did NOT update are unchanged.
4. **Delete** — remove the resource and confirm it is gone (expect 204 or equivalent).

**Why field preservation matters:** The UniFi API silently drops fields that aren't included in a PUT/PATCH body. An update tool that reconstructs the full object from only the changed fields can accidentally zero out existing configuration. The verify step is the only reliable way to catch this.

**Example output to embed verbatim in the PR:**
```
[CREATE] unifi_create_firewall_policy "test-smoke-policy" → id: abc123 ✓
[UPDATE] set description="updated", name unchanged → read back: name="test-smoke-policy" ✓
[DELETE] abc123 → 204 No Content ✓
```

## Procedure C: PR Description Composition

The bar is: **a reviewer must be able to confirm correctness without pulling the branch.**

A compliant PR description contains all of the following:

### 1. Tool summary

List every tool fixed or added, grouped by category. Use the MCP tool name (snake_case, `unifi_` prefix):

```markdown
### Tools Changed
- **unifi_get_client_details** — fixed null-check on optional connection field (#138)
- **unifi_create_firewall_policy** — new tool (#142)
- **unifi_update_firewall_policy** — new tool (#142)
```

### 2. Embedded live test output

Paste the **raw terminal output**, not a prose summary. Reviewers need to see actual values and shapes, not "tests passed."

```markdown
<details>
<summary>Live test output (controller 8.x, 2024-04-01)</summary>

```
[paste raw output here — do not summarize]
```

</details>
```

Reviewers have been burned by "all tests passed" summaries that omit the one tool that returned a malformed response. Embed the raw output and let the reviewer decide what matters.

### 3. Issue references in `#N` format

Tag every issue this PR addresses using `#N` format (not "fixes GH-N" or bare numbers). GitHub autolinks and triggers auto-close on merge.

```
Closes #142, #155
```

**Gotcha:** If you reference an issue in the commit message but not in the PR body, GitHub's auto-close only triggers reliably when the PR body contains the `#N` reference. Put it in both.

## Procedure D: Commit Scoping

Each commit and PR must be cleanly scoped to its stated purpose. Mixed-scope PRs make blame tracking harder and can hide regressions — if a future bisect lands on a commit, the diff must be intelligible in isolation.

**Rules:**
- No unrelated refactors bundled with a bug fix.
- No formatting-only changes mixed with functional changes. If unavoidable, isolate them in a separate commit: `style: normalize whitespace in network handlers`.
- No validator registry changes, doc count bumps, or tool additions mixed into a PR that is nominally fixing a specific issue.

**For community PRs (level99, arnstarn, etc.):** Inspect the diff for scope creep before approving. A PR labeled "fix client lookup" that also registers new tools or alters the validator pattern is a scope violation — request splitting before merge.

## Cross-Cutting Gotchas

**"All 37 tools / 15 categories" is a moving target.** As tools are added the smoke test inventory grows. When adding a new tool, immediately add it to the inventory so the next contributor knows the expected count.

**Issue tags must use `#N` format.** Forms like "fixes GH-142" or "resolves issue 142" (without the `#`) don't autolink in GitHub's UI and may not trigger auto-close on merge.

**Scope violations are a merge blocker, not a nit.** A clean diff is a prerequisite for safe review, not a style preference. Don't approve mixed-scope PRs — they compromise the ability to bisect regressions later.
