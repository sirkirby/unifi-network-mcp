---
name: codebase-intelligence
description: >-
  Search, analyze, and query your codebase using semantic vector search, impact
  analysis, and direct SQL queries against the Oak CI database. Use when finding
  semantically related code, analyzing code change impacts before refactoring,
  discovering component relationships, recalling what was discussed or decided
  in previous sessions, looking up past conversations or outcomes, querying
  session history, checking activity logs, browsing memories, running SQL
  against activities.db, or exploring patterns that grep would miss. Do NOT use
  for storing memories — use oak_remember or oak ci remember instead.
allowed-tools: Bash, Read
user-invocable: true
---

# Codebase Intelligence

Search, analyze, and query your codebase using semantic vector search, impact analysis, and direct SQL queries against the Oak CI database.

## Quick Start

### Semantic search

```bash
# Find code related to a concept
oak ci search "form validation logic" --type code

# Find similar patterns
oak ci search "retry with exponential backoff" --type code
```

### Impact analysis

```bash
# Find all code related to what you're changing
oak ci search "AuthService token validation" --type code -n 20

# Get impact context for a specific file
oak ci context "impact of changes" -f src/services/auth.py
```

### Session and memory lookup

```bash
# What happened in recent sessions?
sqlite3 -readonly -header -column .oak/ci/activities.db \
  "SELECT id, agent, title, status, datetime(created_at_epoch, 'unixepoch', 'localtime') as started FROM sessions ORDER BY created_at_epoch DESC LIMIT 5;"

# Search past decisions and learnings
oak ci search "authentication refactor decision" --type memory

# Browse memories by type
oak ci memories --type decision
```

### Database query

```bash
# Open the database in read-only mode
sqlite3 -readonly -header -column .oak/ci/activities.db "SELECT count(*) FROM sessions;"
```

## Commands Reference

### CLI commands

| Command | Purpose |
|---------|---------|
| `oak ci search "query" --type code` | Semantic vector search for code |
| `oak ci search "query" --type memory` | Semantic search for memories |
| `oak ci search "query" -n 20` | Broader search with more results |
| `oak ci context "task" -f <file>` | Get context for current work |
| `oak ci remember "observation"` | Store a memory (NOT via SQL) |
| `oak ci memories --type gotcha` | Browse memories by type |
| `oak ci memories --status active` | Browse memories by lifecycle status |
| `oak ci resolve <id>` | Mark observation as resolved |
| `oak ci resolve --session <id>` | Bulk-resolve all observations from a session |
| `oak ci sessions` | List session summaries |
| `oak ci status` | Check daemon status |

### MCP tools

| MCP Tool | CLI Equivalent | Purpose |
|----------|---------------|---------|
| `oak_search` | `oak ci search "query"` | Semantic vector search |
| `oak_remember` | `oak ci remember "observation"` | Store a memory |
| `oak_context` | `oak ci context "task"` | Get task-relevant context |
| `oak_resolve_memory` | `oak ci resolve <uuid>` | Mark observation resolved/superseded (UUID from `oak_search`) |

### Direct SQL

```bash
sqlite3 -readonly -header -column .oak/ci/activities.db "YOUR QUERY HERE"
```

## When to Use What

| Need | Tool | Example |
|------|------|---------|
| Find similar implementations | `oak ci search --type code` | "retry with exponential backoff" |
| Understand component relationships | `oak ci context` | "how auth middleware relates to session handling" |
| Assess refactoring risk | `oak ci search --type code -n 20` | "PaymentProcessor error handling" |
| Find past decisions/gotchas | `oak ci search --type memory` | "gotchas with auth changes" |
| Recall previous discussions | `sqlite3 -readonly` | `SELECT title, summary FROM sessions WHERE ...` |
| Find what was done before | `oak ci memories` / `sqlite3` | "what did we decide about caching?" |
| Query session history | `sqlite3 -readonly` | `SELECT * FROM sessions ORDER BY ...` |
| Aggregate usage stats | `sqlite3 -readonly` | `SELECT agent_name, sum(cost_usd) FROM agent_runs ...` |
| Resolve stale observations | `oak ci resolve` | After completing work that addresses a gotcha |
| Find unresolved planning items | `sqlite3 -readonly` | `SELECT ... WHERE status='active' AND session_origin_type='planning'` |
| Run automated analysis | `oak ci agent run` | `oak ci agent run usage-report` |

## Why Semantic Search Over Grep

| Grep | Semantic Search |
|------|-----------------|
| Finds "UserService" literally | Finds code about user management regardless of naming |
| Misses synonyms (auth vs authentication) | Understands concepts are related |
| Can't find "conceptually similar" code | Groups code by purpose, not text |
| No relevance ranking | Returns most relevant first |

## Core Tables Overview

<!-- BEGIN GENERATED CORE TABLES -->
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `memory_observations` | Extracted memories/learnings | `observation`, `memory_type`, `status`, `context`, `tags`, `importance`, `session_origin_type` |
| `sessions` | Coding sessions (launch to exit) | `id`, `agent`, `status`, `summary`, `title`, `title_manually_edited`, `started_at`, `created_at_epoch` |
| `prompt_batches` | User prompts within sessions | `session_id`, `user_prompt`, `classification`, `response_summary` |
| `activities` | Raw tool executions | `session_id`, `tool_name`, `file_path`, `success`, `error_message` |
| `agent_runs` | CI agent executions | `agent_name`, `task`, `status`, `result`, `cost_usd`, `turns_used` |
| `session_link_events` | Session linking analytics | `session_id`, `event_type`, `old_parent_id`, `new_parent_id` |
| `session_relationships` | Semantic session relationships | `session_a_id`, `session_b_id`, `relationship_type`, `similarity_score` |
| `agent_schedules` | Cron scheduling state | `task_name`, `cron_expression`, `enabled`, `additional_prompt`, `last_run_at`, `next_run_at` |
| `resolution_events` | Cross-machine resolution propagation | `observation_id`, `action`, `source_machine_id`, `applied`, `content_hash` |
| `governance_audit_events` |  |  |
<!-- END GENERATED CORE TABLES -->

### Memory Types

The `memory_type` column in `memory_observations` uses these values:
- `gotcha` — Non-obvious behavior or quirk
- `bug_fix` — Solution to a bug with root cause
- `decision` — Architectural/design decision with rationale
- `discovery` — General insight about the codebase
- `trade_off` — Trade-off that was made and why
- `session_summary` — LLM-generated session summary

### Observation Status

The `status` column tracks lifecycle state:
- `active` — Current and relevant (default for all new observations)
- `resolved` — Issue was addressed in a later session
- `superseded` — Replaced by a newer, more accurate observation

### Resolving Observations

When `oak_search` or `oak_context` surfaces a gotcha, bug_fix, or discovery that you then address during your session, **resolve it** so future sessions don't see stale guidance:

1. Note the observation UUID from the `oak_search` results (e.g., `"id": "8430042a-1b01-4c86-8026-6ede46cd93d9"`).
2. After completing the fix or addressing the issue, call:
   - **MCP:** `oak_resolve_memory(id="8430042a-1b01-4c86-8026-6ede46cd93d9")`
   - **CLI:** `oak ci resolve 8430042a-1b01-4c86-8026-6ede46cd93d9`
3. For superseded observations (replaced by a better one), use `status="superseded"`.

**When to resolve:**
- You fixed a bug that was tracked as a `bug_fix` observation
- You addressed a `gotcha` (e.g., refactored the problematic code)
- A `discovery` about a problem is no longer accurate after your changes
- A `decision` was reversed or replaced by a new decision

**When NOT to resolve:**
- The observation is still accurate even after your changes
- You only partially addressed the issue
- The observation is a permanent architectural insight (e.g., "service X uses eventual consistency")

### Session Origin Types

The `session_origin_type` column classifies how the session that created the observation operated:
- `planning` — Planning-phase session (high read:edit ratio, few modifications)
- `investigation` — Exploration/debugging session (many reads, minimal edits)
- `implementation` — Active coding session (significant file modifications)
- `mixed` — Combined activity patterns

Planning/investigation observations are automatically capped at importance 5.

## Essential Queries

### Recent Sessions

```sql
SELECT id, agent, title, status,
       datetime(created_at_epoch, 'unixepoch', 'localtime') as started,
       prompt_count, tool_count
FROM sessions
ORDER BY created_at_epoch DESC
LIMIT 10;
```

### What Files Were Touched in a Session

```sql
SELECT DISTINCT file_path, tool_name, count(*) as times
FROM activities
WHERE session_id = 'SESSION_ID' AND file_path IS NOT NULL
GROUP BY file_path, tool_name
ORDER BY times DESC;
```

### Recent Memories

```sql
SELECT memory_type, substr(observation, 1, 150) as observation,
       context,
       datetime(created_at_epoch, 'unixepoch', 'localtime') as created
FROM memory_observations
ORDER BY created_at_epoch DESC
LIMIT 20;
```

### Agent Run History

```sql
SELECT agent_name, task, status, turns_used,
       printf('$%.4f', cost_usd) as cost,
       datetime(created_at_epoch, 'unixepoch', 'localtime') as created
FROM agent_runs
ORDER BY created_at_epoch DESC
LIMIT 10;
```

### Full-Text Search on Memories

```sql
SELECT m.memory_type, m.observation, m.context
FROM memory_observations m
JOIN memories_fts fts ON m.rowid = fts.rowid
WHERE memories_fts MATCH 'authentication'
ORDER BY rank
LIMIT 10;
```

### Scheduled Tasks

```sql
SELECT task_name, enabled, cron_expression, description,
       datetime(last_run_at_epoch, 'unixepoch', 'localtime') as last_run,
       datetime(next_run_at_epoch, 'unixepoch', 'localtime') as next_run
FROM agent_schedules
ORDER BY next_run_at_epoch;
```

### Observation Lifecycle Status

```sql
SELECT status, count(*) as count
FROM memory_observations
GROUP BY status;
```

### Active Observations from Planning Sessions

```sql
SELECT substr(observation, 1, 120) as observation, memory_type,
       context, session_origin_type,
       datetime(created_at_epoch, 'unixepoch', 'localtime') as created
FROM memory_observations
WHERE status = 'active' AND session_origin_type = 'planning'
ORDER BY created_at_epoch DESC
LIMIT 20;
```

### Resolution Provenance (what resolved what)

```sql
SELECT m.id, substr(m.observation, 1, 100) as observation,
       m.resolved_by_session_id, s.title as resolving_session,
       m.resolved_at
FROM memory_observations m
LEFT JOIN sessions s ON m.resolved_by_session_id = s.id
WHERE m.status = 'resolved'
ORDER BY m.resolved_at DESC
LIMIT 10;
```

## Important Notes

- Always use `-readonly` flag with `sqlite3` to prevent accidental writes
- The database uses WAL mode — safe to read while the daemon is writing
- Epoch timestamps are Unix seconds — use `datetime(col, 'unixepoch', 'localtime')` to format
- FTS5 tables (`activities_fts`, `memories_fts`) use `MATCH` syntax, not `LIKE`
- JSON columns (`tool_input`, `files_affected`, `files_created`) can be queried with `json_extract()`
- Database location: `.oak/ci/activities.db`

## Automated Analysis

For automated analysis that runs queries and produces reports:

```bash
oak ci agent run usage-report              # Cost and token usage trends
oak ci agent run productivity-report       # Session quality and error rates
oak ci agent run codebase-activity-report  # File hotspots and tool patterns
oak ci agent run prompt-analysis           # Prompt quality and recommendations
```

Reports are written to `oak/insights/` (git-tracked, team-shareable).

## Deep Dives

For detailed guidance, consult the reference documents:

- **`references/finding-related-code.md`** — Semantic search for code relationships and patterns
- **`references/impact-analysis.md`** — Assessing change impact before refactoring
- **`references/querying-databases.md`** — Full database querying guide with schema overview
- **`references/schema.md`** — Complete CREATE TABLE statements, indexes, FTS5 tables (auto-generated)
- **`references/queries.md`** — Advanced query cookbook with joins, aggregations, and debugging queries
- **`references/analysis-playbooks.md`** — Structured multi-query workflows for usage, productivity, and activity analysis
