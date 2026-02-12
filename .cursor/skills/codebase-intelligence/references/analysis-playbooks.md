# Analysis Playbooks

Structured multi-query workflows for analyzing CI data. Each playbook is a sequence of queries that build on each other to answer a specific question.

These playbooks can be used manually via the `codebase-intelligence` skill, or automated via the analysis agent (`oak ci agent run <task-name>`).

## Playbook 1: Usage & Cost Analysis

**Goal**: Understand CI spend and identify optimization opportunities.

### Step 1: Overall Cost Summary

```sql
SELECT agent_name,
       count(*) as total_runs,
       sum(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
       sum(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
       printf('$%.4f', sum(cost_usd)) as total_cost,
       printf('$%.4f', avg(cost_usd)) as avg_cost,
       sum(input_tokens) as total_input_tokens,
       sum(output_tokens) as total_output_tokens
FROM agent_runs
GROUP BY agent_name
ORDER BY total_cost DESC;
```

### Step 2: Weekly Cost Trend

```sql
SELECT strftime('%Y-W%W', datetime(created_at_epoch, 'unixepoch')) as week,
       count(*) as runs,
       printf('$%.4f', sum(cost_usd)) as cost,
       sum(input_tokens) as input_tokens,
       sum(output_tokens) as output_tokens
FROM agent_runs
WHERE created_at_epoch > strftime('%s', 'now', '-56 days')
GROUP BY week
ORDER BY week;
```

### Step 3: Most Expensive Runs

```sql
SELECT agent_name, substr(task, 1, 80) as task_preview,
       status, turns_used,
       printf('$%.4f', cost_usd) as cost,
       datetime(created_at_epoch, 'unixepoch', 'localtime') as created
FROM agent_runs
WHERE cost_usd IS NOT NULL
ORDER BY cost_usd DESC
LIMIT 10;
```

### Interpretation

- **Good**: Costs are stable or decreasing week-over-week
- **Watch**: Cost spikes correlating with failed runs (wasted spend)
- **Action**: If a specific agent has high avg_cost, check if its max_turns is too high

---

## Playbook 2: Productivity Analysis

**Goal**: Understand coding session quality and identify improvement patterns.

### Step 1: Session Quality Distribution

```sql
SELECT status,
       count(*) as count,
       avg(prompt_count) as avg_prompts,
       avg(tool_count) as avg_tools,
       avg(CASE WHEN summary IS NOT NULL THEN 1.0 ELSE 0.0 END) as summary_rate
FROM sessions
GROUP BY status;
```

### Step 2: Activity Classification Breakdown

```sql
SELECT classification,
       count(*) as count,
       avg(activity_count) as avg_activities,
       avg(length(user_prompt)) as avg_prompt_length
FROM prompt_batches
WHERE classification IS NOT NULL
GROUP BY classification
ORDER BY count DESC;
```

### Step 3: Error Rate by Tool

```sql
SELECT tool_name,
       count(*) as total,
       sum(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors,
       printf('%.1f%%', 100.0 * sum(CASE WHEN success = 0 THEN 1 ELSE 0 END) / count(*)) as error_rate
FROM activities
GROUP BY tool_name
HAVING count(*) > 10
ORDER BY errors DESC;
```

### Step 4: Productivity by Time of Day

```sql
SELECT strftime('%H', datetime(created_at_epoch, 'unixepoch', 'localtime')) as hour,
       count(DISTINCT session_id) as sessions,
       count(*) as activities
FROM activities
GROUP BY hour
ORDER BY hour;
```

### Interpretation

- **Good**: High completion rate (>80%), low error rates (<5%)
- **Watch**: Many sessions with 0 summaries (sessions may be too short to be useful)
- **Action**: If error_rate is high for a specific tool, investigate common failure patterns

---

## Playbook 3: Codebase Activity

**Goal**: Identify hotspots and understand where development effort is concentrated.

### Step 1: File Hotspots (Edits)

```sql
SELECT file_path, count(*) as edit_count
FROM activities
WHERE tool_name IN ('Write', 'Edit')
  AND file_path IS NOT NULL
GROUP BY file_path
ORDER BY edit_count DESC
LIMIT 20;
```

### Step 2: Directory-Level Activity

```sql
SELECT
  CASE
    WHEN instr(file_path, '/') > 0
    THEN substr(file_path, 1, instr(file_path, '/') - 1)
    ELSE file_path
  END as top_dir,
  count(*) as activity_count,
  count(DISTINCT file_path) as unique_files
FROM activities
WHERE file_path IS NOT NULL
GROUP BY top_dir
ORDER BY activity_count DESC
LIMIT 15;
```

### Step 3: Memory Growth Over Time

```sql
SELECT strftime('%Y-%m', datetime(created_at_epoch, 'unixepoch')) as month,
       memory_type,
       count(*) as new_memories
FROM memory_observations
GROUP BY month, memory_type
ORDER BY month DESC, new_memories DESC;
```

### Interpretation

- **Good**: Activity spread across multiple directories (not concentrated in one area)
- **Watch**: Files edited >50 times may need refactoring or splitting
- **Action**: Gotcha accumulation in a directory suggests it needs documentation

---

## Playbook 4: Prompt Quality

**Goal**: Understand how prompt quality affects session outcomes.

### Step 1: Prompt Length Distribution

```sql
SELECT
  CASE
    WHEN length(user_prompt) < 20 THEN '1. tiny (<20)'
    WHEN length(user_prompt) < 50 THEN '2. short (20-50)'
    WHEN length(user_prompt) < 200 THEN '3. medium (50-200)'
    WHEN length(user_prompt) < 500 THEN '4. long (200-500)'
    ELSE '5. very long (500+)'
  END as length_bucket,
  count(*) as count,
  avg(activity_count) as avg_activities
FROM prompt_batches
WHERE user_prompt IS NOT NULL AND user_prompt != ''
GROUP BY length_bucket
ORDER BY length_bucket;
```

### Step 2: High-Quality Prompt Examples

```sql
SELECT substr(user_prompt, 1, 200) as prompt_preview,
       classification,
       activity_count
FROM prompt_batches
WHERE user_prompt IS NOT NULL
  AND activity_count > 5
  AND classification IS NOT NULL
ORDER BY activity_count DESC
LIMIT 10;
```

### Interpretation

- **Good**: Most prompts in the "medium" to "long" range (50-500 chars)
- **Watch**: Many "tiny" prompts suggest vague instructions
- **Action**: Use exemplary prompts as templates for future work

---

## Automated Analysis

These playbooks can be run automatically via the analysis agent:

```bash
oak ci agent run usage-report          # Playbook 1
oak ci agent run productivity-report   # Playbook 2
oak ci agent run codebase-activity-report  # Playbook 3
oak ci agent run prompt-analysis       # Playbook 4
```

Reports are written to `oak/insights/` and can be committed to git for team visibility.
