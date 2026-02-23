# The Context Engineering Framework

Context engineering is designing the complete information environment a model receives at inference time. Four core strategies — Write, Select, Compress, Isolate — ensure the model has the right information, in the right form, at the right moment.

## The Core Insight

Context engineering is not prompt engineering. A prompt is what you type. Context is *everything* the model sees: system prompt + conversation history + tool definitions + tool results + retrieved documents + injected memories + file contents + structured metadata.

A well-engineered prompt inside poorly-engineered context will underperform. A mediocre prompt inside well-engineered context will often succeed. **The context is the product.**

The question shifts from "What should I tell the model?" to "What should the model see, and when should it see it?"

---

## Strategy 1: Write — Craft the Persistent Context

The system prompt persists across every turn, anchoring behavior, tone, and decision-making. It is the highest-leverage piece of context.

### The Altitude Scale

Altitude is the level of abstraction at which you write instructions. Most system prompts fail because they target the wrong altitude.

| Level | Example | Problem |
|---|---|---|
| Too High (30,000 ft) | "Be a helpful coding assistant" | No actionable guidance |
| Too Low (ground level) | "Always use 4-space indentation, prefer f-strings over .format(), use pathlib instead of os.path" | Brittle, doesn't generalize, model may ignore the list |
| Right Altitude (10,000 ft) | "Follow the project's existing code style. When uncertain, match the patterns in nearby files." | Principled, adaptable, scales to new situations |

Right-altitude examples across domains:

| Domain | Too High | Right Altitude |
|---|---|---|
| Code review | "Review code carefully" | "Identify bugs that would cause runtime failures, focusing on edge cases the author likely didn't test" |
| Customer support | "Help the customer" | "Acknowledge the customer's specific situation before moving to resolution. Gather account info early." |
| Data analysis | "Analyze this data" | "Check for quality issues first (missing values, type mismatches), then answer using appropriate aggregations" |
| Writing | "Help me write" | "Match the style of the user's existing text. Preserve their voice; improve clarity without imposing a formula." |

**The altitude test:** If your instruction would still be correct after the codebase or domain changes significantly, it is at the right altitude. If it would break, it is too low. If it provides no guidance for concrete decisions, it is too high.

### Canonical Examples in System Prompts

Instructions tell the model what to do. Examples *show* it. When the two conflict, examples usually win — models pattern-match on demonstrations more reliably than they follow abstract rules.

Include 2-3 gold-standard input/output pairs directly in the system prompt:

```
You are a code review assistant.

## Example Review

**Input code:**
def get_user(id):
    user = db.query(f"SELECT * FROM users WHERE id = {id}")
    return user[0]

**Your review:**
1. **SQL injection** (critical): Use parameterized queries:
   `db.query("SELECT * FROM users WHERE id = ?", [id])`
2. **Unhandled empty result** (bug): `user[0]` raises IndexError
   if no user matches. Check the result length first.
3. **Naming**: `id` shadows the built-in. Use `user_id`.

Apply this structure: prioritize by severity, explain the why, show the fix.
```

This single example establishes the review structure, severity ordering, inline-fix convention, and explanatory tone — all by demonstration.

### System Prompt as Constitution

A system prompt can function as a constitution: a governing document establishing principles, boundaries, and quality standards for an entire project.

> Cross-reference: The `/project-governance` skill creates constitutions that serve exactly this purpose — the Write strategy applied at project scale.

---

## Strategy 2: Select — Choose What Enters the Context

Every token in the context window competes for the model's attention. Select ensures only high-value, relevant information occupies that space.

### Minimal Viable Toolsets

Fewer, well-described tools lead to better tool selection. Tool sprawl causes selection errors and wastes tokens.

| Quality | Tool Description | Issue |
|---|---|---|
| Bad | "search: A tool for searching" | What does it search? What format? |
| Bad | "find_and_replace_in_files: Searches and optionally replaces, supports regex, globs, recursive traversal" | Two tools in one |
| Good | "grep_codebase: Search file contents with regex. Returns matching lines with file paths and line numbers." | Clear scope, output, use case |
| Good | "edit_file: Replace a specific string in a file. old_string must appear exactly once." | Precise contract |

**Principles:** single responsibility per tool, verb-based names, remove overlapping tools, conditionally load rarely-used tools.

### Retrieval Quality

RAG is the Select strategy operationalized. Quality matters far more than quantity.

**Precision over recall.** Injecting 20 vaguely-related documents is worse than 3 highly relevant ones. Irrelevant results actively mislead by introducing noise that competes with signal.

Key practices: re-rank after initial retrieval, limit to top-K (typically 3-5), chunk at semantic boundaries (sections, functions) not fixed token counts, test retrieval quality independently.

### Dynamic Context Selection

Route queries to different context sources based on what the query needs:

```
"I was charged twice"       -> billing KB + account lookup tool
"App crashes on login"      -> troubleshooting docs + error log tool
"How do I export my data?"  -> product docs + feature guide
"I want to cancel"          -> retention playbook + account status tool
```

Implementation patterns: classify-then-select (two-step), model self-selection via tool descriptions, metadata pre-filtering, or combinations of these.

---

## Strategy 3: Compress — Reduce Without Losing

Conversations grow. Tool results are verbose. Left unchecked, context fills and performance degrades. Compress fights context bloat while preserving essential information.

### Compaction Techniques

| Technique | How It Works | When to Use |
|---|---|---|
| Summarization | LLM summarizes older conversation history | Long conversations approaching limits |
| Note-taking scratchpad | Agent writes key findings to a persistent scratchpad | Complex research tasks |
| Sub-agent delegation | Spawn focused sub-agents with narrow context; receive only conclusions | Multi-domain tasks |
| Tool result clearing | Replace verbose tool output with summary after processing | Large tool responses |
| Recursive summarization | Summarize existing summaries | Very long sessions |

### The Two-Phase Compression Approach

A production pattern combining techniques:

**Phase 1 — Sliding window:** Keep the last N messages verbatim (active working context).

**Phase 2 — Structured summarization:** Compress older messages into: key facts established, decisions made with rationale, open questions, constraints discovered.

This preserves detail where it matters most (recent context) while retaining essentials from earlier. Maintaining a "facts learned" scratchpad alongside the conversation enhances this — the scratchpad becomes a compressed representation of the entire session's knowledge.

### Token Budget Analysis

Budget tokens deliberately rather than filling the window opportunistically.

```
Available context = Window size - system prompt - tool descriptions
                  - conversation history - retrieved docs - response budget
```

| Component | 8K | 32K | 128K | 200K |
|---|---|---|---|---|
| System prompt | 1,000 (12%) | 2,000 (6%) | 4,000 (3%) | 5,000 (2.5%) |
| Tool descriptions | 500 (6%) | 1,500 (5%) | 3,000 (2%) | 4,000 (2%) |
| Conversation | 2,500 (31%) | 12,000 (37%) | 50,000 (39%) | 80,000 (40%) |
| Retrieved docs | 1,500 (19%) | 8,000 (25%) | 35,000 (27%) | 55,000 (27.5%) |
| **Response budget** | **2,500 (31%)** | **8,500 (27%)** | **36,000 (28%)** | **56,000 (28%)** |

**Rules:** Reserve 20-30% for response (truncation degrades quality). Compress proactively, not reactively. System prompt and tool descriptions are fixed costs; conversation and retrieved docs are where compression pays off.

---

## Strategy 4: Isolate — Move Information Out of Main Context

The most powerful strategy for scaling. Move information to external storage, retrieve just-in-time. The context window becomes working memory, not permanent storage.

### Just-in-Time Retrieval

Don't load information until the model needs it.

**Anti-pattern — eager loading:**
```
System prompt: full API docs (15K tokens) + style guide (3K)
  + project rules (5K) + DB schema (4K) = 27K tokens before the user speaks
```

**Pattern — just-in-time:**
```
System prompt: role (200 tokens) + principles (300 tokens)
  + tools: search_docs(), get_schema(), check_style() = 800 tokens
  → detailed info retrieved on demand
```

97% fewer system prompt tokens, access to the same (or more) information.

### Progressive Disclosure

Structure information in layers:

- **Layer 1 — Overview** (always in context): project structure, directory summaries
- **Layer 2 — Details** (retrieved on demand): file listings with descriptions, section contents
- **Layer 3 — Raw data** (retrieved for specific work): full file contents, complete records

Each layer provides enough information to decide whether to go deeper — like navigating from a map to a neighborhood to a specific building.

### Hybrid Context Loading

- **Static context** (every turn): system prompt, core tools, persistent memory
- **Dynamic context** (query-dependent): retrieved documents, relevant code files, user info
- **Ephemeral context** (use once, then clear): raw tool results, intermediate search results, verbose API responses

Most context is ephemeral — needed for one step, then dead weight. Actively managing context lifecycle (load, use, summarize, clear) keeps the window focused.

---

## Combining Strategies

The four strategies work together. Decision framework:

```
Is the information needed on EVERY turn?
+-- Yes -> WRITE it into the system prompt
|   +-- System prompt too long?
|       +-- Yes -> Raise ALTITUDE or move specifics to retrieval
|       +-- No  -> Keep it
+-- No -> Needed on SOME turns?
    +-- Yes -> Can you predict WHEN?
    |   +-- Yes -> SELECT (pre-filter by query type or metadata)
    |   +-- No  -> ISOLATE (let model retrieve via tools)
    +-- Rarely -> COMPRESS or remove entirely
```

**Combinations in practice:**

| Scenario | Strategies |
|---|---|
| Long coding session | Write (project principles) + Isolate (file contents via tools) + Compress (summarize old turns) |
| RAG-powered Q&A | Write (role + format) + Select (top-K docs) + Compress (multi-retrieval summaries) |
| Research agent | Write (methodology) + Isolate (search tools) + Compress (scratchpad) + Select (curate findings) |
| Customer support | Write (tone + policy) + Select (route to relevant KB) + Isolate (account lookup) |

---

## Measuring Context Quality

| Signal | Likely Cause | Action |
|---|---|---|
| Model ignores instructions | System prompt too long or low altitude | Raise altitude, compress, move details to retrieval |
| Wrong tool selected | Ambiguous or overlapping descriptions | Rewrite descriptions, reduce tool count |
| Hallucinated information | Missing context | Add retrieval, improve selection |
| Repetitive responses | Context rot (stale/redundant info) | Compress history, deduplicate |
| Slow responses | Context too large | Compress, isolate verbose data |
| Contradictory behavior | Conflicting instructions | Audit for contradictions, set precedence |
| Degraded quality over time | Window filling with low-value history | Sliding-window compression, scratchpad |

### Quick Diagnostic Checklist

When agent performance drops, check in order:

1. **System prompt over 3,000 tokens?** Raise altitude or isolate details.
2. **More than 15 tools defined?** Reduce, merge, or conditionally load.
3. **Conversation history over 50% of window?** Compress.
4. **Retrieved documents relevant?** Spot-check what was actually injected.
5. **Response budget sufficient?** Ensure 20-30% of window remains for output.
6. **Contradictions present?** Search full context for conflicting instructions.

Context engineering is iterative. Measure signals, diagnose root causes, apply strategies, measure again.
