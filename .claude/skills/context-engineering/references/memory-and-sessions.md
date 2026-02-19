# Memory and Sessions

This reference covers how to use memory effectively in agent-assisted development: the three memory types, how to extract and consolidate knowledge, provenance tracking, and practical patterns for OAK CI's memory tools.

---

## Memory Types

### Episodic Memory (What Happened)

Records of specific events, experiences, and outcomes. Time-stamped, contextual, narrative — answers "what happened last time?"

- Tied to a specific moment and context
- Includes cause, effect, and resolution
- Most valuable when recent; decays in relevance over time
- Forms raw material for semantic memory through consolidation

**Examples:**
- "Refactoring broke auth tests — circular imports between `auth_service.py` and `user_service.py`"
- "Customer API returned 429s after batch size increased to 100 — dropped to 50"

**OAK CI mapping:** Observations with type `bug_fix` or `gotcha`

### Procedural Memory (How To Do Things)

Skills, workflows, and step-by-step processes. Relatively stable — changes slowly as best practices evolve.

- Describes a sequence of actions to achieve a goal
- Codified in documentation, runbooks, or constitutions
- Most valuable when accurate and current

**Examples:**
- "To add a new API endpoint: create route, add service method, write tests, update docs"
- "To add a new OAK feature: create manifest.yaml, implement RFC, add commands, register in feature service"

**OAK CI mapping:** Constitutions (`oak/constitution.md`), skill files, golden paths. Procedural memory lives in structured documents rather than individual observations.

### Semantic Memory (Facts and Concepts)

General knowledge about the domain, codebase, or system. Context-independent — true regardless of when or how it was learned.

- Factual, declarative knowledge
- Stable until the underlying reality changes
- Provides context without requiring the full history

**Examples:**
- "This project uses PostgreSQL 15 with read replicas for reporting queries"
- "We chose event sourcing for the order system to support audit requirements"

**OAK CI mapping:** Observations with type `discovery`, `decision`, or `trade_off`

### Memory Type Selection Guide

| You want to remember... | Memory Type | OAK CI Type |
|---|---|---|
| A bug you fixed and why | Episodic | `bug_fix` |
| A non-obvious behavior | Episodic | `gotcha` |
| How to deploy the app | Procedural | Constitution/Skill |
| An architectural decision | Semantic | `decision` |
| A pattern you discovered | Semantic | `discovery` |
| A trade-off you accepted | Semantic | `trade_off` |

**Rule of thumb:** If it happened once and the specifics matter, it is episodic. If it is always true (until something changes), it is semantic. If it describes how to do something, it is procedural.

---

## Memory Extraction Pipeline

Raw experience becomes useful memory through four stages: capture, classify, consolidate, retrieve.

### 1. Capture (During Work)

Record observations as they happen — context and detail fade quickly. Capture surprising behavior, root causes (not symptoms), decisions with rationale, and codebase discoveries.

```bash
# Good — specific, includes file path and root cause
oak ci remember "Auth middleware silently swallows ConnectionError — returns 200 instead of 503. Bare except on line 47" --type gotcha --context src/middleware/auth.py

# Bad — vague, no actionable detail
oak ci remember "Auth has a bug" --type gotcha
```

**Every observation should include:** what happened, where it applies (file paths), and why it matters.

### 2. Classify

Assign a type based on what kind of knowledge the observation represents.

| Observation is about... | Classify as |
|---|---|
| Something that broke and how you fixed it | `bug_fix` |
| A non-obvious behavior that could trip someone up | `gotcha` |
| A fact about the system or domain | `discovery` |
| A choice you made and why | `decision` |
| A compromise with known downsides | `trade_off` |

### 3. Consolidate

Individual episodic memories should consolidate into semantic knowledge over time — specific events become general understanding.

**Example:** Three separate gotchas about parallel test failures (shared session state, shared mock gateway, shared email queue) consolidate into one decision: "Integration tests using shared external state must use the `isolated_services` fixture."

```bash
# Create the consolidated observation
oak ci remember "Integration tests with shared external state must use isolated_services fixture" --type decision --context tests/conftest.py

# Resolve the observations it replaces
oak ci resolve <uuid-1> --status superseded
oak ci resolve <uuid-2> --status superseded
```

**When to consolidate:** Three or more observations about the same topic, or a pattern has emerged from individual incidents.

### 4. Retrieve

Pull relevant memories when starting new work.

```bash
# Automatic context assembly — curated code + memories based on task and files
oak ci context "refactoring the auth service" -f src/services/auth.py

# Targeted search by type
oak ci search "auth import issues" --type memory
oak ci search "rate limiting" --type all
```

---

## Provenance Tracking

Every memory should answer: who learned this, when, and from what evidence?

### Why Provenance Matters

Stale memories are worse than no memories — they actively mislead. An observation saying "the users table has no index on email" causes agents to work around a problem that was fixed last week. Provenance (when recorded, what code referenced) lets you detect and resolve staleness.

### OAK CI Provenance Fields

| Field | What it records |
|---|---|
| `session_id` | Which session created the observation |
| `created_at_epoch` | When it was created (Unix timestamp) |
| `context` | File path or additional context linking to code |
| `session_origin_type` | Planning, investigation, or implementation |
| `resolved_by_session_id` | Which session marked it resolved |
| `resolved_at` | When it was resolved |

### Provenance Best Practices

**Include file paths in the context field.** Ties memory to code, enabling staleness detection when code changes.

```bash
# Good — tied to specific code
oak ci remember "Rate limiter uses fixed window, not sliding — burst at window boundaries" --type discovery --context src/middleware/rate_limiter.py

# Weak — floating, hard to verify later
oak ci remember "Rate limiter has a burst problem" --type discovery
```

**Include error messages and specific details** for searchability. **Record session type** — implementation observations (tested and verified) carry more weight than planning observations (potentially speculative).

---

## Memory-as-a-Tool Pattern

Instead of holding everything in the context window, treat memory as an external tool queried on demand.

### The Workflow

```
Agent receives task -> searches memory -> gets relevant results -> uses in current work -> stores new learnings -> future sessions benefit
```

**Benefits:** Context window stays focused on the current task. Memory accumulates across sessions. Each retrieval is targeted. Knowledge persists beyond session boundaries and is shared across agents.

### OAK CI Commands

**Store** during work:
```bash
oak ci remember "Billing API rate limits at 100 req/min — returns 429 with Retry-After" --type discovery
```

**Retrieve** when starting work:
```bash
oak ci search "billing API rate limits" --type memory
oak ci context "refactoring the auth service" -f src/services/auth.py
```

**Resolve** when memory becomes stale:
```bash
oak ci resolve <uuid> --reason "Refactored to eliminate circular dependency"
oak ci resolve <uuid> --status superseded --reason "Replaced by event-driven architecture"
```

---

## Session Memory Patterns

### Session Summaries

At session end, generate a summary: what was accomplished, what was learned, what remains. OAK CI stores these as `session_summary` observations, creating episodic memories for future sessions.

**A good session summary includes:**
- Tasks completed (with file paths)
- Decisions made and their rationale
- Open questions or unfinished work
- Observations stored during the session

### Cross-Session Context

Retrieve relevant context from past sessions when starting new work:

```bash
oak ci context "continuing the auth refactor" -f src/services/auth.py -f src/services/user.py
```

This returns relevant memories (including past session summaries) alongside related code, providing continuity without full conversation history.

### Memory Decay and Maintenance

Not all memories stay relevant. Active maintenance prevents memory rot. Resolve observations when: the referenced code was refactored or deleted, the decision was reversed, the gotcha was fixed, or newer observations cover the same ground better.

| Situation | Action |
|---|---|
| Bug was fixed | Resolve the `bug_fix` observation |
| Gotcha no longer applies | Resolve the `gotcha` observation |
| Decision was reversed | Mark `superseded`, create new decision |
| Observations overlap | Consolidate into one, resolve the rest |
| Code was deleted | Resolve related observations |

---

## Common Memory Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Storing everything | Bloat, poor retrieval — important observations buried in noise | Be selective: only store what would help a future session |
| Vague observations | "Auth was broken" — useless for retrieval, no actionable guidance | Include specifics: error messages, file paths, root cause |
| Never resolving | Stale memories mislead sessions into working around fixed problems | Resolve observations after addressing the issue |
| No context field | Memory disconnected from code, cannot validate against current state | Always include file paths or module names |
| Duplicate observations | Same insight stored multiple times degrades precision | Search before storing; consolidate duplicates |
| Session-only memory | Knowledge lost when session ends | Use persistent memory for learnings worth keeping |
| Over-consolidation | Premature generalization loses nuance from specific incidents | Wait for three or more instances before generalizing |
| No provenance | Cannot assess validity; no way to trace back to evidence | Include file paths, timestamps, and specific details |
