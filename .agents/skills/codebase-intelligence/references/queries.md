# Oak CI Database — Advanced Query Cookbook

Ready-to-use queries for common investigation tasks. All queries assume read-only access:

```bash
sqlite3 -readonly -header -column .oak/ci/activities.db "QUERY"
```

## Session Investigation

### Find sessions where a specific file was modified

```sql
SELECT DISTINCT s.id, s.title, s.agent,
       datetime(s.created_at_epoch, 'unixepoch', 'localtime') as started,
       s.prompt_count
FROM sessions s
JOIN activities a ON s.id = a.session_id
WHERE a.file_path LIKE '%/auth.py'
  AND a.tool_name IN ('Write', 'Edit')
ORDER BY s.created_at_epoch DESC
LIMIT 10;
```

### Session timeline (what happened in order)

```sql
SELECT a.tool_name,
       substr(a.file_path, -40) as file,
       a.success,
       substr(a.error_message, 1, 80) as error,
       datetime(a.timestamp_epoch, 'unixepoch', 'localtime') as time
FROM activities a
WHERE a.session_id = 'SESSION_ID'
ORDER BY a.timestamp_epoch;
```

### Sessions with errors

```sql
SELECT s.id, s.title, s.agent,
       count(a.id) as error_count,
       datetime(s.created_at_epoch, 'unixepoch', 'localtime') as started
FROM sessions s
JOIN activities a ON s.id = a.session_id
WHERE a.success = FALSE
GROUP BY s.id
ORDER BY error_count DESC
LIMIT 10;
```

### Session lineage (parent chain)

```sql
-- Follow parent_session_id chain to reconstruct session continuity
WITH RECURSIVE lineage AS (
    SELECT id, title, parent_session_id, parent_session_reason, 0 as depth
    FROM sessions WHERE id = 'SESSION_ID'
    UNION ALL
    SELECT s.id, s.title, s.parent_session_id, s.parent_session_reason, l.depth + 1
    FROM sessions s JOIN lineage l ON s.id = l.parent_session_id
    WHERE l.depth < 10
)
SELECT depth, id, title, parent_session_reason
FROM lineage ORDER BY depth;
```

## Activity Analysis

### Most used tools across all sessions

```sql
SELECT tool_name, count(*) as uses,
       sum(CASE WHEN success THEN 1 ELSE 0 END) as successes,
       sum(CASE WHEN NOT success THEN 1 ELSE 0 END) as failures,
       avg(duration_ms) as avg_ms
FROM activities
GROUP BY tool_name
ORDER BY uses DESC;
```

### Most edited files (recent 7 days)

```sql
SELECT file_path, count(*) as edits,
       count(DISTINCT session_id) as sessions
FROM activities
WHERE tool_name IN ('Write', 'Edit')
  AND file_path IS NOT NULL
  AND timestamp_epoch > unixepoch() - 7*86400
GROUP BY file_path
ORDER BY edits DESC
LIMIT 20;
```

### Failed commands with error messages

```sql
SELECT tool_name,
       substr(json_extract(tool_input, '$.command'), 1, 80) as command,
       substr(error_message, 1, 120) as error,
       datetime(timestamp_epoch, 'unixepoch', 'localtime') as time
FROM activities
WHERE success = FALSE AND tool_name = 'Bash'
ORDER BY timestamp_epoch DESC
LIMIT 20;
```

### Activity count by day

```sql
SELECT date(timestamp_epoch, 'unixepoch', 'localtime') as day,
       count(*) as activities,
       count(DISTINCT session_id) as sessions
FROM activities
GROUP BY day
ORDER BY day DESC
LIMIT 14;
```

## Memory Queries

### All gotchas (things to watch out for)

```sql
SELECT observation, context, file_path,
       datetime(created_at_epoch, 'unixepoch', 'localtime') as learned
FROM memory_observations
WHERE memory_type = 'gotcha'
ORDER BY created_at_epoch DESC;
```

### Decisions with rationale

```sql
SELECT observation, context,
       datetime(created_at_epoch, 'unixepoch', 'localtime') as decided
FROM memory_observations
WHERE memory_type = 'decision'
ORDER BY created_at_epoch DESC;
```

### Memories about a specific file or topic

```sql
SELECT memory_type, observation, context
FROM memory_observations
WHERE context LIKE '%auth%'
   OR observation LIKE '%auth%'
   OR file_path LIKE '%auth%'
ORDER BY created_at_epoch DESC
LIMIT 20;
```

### Full-text search on memories

```sql
SELECT m.memory_type, m.observation, m.context,
       datetime(m.created_at_epoch, 'unixepoch', 'localtime') as created
FROM memory_observations m
JOIN memories_fts fts ON m.rowid = fts.rowid
WHERE memories_fts MATCH 'database migration'
ORDER BY rank
LIMIT 10;
```

### High-importance memories

```sql
SELECT memory_type, observation, importance, context
FROM memory_observations
WHERE importance >= 7
ORDER BY importance DESC, created_at_epoch DESC;
```

### Memory statistics

```sql
SELECT memory_type, count(*) as count,
       min(datetime(created_at_epoch, 'unixepoch', 'localtime')) as oldest,
       max(datetime(created_at_epoch, 'unixepoch', 'localtime')) as newest
FROM memory_observations
GROUP BY memory_type
ORDER BY count DESC;
```

## Agent Run Queries

### Recent agent runs with costs

```sql
SELECT agent_name, substr(task, 1, 60) as task,
       status, turns_used,
       printf('$%.4f', cost_usd) as cost,
       input_tokens, output_tokens,
       datetime(created_at_epoch, 'unixepoch', 'localtime') as started
FROM agent_runs
ORDER BY created_at_epoch DESC
LIMIT 20;
```

### Total cost by agent

```sql
SELECT agent_name,
       count(*) as runs,
       sum(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
       sum(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
       printf('$%.4f', sum(cost_usd)) as total_cost,
       printf('$%.4f', avg(cost_usd)) as avg_cost
FROM agent_runs
GROUP BY agent_name
ORDER BY sum(cost_usd) DESC;
```

### Failed agent runs with errors

```sql
SELECT agent_name, substr(task, 1, 80) as task,
       substr(error, 1, 120) as error,
       datetime(created_at_epoch, 'unixepoch', 'localtime') as failed_at
FROM agent_runs
WHERE status = 'failed'
ORDER BY created_at_epoch DESC
LIMIT 10;
```

### Files modified by agent runs

```sql
SELECT agent_name, task,
       json_extract(files_created, '$') as created,
       json_extract(files_modified, '$') as modified,
       json_extract(files_deleted, '$') as deleted
FROM agent_runs
WHERE status = 'completed'
  AND (files_created IS NOT NULL
       OR files_modified IS NOT NULL
       OR files_deleted IS NOT NULL)
ORDER BY created_at_epoch DESC
LIMIT 10;
```

## Schedule Queries

### All schedules with status

```sql
SELECT task_name, enabled,
       cron_expression, description,
       datetime(last_run_at_epoch, 'unixepoch', 'localtime') as last_run,
       datetime(next_run_at_epoch, 'unixepoch', 'localtime') as next_run
FROM agent_schedules
ORDER BY next_run_at_epoch;
```

### Overdue schedules

```sql
SELECT task_name, cron_expression,
       datetime(next_run_at_epoch, 'unixepoch', 'localtime') as overdue_since
FROM agent_schedules
WHERE enabled = 1
  AND next_run_at_epoch < unixepoch()
ORDER BY next_run_at_epoch;
```

## Cross-Table Joins

### What prompted a specific memory (trace back to user prompt)

```sql
SELECT m.memory_type, m.observation,
       pb.user_prompt,
       s.title as session_title, s.agent
FROM memory_observations m
JOIN prompt_batches pb ON m.prompt_batch_id = pb.id
JOIN sessions s ON m.session_id = s.id
WHERE m.observation LIKE '%search_term%'
LIMIT 10;
```

### Session summary with key stats

```sql
SELECT s.id, s.agent, s.title, s.status,
       s.prompt_count, s.tool_count,
       datetime(s.created_at_epoch, 'unixepoch', 'localtime') as started,
       datetime(s.ended_at, 'localtime') as ended,
       count(DISTINCT a.file_path) as unique_files,
       sum(CASE WHEN a.success = FALSE THEN 1 ELSE 0 END) as errors,
       (SELECT count(*) FROM memory_observations m WHERE m.session_id = s.id) as memories_created
FROM sessions s
LEFT JOIN activities a ON s.id = a.session_id
WHERE s.id = 'SESSION_ID'
GROUP BY s.id;
```

### What happened today

```sql
SELECT s.agent, s.title,
       s.prompt_count || ' prompts, ' || s.tool_count || ' tools' as activity,
       datetime(s.created_at_epoch, 'unixepoch', 'localtime') as started,
       s.status
FROM sessions s
WHERE date(s.created_at_epoch, 'unixepoch', 'localtime') = date('now', 'localtime')
ORDER BY s.created_at_epoch DESC;
```

## JSON Column Queries

Several columns store JSON. Use `json_extract()` to query them:

```sql
-- Extract command from Bash tool_input
SELECT json_extract(tool_input, '$.command') as command
FROM activities
WHERE tool_name = 'Bash' AND tool_input IS NOT NULL
LIMIT 10;

-- Extract file_path from Read/Write tool_input
SELECT json_extract(tool_input, '$.file_path') as file
FROM activities
WHERE tool_name = 'Read' AND tool_input IS NOT NULL
LIMIT 10;

-- Count files created by an agent run
SELECT agent_name, task,
       json_array_length(files_created) as files_created_count,
       json_array_length(files_modified) as files_modified_count
FROM agent_runs
WHERE files_created IS NOT NULL OR files_modified IS NOT NULL;
```

## Database Health

### Table sizes

```sql
SELECT 'sessions' as tbl, count(*) as rows FROM sessions
UNION ALL SELECT 'prompt_batches', count(*) FROM prompt_batches
UNION ALL SELECT 'activities', count(*) FROM activities
UNION ALL SELECT 'memory_observations', count(*) FROM memory_observations
UNION ALL SELECT 'agent_runs', count(*) FROM agent_runs
UNION ALL SELECT 'agent_schedules', count(*) FROM agent_schedules;
```

### Database file size

```bash
du -h .oak/ci/activities.db
```

### Unprocessed items (processing backlog)

```sql
SELECT 'sessions' as type, count(*) as unprocessed
FROM sessions WHERE processed = FALSE AND status = 'completed'
UNION ALL
SELECT 'batches', count(*) FROM prompt_batches WHERE processed = FALSE AND status = 'completed'
UNION ALL
SELECT 'memories (unembedded)', count(*) FROM memory_observations WHERE embedded = FALSE;
```
