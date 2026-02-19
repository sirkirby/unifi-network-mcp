---
name: context-engineering
description: >-
  Design effective prompts and optimize context for AI models and agents.
  Covers prompt engineering foundations (clarity, examples, chain of thought,
  XML structure), the four context engineering strategies (Write, Select,
  Compress, Isolate), agent memory and session patterns, and before/after
  examples showing measurable improvement. Use when writing system prompts,
  designing agent workflows, optimizing context windows, building prompt
  templates, structuring few-shot examples, reducing context rot, or
  improving AI output quality.
allowed-tools: Read
user-invocable: true
---

# Context Engineering

Design effective prompts and optimize the full context window for AI models and agents to produce consistently high-quality output.

## Quick Start

### Recipe 1: Improve a vague prompt

**Before:** `Review this code and give feedback.`

**After:**
```xml
<task>Review the provided code for correctness, performance, and maintainability.</task>
<output-format>
For each issue: file/line, severity (critical|warning|suggestion), problem (one sentence), fix (concrete code change).
If no issues, state "No issues found" and list one strength.
</output-format>
<code>{{code_to_review}}</code>
```

**Why it works:** Specifies evaluation criteria, defines output structure, separates instructions from data with XML tags.

### Recipe 2: Design a system prompt

Use the **altitude concept** -- not so high it's useless ("be helpful"), not so low it's brittle ("always use 4 spaces").

1. **Define the role** in one sentence: what the agent IS and IS NOT
2. **Set altitude** -- right level: "Follow the project's existing naming conventions. When none exists, prefer descriptive names over short ones."
3. **Add constraints** using RFC 2119 language (MUST, SHOULD, MAY)
4. **Include 1-2 canonical examples** of ideal output
5. **Define non-goals** to prevent scope creep

See `references/system-prompt-design.md` for full anatomy and templates.

### Recipe 3: Structure agent context with the 4 strategies

When your agent produces inconsistent or degraded output, apply the four strategies:

| Strategy | Action | Example |
|----------|--------|---------|
| **Write** | Craft persistent instructions | System prompt with altitude-appropriate rules |
| **Select** | Choose what enters context | Use `oak_search` to retrieve only relevant code |
| **Compress** | Reduce tokens, preserve signal | Summarize prior conversation turns, delegate to sub-agents |
| **Isolate** | Move information out of context | Store reference docs externally, load just-in-time |

```
1. Start with Write: define a clear system prompt
2. Apply Select: give the agent only the tools and context it needs
3. Add Compress: implement compaction for long sessions
4. Use Isolate: move large reference material behind retrieval
```

See `references/context-engineering-framework.md` for the full framework.

## The Evolution: Prompt to Context Engineering

| Level | Focus | Scope | Key Insight |
|-------|-------|-------|-------------|
| **Basic Prompting** | The question you type | Single user message | Clarity matters |
| **Prompt Engineering** | Crafting effective prompts | Prompt + examples + structure | Technique amplifies quality |
| **Context Engineering** | Everything the model sees | System prompt + tools + memory + retrieved docs + conversation history | The context window IS the product |

Context engineering manages **everything** the model sees -- system prompt, tools, retrieved documents, conversation history, and memory. Every token either helps or hurts. The entire context window is a design surface.

## Prompt Engineering Foundations

These eight techniques form the foundation. Master them before moving to context engineering.

| # | Technique | When to Use | Key Rule |
|---|-----------|-------------|----------|
| 1 | **Be clear and direct** | Always -- this is the baseline | State exactly what you want; remove ambiguity |
| 2 | **Use examples (multishot)** | Output format matters, or the task is nuanced | Show 2-3 examples of ideal input/output pairs |
| 3 | **Chain of thought** | Reasoning, math, multi-step logic | Ask the model to think step-by-step before answering |
| 4 | **Use XML tags** | Separating instructions from data, structured output | Wrap distinct sections in descriptive tags like `<context>`, `<instructions>` |
| 5 | **Give Claude a role** | Specialized tasks needing domain expertise | Set the role in the system prompt, not the user message |
| 6 | **Chain complex prompts** | Multi-step workflows, pipelines | Break into sequential steps; output of step N feeds step N+1 |
| 7 | **Long context tips** | Large documents, many files | Put key instructions at top and bottom; use XML to delineate sections |
| 8 | **Extended thinking** | Complex reasoning, planning, self-correction | Enable thinking to let the model plan before responding |

**Combining techniques:** Most effective prompts use 3-5 techniques together. A code review prompt might combine clarity (#1), XML structure (#4), role (#5), and examples (#2).

See `references/prompt-foundations.md` for detailed explanations, examples, and anti-patterns for each technique.

## Context Engineering Framework (4 Strategies)

### Write: Craft the persistent context

The Write strategy covers everything you author in advance: system prompts, tool descriptions, and instruction files. This is the context you control completely.

**The altitude concept** is the most important principle. Your instructions need to be at the right level of abstraction:

| Altitude | Example | Problem |
|----------|---------|---------|
| Too high | "Write clean code" | No actionable guidance -- the agent fills in its own interpretation |
| Too low | "Always use `Array.prototype.reduce` for aggregation" | Brittle -- breaks when context changes, prevents good judgment |
| Right | "Prefer declarative patterns over imperative loops. Choose the array method that most clearly expresses intent." | Guides without constraining |

**Canonical examples** are powerful -- a single well-chosen example communicates more than paragraphs of rules:

```xml
<system>
You generate API documentation from source code.
<example>
<input>
def calculate_tax(amount: float, rate: float = 0.08) -> float:
    """Calculate sales tax for a given amount."""
    return round(amount * rate, 2)
</input>
<output>
### `calculate_tax(amount, rate=0.08)`
Calculate sales tax for a given amount.
- `amount` (float): The pre-tax amount
- `rate` (float, optional): Tax rate as decimal. Default: 0.08
- **Returns:** float -- Tax amount, rounded to 2 decimal places.
</output>
</example>
</system>
```

**Project-level Write strategy:** Use the `/project-governance` skill to create a constitution (`oak/constitution.md`) and agent instruction files. Your constitution IS your project-level system prompt. The altitude concept applies directly: "write good code" is useless; "copy `src/features/auth/service.py` for new services" is actionable.

See `references/context-engineering-framework.md` for the full Write strategy guide.

### Select: Choose what enters the context window

Select the right information to include; keep everything else out.

**For tools:** Provide the **minimal viable toolset** (unused tools cause confusion), write **unambiguous descriptions** (the model uses these to decide when to call), and prefer **specific tools** over general-purpose ones.

**For retrieved context:** Quality over quantity (3 relevant snippets beat 20 loose ones), recency matters, and always include source attribution (file paths, line numbers).

**Anti-pattern -- context stuffing:**
```
# Bad: dumping everything "just in case"
context = all_docs + all_code + all_history + all_memories
# Good: selecting what's relevant
context = search_relevant_code(task) + get_recent_decisions(task)
```

### Compress: Reduce tokens while preserving information

Compress rather than truncate. Preserve signal while reducing cost.

**Strategies:** Conversation summarization (replace old turns with structured summary), note-taking scratchpad (running notes vs. re-reading history), sub-agent delegation (offload research, return only findings), and tool result cleanup (extract then clear verbose output).

**When to compress:** Context exceeds 50% capacity, agent forgets earlier instructions, responses repeat or lose focus, or tool results contain mostly irrelevant data.

### Isolate: Move information out of the main context

Store information externally and load just-in-time, rather than keeping it in context at all times.

**Patterns:** Just-in-time retrieval (load docs only when needed), progressive disclosure (summary first, details on demand), hybrid context loading (rules in system prompt, reference material behind search), and memory-as-a-tool (store externally, retrieve on demand).

**Progressive disclosure example:** Agent sees summary ("Auth uses JWT") -> needs details (retrieves auth docs) -> needs code (retrieves auth service file). Each step loads only what's needed.

See `references/context-engineering-framework.md` for the complete framework with extended examples.

## Agent Context Patterns

### Sessions vs memory

| Concept | Scope | Lifetime | Purpose |
|---------|-------|----------|---------|
| **Session** | Single conversation | Ephemeral | Working memory for the current task |
| **Memory** | Cross-session | Persistent | Accumulated knowledge and learnings |

The common mistake: keeping everything in the session instead of writing important things to persistent memory.

### Context rot

Output quality degrades as conversations grow longer due to: **dilution** (instructions buried under tool results), **position bias** (models attend more to beginning/end, losing middle), **contradiction accumulation**, and **working memory overflow**.

**Signs:** Agent forgets earlier constraints, responses become generic/repetitive, re-asks answered questions, quality drops vs. early turns.

**Mitigation:** Apply Compress (summarize and compact) and Isolate (move reference material behind retrieval). For long-running agents, implement periodic compaction checkpoints.

### Memory types

| Type | What It Stores | Example | OAK CI Tool |
|------|---------------|---------|-------------|
| **Episodic** | What happened | "Refactored auth module in session #42" | `oak_search --type memory` |
| **Procedural** | How to do things | "To add a feature, copy the strategic_planning exemplar" | `oak_remember` with type `discovery` |
| **Semantic** | Facts and concepts | "The API uses JWT tokens with 1-hour expiry" | `oak_remember` with type `discovery` |

### Memory-as-a-tool pattern

Store externally, retrieve on demand -- instead of accumulating in context:

```
1. Discover → oak_remember("auth tokens expire after 1 hour", type="discovery")
2. Later   → oak_search("auth token expiry") retrieves just-in-time
3. Stale   → oak_resolve_memory(id, status="resolved") cleans up
```

This implements both Compress (don't hold everything) and Isolate (retrieve when needed).

### Compaction strategies

| Strategy | How It Works | Best For |
|----------|-------------|----------|
| **Last-N** | Keep only the last N conversation turns | Simple, predictable token budget |
| **Recursive summarization** | Summarize old turns, keep recent ones verbatim | Long conversations with important early context |
| **Hybrid** | Summarize + keep pinned messages (system prompt, key decisions) | Complex agents with critical persistent instructions |

See `references/agent-context-patterns.md` and `references/memory-and-sessions.md` for detailed patterns and implementation guidance.

## CI Integration: Context Engineering in Practice

OAK's Codebase Intelligence tools directly implement the four context engineering strategies:

| Strategy | CI Tool | What It Does |
|----------|---------|--------------|
| **Write** | `oak_remember` / `oak ci remember` | Persist learnings, decisions, and gotchas to long-term memory |
| **Select** | `oak_search` / `oak ci search` | Retrieve only the code and memories relevant to the current task |
| **Isolate** | `oak_context` / `oak ci context` | Assemble just-in-time context for a specific task, pulling from code and memory |
| **Consolidate** | `oak_resolve_memory` / `oak ci resolve` | Resolve stale observations to prevent context rot in the memory store |

### Example workflow

```bash
# WRITE: Store a discovery for future sessions
oak ci remember "Payment service retries 3x with exponential backoff" --type discovery
# SELECT: Find relevant code for a task
oak ci search "payment retry logic" --type code -n 5
# ISOLATE: Assemble just-in-time context
oak ci context "fix payment timeout bug" -f src/services/payment.py
# CONSOLIDATE: Clean up after fixing
oak ci resolve <memory-id>
```

## Before/After Gallery

### Vague prompt to structured prompt

**Before:** `Write tests for the user service.`

**After:**
```xml
<task>Write unit tests for UserService: create_user, get_user_by_email, delete_user.</task>
<constraints>
- pytest with fixtures for setup/teardown
- Test success and error paths for each method
- Mock external API calls (email verification)
- Descriptive test names: test_create_user_with_duplicate_email_raises_conflict
</constraints>
```

### Bloated system prompt to altitude-optimized

**Before** (micromanaging): "Always use f-strings. Always use pathlib. Always use type hints. Use black with line length 88. Use dataclasses for DTOs. Never use print()..."

**After** (right altitude):
```xml
<role>You are a Python developer working in this project.</role>
<principles>
- Follow existing patterns. Find the closest implementation and mirror its style.
- Prefer modern Python (3.10+). When in doubt, check what the codebase uses.
- Write code that reads clearly without comments. Comment only non-obvious "why" decisions.
</principles>
<quality>Run `make check` before considering any change complete.</quality>
```

### Context-stuffed agent to compress + isolate

**Before:** 40,000 tokens (2K rules + 3K README + 8K tool descriptions + 12K API docs + 15K conversation = half irrelevant)

**After:** 8,000 tokens (800 altitude-optimized prompt + 1,200 for 5 relevant tools + 2,000 retrieved context + 4,000 compressed conversation = all relevant)

See `references/before-after-examples.md` for the full gallery with additional transformations.

## When to Use What

| Situation | Strategy | Key Technique | Reference |
|-----------|----------|---------------|-----------|
| Writing a new system prompt | Write | Altitude concept, canonical examples | `references/system-prompt-design.md` |
| Prompt gives inconsistent results | Foundations | Add examples, use XML structure | `references/prompt-foundations.md` |
| Agent losing track of goals | Compress | Conversation summarization, compaction | `references/context-engineering-framework.md` |
| Agent context window filling up | Isolate | Just-in-time retrieval, progressive disclosure | `references/agent-context-patterns.md` |
| Agent forgetting earlier decisions | Write + Compress | Pin critical context, summarize history | `references/memory-and-sessions.md` |
| Need to measure prompt quality | Evaluate | A/B testing, rubric scoring | `references/evaluation-and-testing.md` |
| Setting project-wide AI rules | Write | Constitution as system prompt | `/project-governance` skill |
| Agent repeating mistakes across sessions | Write | Memory-as-a-tool, `oak_remember` | `references/memory-and-sessions.md` |
| Complex multi-step reasoning | Foundations | Chain of thought, extended thinking | `references/prompt-foundations.md` |
| Output format is wrong | Foundations | Examples (multishot), XML tags | `references/prompt-foundations.md` |

## Deep Dives

For detailed guidance on specific topics, consult the reference documents:

- **`references/prompt-foundations.md`** -- Core prompt engineering techniques with examples and anti-patterns
- **`references/context-engineering-framework.md`** -- The four strategies (Write, Select, Compress, Isolate) in depth
- **`references/agent-context-patterns.md`** -- Sessions, memory types, context rot, and compaction strategies
- **`references/system-prompt-design.md`** -- System prompt anatomy, the altitude concept, and reusable templates
- **`references/memory-and-sessions.md`** -- Memory types, the memory-as-a-tool pattern, and OAK CI integration
- **`references/before-after-examples.md`** -- Extended gallery of prompt and context transformations
- **`references/evaluation-and-testing.md`** -- Measuring prompt quality, A/B testing, and iterative improvement
