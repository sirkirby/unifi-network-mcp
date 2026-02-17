# Oak CI Database Schema Reference

Complete DDL for the Oak CI SQLite database at `.oak/ci/activities.db`.

Current schema version: **3**

## memory_observations

Source of truth for extracted memories. ChromaDB is a search index over this data.

```sql
CREATE TABLE IF NOT EXISTS memory_observations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    prompt_batch_id INTEGER,
    observation TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    context TEXT,
    tags TEXT,  -- Comma-separated tags
    importance INTEGER DEFAULT 5,
    file_path TEXT,
    created_at TEXT NOT NULL,
    created_at_epoch INTEGER NOT NULL,
    embedded BOOLEAN DEFAULT FALSE,  -- Has this been added to ChromaDB?
    content_hash TEXT,  -- Hash for cross-machine deduplication
    source_machine_id TEXT,  -- Machine that originated this record
    status TEXT DEFAULT 'active',              -- active | resolved | superseded
    resolved_by_session_id TEXT,               -- Session that resolved this
    resolved_at TEXT,                          -- ISO timestamp of resolution
    superseded_by TEXT,                        -- Observation ID that supersedes this
    session_origin_type TEXT,                  -- planning | investigation | implementation | mixed
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (prompt_batch_id) REFERENCES prompt_batches(id)
);
```

**Key indexes:** `idx_memory_observations_embedded`, `idx_memory_observations_session`, `idx_memory_observations_hash`, `idx_memory_observations_type`, `idx_memory_observations_context`, `idx_memory_observations_created`, `idx_memory_observations_type_created`, `idx_memory_observations_source_machine`, `idx_memory_observations_status`, `idx_memory_observations_resolved_by`, `idx_memory_observations_origin_type`

## sessions

Tracks coding sessions from launch to exit.

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    project_root TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT DEFAULT 'active',  -- active, completed, abandoned
    prompt_count INTEGER DEFAULT 0,
    tool_count INTEGER DEFAULT 0,
    processed BOOLEAN DEFAULT FALSE,  -- Has background processor handled this?
    summary TEXT,  -- LLM-generated session summary
    title TEXT,  -- LLM-generated short session title (10-20 words)
    created_at_epoch INTEGER NOT NULL,
    parent_session_id TEXT,  -- Session this was derived from
    parent_session_reason TEXT,  -- Why linked: 'clear', 'compact', 'inferred'
    source_machine_id TEXT,  -- Machine that originated this record
    transcript_path TEXT  -- Path to session transcript file for recovery
);
```

**Key indexes:** `idx_sessions_status`, `idx_sessions_processed`, `idx_sessions_created_at`, `idx_sessions_source_machine`

## prompt_batches

Activities between user prompts — the unit of processing.

```sql
CREATE TABLE IF NOT EXISTS prompt_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    prompt_number INTEGER NOT NULL,  -- Sequence number within session
    user_prompt TEXT,  -- Full user prompt (up to 10K chars) for context
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT DEFAULT 'active',  -- active, completed
    activity_count INTEGER DEFAULT 0,
    processed BOOLEAN DEFAULT FALSE,  -- Has background processor handled this?
    classification TEXT,  -- LLM classification: exploration, implementation, debugging, refactoring
    source_type TEXT DEFAULT 'user',  -- user, agent_notification, plan, system, derived_plan
    plan_file_path TEXT,  -- Path to plan file (for source_type='plan')
    plan_content TEXT,  -- Full plan content (stored for self-contained CI)
    plan_embedded INTEGER DEFAULT 0,  -- Has plan been indexed in ChromaDB?
    created_at_epoch INTEGER NOT NULL,
    content_hash TEXT,  -- Hash for cross-machine deduplication
    source_plan_batch_id INTEGER,  -- Link to plan batch being implemented
    source_machine_id TEXT,  -- Machine that originated this record
    response_summary TEXT,  -- Agent's final response/summary
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (source_plan_batch_id) REFERENCES prompt_batches(id)
);
```

**Key indexes:** `idx_prompt_batches_session`, `idx_prompt_batches_processed`, `idx_prompt_batches_hash`, `idx_prompt_batches_source_machine`

## activities

Raw tool executions logged during sessions.

```sql
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    prompt_batch_id INTEGER,  -- Links to the prompt batch (for prompt-level processing)
    tool_name TEXT NOT NULL,
    tool_input TEXT,  -- JSON of input params (sanitized)
    tool_output_summary TEXT,  -- Brief summary, not full output
    file_path TEXT,  -- Primary file affected (if any)
    files_affected TEXT,  -- JSON array of all files
    duration_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    timestamp TEXT NOT NULL,
    timestamp_epoch INTEGER NOT NULL,
    processed BOOLEAN DEFAULT FALSE,  -- Has this activity been processed?
    observation_id TEXT,  -- Link to extracted observation (if any)
    content_hash TEXT,  -- Hash for cross-machine deduplication
    source_machine_id TEXT,  -- Machine that originated this record
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (prompt_batch_id) REFERENCES prompt_batches(id)
);
```

**Key indexes:** `idx_activities_session`, `idx_activities_prompt_batch`, `idx_activities_tool`, `idx_activities_processed`, `idx_activities_timestamp`, `idx_activities_hash`, `idx_activities_source_machine`

## agent_runs

CI agent executions via claude-code-sdk.

```sql
CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    task TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, cancelled, timeout

    -- Timing
    created_at TEXT NOT NULL,
    created_at_epoch INTEGER NOT NULL,
    started_at TEXT,
    started_at_epoch INTEGER,
    completed_at TEXT,
    completed_at_epoch INTEGER,

    -- Results
    result TEXT,  -- Final output/summary from the agent
    error TEXT,  -- Error message if failed
    turns_used INTEGER DEFAULT 0,
    cost_usd REAL,
    input_tokens INTEGER,  -- Input tokens used (from SDK ResultMessage)
    output_tokens INTEGER,  -- Output tokens generated (from SDK ResultMessage)

    -- Files modified (JSON arrays)
    files_created TEXT,  -- JSON array of file paths
    files_modified TEXT,  -- JSON array of file paths
    files_deleted TEXT,  -- JSON array of file paths

    -- Warnings - non-fatal issues during execution
    warnings TEXT,  -- JSON array of warning messages

    -- Configuration snapshot (for reproducibility)
    project_config TEXT,  -- JSON of project config at run time
    system_prompt_hash TEXT,  -- Hash of system prompt used

    -- Machine tracking
    source_machine_id TEXT
);
```

**Key indexes:** `idx_agent_runs_agent`, `idx_agent_runs_status`, `idx_agent_runs_created`, `idx_agent_runs_agent_created`

## session_link_events

Analytics for user-driven session linking.

```sql
CREATE TABLE IF NOT EXISTS session_link_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- auto_linked, suggestion_accepted, suggestion_rejected, manual_linked, unlinked
    old_parent_id TEXT,
    new_parent_id TEXT,
    suggested_parent_id TEXT,
    suggestion_confidence REAL,
    link_reason TEXT,
    created_at TEXT NOT NULL,
    created_at_epoch INTEGER NOT NULL
);
```

**Key indexes:** `idx_session_link_events_session`, `idx_session_link_events_type`, `idx_session_link_events_created`

## session_relationships

Many-to-many semantic relationships between sessions.

```sql
CREATE TABLE IF NOT EXISTS session_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_a_id TEXT NOT NULL,
    session_b_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,  -- 'related'
    similarity_score REAL,            -- Vector similarity when created
    created_at TEXT NOT NULL,
    created_at_epoch INTEGER NOT NULL,
    created_by TEXT NOT NULL,         -- 'suggestion', 'manual'

    FOREIGN KEY (session_a_id) REFERENCES sessions(id),
    FOREIGN KEY (session_b_id) REFERENCES sessions(id),
    UNIQUE(session_a_id, session_b_id)  -- Prevent duplicates (a->b only, not b->a)
);
```

**Key indexes:** `idx_session_relationships_a`, `idx_session_relationships_b`, `idx_session_relationships_type`

## agent_schedules

Cron scheduling runtime state. Database is the sole source of truth.

```sql
CREATE TABLE IF NOT EXISTS agent_schedules (
    task_name TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 1,

    -- Schedule definition
    cron_expression TEXT,           -- Cron expression (e.g., '0 0 * * MON')
    description TEXT,               -- Human-readable schedule description
    trigger_type TEXT DEFAULT 'cron', -- 'cron' or 'manual' (future: 'git_commit', 'file_change')

    -- Runtime state
    last_run_at TEXT,
    last_run_at_epoch INTEGER,
    last_run_id TEXT,
    next_run_at TEXT,
    next_run_at_epoch INTEGER,

    -- Metadata
    created_at TEXT NOT NULL,
    created_at_epoch INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    updated_at_epoch INTEGER NOT NULL,

    -- Machine tracking (for backup/restore filtering)
    source_machine_id TEXT
);
```

**Key indexes:** `idx_agent_schedules_enabled_next`, `idx_agent_schedules_source_machine`

## resolution_events

Cross-machine resolution propagation. Each resolution action (resolve, supersede, reactivate) is recorded as a first-class, machine-owned entity that flows through the backup pipeline.

```sql
CREATE TABLE IF NOT EXISTS resolution_events (
    id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,        -- Target observation (soft FK, no constraint)
    action TEXT NOT NULL,                -- 'resolved' | 'superseded' | 'reactivated'
    resolved_by_session_id TEXT,
    superseded_by TEXT,                  -- New observation ID (for 'superseded')
    reason TEXT,
    created_at TEXT NOT NULL,
    created_at_epoch INTEGER NOT NULL,
    source_machine_id TEXT NOT NULL,
    content_hash TEXT,
    applied BOOLEAN DEFAULT TRUE         -- Locally-created = TRUE, imported = FALSE
);
```

**Key indexes:** `idx_resolution_events_observation`, `idx_resolution_events_source_machine`, `idx_resolution_events_applied`, `idx_resolution_events_epoch`, `idx_resolution_events_content_hash`

## Full-Text Search Tables (FTS5)

### memories_fts

Full-text search index over memory observations (FTS5).

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    observation,
    context,
    content='memory_observations',
    content_rowid='rowid'
);
```

### activities_fts

Full-text search index over activities (FTS5).

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS activities_fts USING fts5(
    tool_name,
    tool_input,
    tool_output_summary,
    file_path,
    error_message,
    content='activities',
    content_rowid='id'
);
```

FTS5 tables are kept in sync via triggers. Query with `MATCH` syntax:

```sql
-- Simple term search
WHERE activities_fts MATCH 'authentication'

-- Phrase search
WHERE memories_fts MATCH '"database connection"'

-- Boolean operators
WHERE activities_fts MATCH 'auth AND token'
WHERE memories_fts MATCH 'auth OR authentication'

-- Column-specific search
WHERE activities_fts MATCH 'file_path:auth.py'
```

## Related Files on Disk

| Resource | Path |
|----------|------|
| SQLite database | `.oak/ci/activities.db` |
| ChromaDB vector index | `.oak/ci/chroma/` |
| Daemon logs | `.oak/ci/daemon.log` |
| Hook logs | `.oak/ci/hooks.log` |
| User backups (git-tracked) | `oak/history/*.sql` |
| Agent configs (git-tracked) | `oak/agents/` |
| Shared port file (git-tracked) | `oak/daemon.port` |
