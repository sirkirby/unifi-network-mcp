# Agent Context Patterns

Context management patterns for AI agents: autonomous systems that take actions over multiple turns, read and write files, call tools, and maintain state across interactions. These patterns draw from Google's "Context Engineering: Sessions & Memory" whitepaper by Kimberly Milam & Antonio Gulli, and from production agent architectures.

---

## Sessions vs Memory

Sessions and memory serve fundamentally different roles in agent context. Conflating them leads to either bloated sessions (stuffing everything into the conversation) or amnesia (losing hard-won knowledge between conversations).

| Concept | Sessions | Memory |
|---|---|---|
| Lifetime | Single conversation | Across conversations |
| Scope | Turn-by-turn interaction | Persistent knowledge |
| Storage | Conversation history (in-context) | External database or file store |
| Growth | Linear with turns | Curated, relatively stable |
| Example | Chat messages, tool results | Learned preferences, past decisions, gotchas |

### Session Architecture

Each session is one continuous interaction with a goal. The session context grows with every turn: user message, assistant response, tool calls and their results.

A well-structured session has three phases:

1. **Start**: Goal is established, relevant context is loaded (system prompt, retrieved memories, relevant files).
2. **Middle**: Work happens. Tool calls, reasoning, intermediate results accumulate.
3. **End**: Outcome is reached. Learnings are extracted and stored to memory.

Session metadata worth tracking:

- Start time and duration
- Agent ID and model used
- Tools invoked (names and counts)
- Files read and written
- Tokens consumed (input + output)
- Outcome: completed, failed, abandoned
- Cost (if available)

This metadata becomes the raw material for episodic memory. OAK CI captures this automatically via `agent_runs` and `sessions` tables.

### Session Boundaries

Deciding when to start a new session vs. continue an existing one:

**Start a new session when:**
- The user's goal has fundamentally changed
- The previous session ended with a clear outcome
- Context has grown past the compaction threshold and a clean start is cheaper than summarization
- A different agent or model is better suited to the new task

**Continue the existing session when:**
- The new request builds directly on prior work
- Relevant context (variable bindings, file state, intermediate results) would be lost
- The user explicitly asks to continue

**Session continuity** (bridging sessions):
- Generate a session summary at the end of each session
- Store key decisions, files touched, and open questions
- Load this summary at the start of the next related session
- This is cheaper than maintaining a massive continuous context

---

## Context Rot

Context rot is the degradation of model performance as the context window fills. It is **not linear** -- performance holds steady for a while, then falls off a cliff.

### The Degradation Curve

Empirical behavior across major LLMs:

```
Performance
  |████████████████████████
  |                        ████████
  |                                ████
  |                                    ███
  |                                       ██
  |                                         █
  |__________________________________________|___
  0%        30%       50%       70%      100%
                Context Window Usage
```

- **0-35% capacity**: Performance is roughly constant. The model handles instructions, history, and retrieval well.
- **35-65% capacity**: Gradual degradation. The model starts missing details in the middle of context.
- **65-80% capacity**: Noticeable decline. Instruction-following weakens, hallucinations increase.
- **80%+ capacity**: Sharp decline. The model may ignore instructions, contradict itself, or lose track of the goal.

These thresholds vary by model and task. Complex reasoning tasks degrade earlier than simple retrieval tasks.

### Position Bias

Models do not attend equally to all positions in the context window:

- **Primacy effect**: Content at the beginning of context (system prompt, first instructions) gets disproportionate attention.
- **Recency effect**: Content at the end (most recent messages) also gets strong attention.
- **Lost in the middle**: Content in the middle of a long context receives the least attention.

**Mitigations:**

1. Place critical instructions in the system prompt (beginning of context).
2. Repeat key instructions or constraints near the end of context, especially after compaction.
3. Use XML tags or markdown headers to create clear section boundaries -- these act as attention anchors.
4. When retrieving context, place the most relevant items closest to the current turn (end of context).

### Causes of Context Rot

| Cause | Mechanism | Mitigation |
|---|---|---|
| Token accumulation | Context window fills with conversation history | Compaction or summarization before 60% capacity |
| Instruction dilution | Instructions become a smaller percentage of total context | Repeat key instructions; use XML section tags |
| Contradictory information | Earlier context conflicts with later corrections | Explicit "latest wins" rules; remove outdated content |
| Tool result bloat | Verbose tool outputs (file contents, search results) consume tokens | Summarize tool results after processing; drop raw output |
| Goal drift | Original goal buried under conversation noise | Maintain a goal scratchpad; restate goals after compaction |
| Retrieval noise | Irrelevant retrieved context dilutes signal | Filter retrieval results aggressively; prefer precision over recall |

---

## Multi-Agent Session Management

When multiple agents collaborate, context management becomes a distributed systems problem. Three fundamental patterns exist.

### Pattern 1: Shared Context

All agents read from and write to the same context window (or shared document).

```
┌─────────────────────────────────┐
│        Shared Context           │
│  ┌───────┐ ┌───────┐ ┌───────┐ │
│  │Agent A│ │Agent B│ │Agent C│ │
│  └───────┘ └───────┘ └───────┘ │
└─────────────────────────────────┘
```

**Strengths:**
- All agents see the full picture
- No communication overhead
- Simple to implement

**Weaknesses:**
- Context bloats N times faster (each agent's output adds to shared context)
- Agents may contradict each other
- Hard to scale past 2-3 agents
- No isolation: one agent's verbose output degrades context for all

**Best for:** Small teams of tightly-coupled agents working on the same artifact.

### Pattern 2: Separate Contexts (Isolation)

Each agent has its own context window. Communication happens via structured messages.

```
┌───────────┐   message   ┌───────────┐
│  Agent A   │ ──────────→ │  Agent B   │
│  (own ctx) │ ←────────── │  (own ctx) │
└───────────┘             └───────────┘
```

**Strengths:**
- Each agent gets focused, relevant context
- No cross-contamination
- Scales to many agents
- Agents can use different models optimized for their task

**Weaknesses:**
- Communication overhead (messages must be explicit)
- Risk of information loss at boundaries
- Harder to coordinate complex multi-step work

**Best for:** Diverse tasks where each agent needs specialized context (e.g., one agent researches, another codes, another reviews).

### Pattern 3: Hybrid (Orchestrator + Workers)

An orchestrator agent maintains shared state. Worker agents operate in isolation with task-specific context. Results flow back through the orchestrator.

```
              ┌──────────────┐
              │ Orchestrator  │
              │ (shared state)│
              └──┬───┬───┬──┘
                 │   │   │
          ┌──────┘   │   └──────┐
          ▼          ▼          ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Worker A  │ │ Worker B  │ │ Worker C  │
    │ (own ctx) │ │ (own ctx) │ │ (own ctx) │
    └──────────┘ └──────────┘ └──────────┘
```

**Strengths:**
- Workers get clean, focused context (no pollution from other workers)
- Orchestrator maintains the big picture
- Workers can run in parallel
- Scales well

**Weaknesses:**
- Orchestrator context can still bloat if many workers report back
- Design complexity: must define clear task boundaries and result formats

**Best for:** Production agent systems. This is the pattern used by Claude Code's team mode, OAK's analysis agents, and most multi-agent frameworks.

### Choosing a Pattern

| Factor | Shared | Isolated | Hybrid |
|---|---|---|---|
| Number of agents | 2-3 | Any | Any |
| Task coupling | Tight | Loose | Mixed |
| Context efficiency | Low | High | High |
| Implementation effort | Low | Medium | High |
| Scalability | Poor | Good | Good |

---

## Compaction Strategies

When context grows too large, you must compact it. The strategy you choose determines what knowledge survives compression.

### Strategy 1: Last-N Messages

Keep only the most recent N conversation turns. Discard everything older.

**How it works:**
```
Before: [msg1, msg2, msg3, msg4, msg5, msg6, msg7, msg8]
After (N=4): [msg5, msg6, msg7, msg8]
```

**Characteristics:**
- Simple and predictable
- Token usage is bounded
- Completely loses early context (instructions, goals, decisions made early)
- No computation overhead

**Best for:** Stateless chat applications, simple Q&A bots, situations where early context is truly irrelevant.

**Not suitable for:** Multi-step tasks where early instructions or decisions matter.

### Strategy 2: Recursive Summarization

Summarize old messages into a running summary. Keep the summary plus recent messages.

**How it works:**
```
Before: [summary_v1, msg4, msg5, msg6, msg7, msg8, msg9, msg10]
Trigger: context > 60% capacity
After:  [summary_v2 (covers msg1-msg7), msg8, msg9, msg10]
```

Where `summary_v2` incorporates `summary_v1` and `msg4-msg7` into a new summary.

**Characteristics:**
- Preserves a compressed version of all history
- Moderate token efficiency
- Risk: summarization losses compound over time (the "telephone game" effect)
- Each compaction step loses some fidelity
- Works best when the model doing summarization is high quality

**Implementation guidance:**
- Trigger summarization at 55-65% context capacity (before degradation begins)
- Use structured summaries: decisions made, files changed, open questions, key facts
- Include explicit section for "instructions that must be preserved"
- Consider having the summary reviewed/approved before discarding originals

### Strategy 3: Manus Hybrid (Structured Scratchpad)

Maintain two zones: a **verbatim zone** (recent turns, kept as-is) and a **summary zone** (older turns, compressed). Alongside both, maintain a **structured scratchpad** that is never summarized.

**How it works:**
```
Context layout:
┌─────────────────────────────┐
│ System Prompt (fixed)        │
├─────────────────────────────┤
│ Scratchpad (preserved)       │
│  - Current goal              │
│  - Key facts learned         │
│  - Decisions made            │
│  - Open questions            │
│  - Files modified            │
├─────────────────────────────┤
│ Summary Zone (compressed)    │
│  "Earlier: researched auth   │
│   options, chose JWT..."     │
├─────────────────────────────┤
│ Verbatim Zone (recent turns) │
│  [msg8, msg9, msg10]         │
└─────────────────────────────┘
```

**Characteristics:**
- Highest context preservation of any compaction strategy
- The scratchpad acts as a lossless knowledge store across compactions
- More complex to implement: requires maintaining the scratchpad format
- The scratchpad itself must be kept concise (it is never compressed)

**Implementation guidance:**
- Define scratchpad structure upfront (what sections, what format)
- Update the scratchpad explicitly during the session (not just at compaction time)
- On compaction: compress the narrative (conversation), but copy the scratchpad verbatim
- Cap scratchpad size (e.g., 2000 tokens) to prevent it from becoming its own bloat problem

### Strategy Comparison

| Strategy | Context Preservation | Simplicity | Token Efficiency | Compounding Loss | Best For |
|---|---|---|---|---|---|
| Last-N | Low | High | High | None (hard cutoff) | Short tasks, chat |
| Recursive Summarization | Medium | Medium | Medium | Yes (telephone game) | Medium-length sessions |
| Manus Hybrid | High | Low | Medium | Minimal (scratchpad preserved) | Complex multi-step tasks |
| Full (no compaction) | Perfect | Highest | Lowest | N/A | Sessions under 30% capacity |

**Rule of thumb:** If your agent sessions routinely exceed 50% context capacity, you need a compaction strategy. If they involve multi-step reasoning or long-running tasks, prefer the Manus Hybrid approach.

---

## Memory Architecture (5 Layers)

From Google's whitepaper, agent memory has five layers, analogous to human memory systems. Each layer has different lifetime, retrieval characteristics, and storage requirements.

### Layer 1: Sensory Memory (Immediate Context)

The current turn's raw input: the user's latest message, tool results just returned, documents just retrieved.

- **Lifetime:** Single turn
- **Size:** Small (one turn's worth of data)
- **Analogy:** What you are looking at right now
- **Implementation:** The latest entries in the conversation messages array
- **Key concern:** Filter aggressively. Not everything the tools return needs to stay in context.

### Layer 2: Short-Term Memory (Session Context)

The conversation history within the current session. Grows with each turn.

- **Lifetime:** Current session
- **Size:** Grows linearly; subject to context rot
- **Analogy:** What you have been thinking about for the last hour
- **Implementation:** The conversation messages array, subject to compaction
- **Key concern:** This is where context rot lives. Apply compaction strategies from the previous section.

### Layer 3: Episodic Memory (What Happened)

Records of past events and experiences. Retrieved when relevant to the current task.

- **Lifetime:** Long-term (persists across sessions)
- **Content:** Specific events: "Last time we refactored the auth module, tests broke because mock setup was order-dependent"
- **Retrieval:** Semantic search triggered by current task context
- **OAK CI equivalent:** `memory_observations` with types `bug_fix` and `gotcha`
- **Key concern:** Must be retrievable by relevance, not just recency. Vector search is preferred.

### Layer 4: Semantic Memory (Facts and Concepts)

General knowledge about the domain, the codebase, or the project. Relatively stable over time.

- **Lifetime:** Long-term, updated infrequently
- **Content:** "This codebase uses the repository pattern for data access" or "The API rate limit is 100 requests per minute"
- **Retrieval:** Semantic search, or loaded proactively based on file/topic context
- **OAK CI equivalent:** `memory_observations` with types `discovery` and `decision`
- **Key concern:** Keep entries atomic and factual. Vague or compound observations degrade search quality.

### Layer 5: Procedural Memory (How To Do Things)

Skills, procedures, and workflows. The agent's "muscle memory."

- **Lifetime:** Permanent (updated with project evolution)
- **Content:** "To add a new API endpoint: create route file, add service, write tests, update OpenAPI spec"
- **Implementation:** System prompts, constitution files, skill files, templates
- **OAK CI equivalent:** Constitution (`oak/constitution.md`), skill files, agent task definitions
- **Key concern:** This is the most valuable memory layer. It should be curated by humans, not auto-generated.

### How the Layers Integrate

At each turn, the agent assembles context from all five layers:

```
Context Assembly (per turn):

  Layer 5: System prompt + skill instructions    [always present, fixed cost]
      │
  Layer 4: Retrieved semantic memories           [loaded at session start or on topic change]
      │
  Layer 3: Retrieved episodic memories            [searched per-turn based on current task]
      │
  Layer 2: Session history (compacted)            [growing, subject to compaction]
      │
  Layer 1: Current turn input + tool results      [fresh each turn]
      │
      ▼
  ┌──────────────────┐
  │  Model Inference  │
  └──────────────────┘
```

**Token budget allocation** (approximate, for a 200K-token model):

| Layer | Budget | Notes |
|---|---|---|
| Layer 5 (Procedural) | 10-20K tokens | System prompt, skills, constitution |
| Layer 4 (Semantic) | 5-10K tokens | Retrieved facts, project knowledge |
| Layer 3 (Episodic) | 3-5K tokens | Relevant past experiences |
| Layer 2 (Session) | 50-100K tokens | Conversation history (compacted) |
| Layer 1 (Sensory) | 10-30K tokens | Current tool results, retrieved docs |
| Reserved for response | 10-30K tokens | Model's output budget |

These are guidelines, not rules. Adjust based on your model's context window and task requirements.

---

## Practical Patterns for Agent Loops

### The Observe-Think-Act-Reflect Loop

The core agent loop with explicit context management at each phase:

**1. Observe** -- Gather context before reasoning.
- Retrieve relevant memories (`oak_search`, `oak_context`)
- Read relevant files
- Check task state and dependencies
- Load any session scratchpad from prior compaction

**2. Think** -- Reason about the gathered context.
- Extended thinking / chain-of-thought helps here
- Consider multiple approaches before acting
- Identify what additional context might be needed

**3. Act** -- Take action based on reasoning.
- Write code, call APIs, modify files
- Use tools to verify results (run tests, check output)
- Keep tool calls focused: avoid retrieving more context than needed

**4. Reflect** -- Store learnings from the outcome.
- If something unexpected happened, store it as episodic memory (`oak_remember`)
- Update the session scratchpad with new facts, decisions, and open questions
- If a general pattern was discovered, store it as semantic memory

This loop naturally integrates all five memory layers: Layer 5 provides the loop structure itself, Layers 3-4 feed the Observe phase, Layer 2 provides session continuity, and Layer 1 is the current turn's input.

### Context Budget Management

Monitor context usage and trigger compaction proactively:

```
Per-turn context check:

  current_usage = system_prompt + session_history + retrieval + pending_response
  capacity = model_context_window

  if current_usage > 0.55 * capacity:
      trigger_compaction()       # Summarize old turns, preserve scratchpad

  if current_usage > 0.75 * capacity:
      aggressive_compaction()    # Deeper summarization, drop tool results

  if current_usage > 0.90 * capacity:
      emergency_compaction()     # Keep only scratchpad + last 3 turns
```

**Key principle:** Compact early, compact often. It is better to summarize 10 turns when you have headroom than to be forced into emergency compaction that loses critical context.

### Goal Persistence

Goal drift is the most common cause of agent failure in long sessions. The original task gets buried under conversation history and the agent starts optimizing for the wrong thing.

**Mitigations:**

1. **Explicit goal statement**: Store the current goal in the session scratchpad. Not just "fix the bug" but "fix the authentication timeout bug in `auth_service.py` where JWT tokens expire during long-running requests."

2. **Goal restatement**: After every compaction, restate the goal. After every N turns (e.g., 10), restate the goal.

3. **Goal decomposition**: Break complex goals into sub-goals. Track which sub-goals are complete and which remain.

4. **Completion criteria**: Define upfront what "done" looks like. "The fix is done when: (a) the timeout no longer occurs, (b) existing tests pass, (c) a new test covers the edge case."

### When to Store Memories

Not every observation deserves to be a memory. Store memories when:

| Signal | Memory Type | Example |
|---|---|---|
| Something broke unexpectedly | `gotcha` | "Mocking `datetime.now()` in this codebase requires patching the module-level import, not `datetime.datetime.now`" |
| A bug was fixed and the root cause was non-obvious | `bug_fix` | "The flaky test was caused by test ordering -- `test_auth` was leaking a database connection" |
| An architectural pattern was discovered | `discovery` | "All API routes in this project use the decorator pattern from `base_route.py`" |
| A deliberate choice was made between alternatives | `decision` | "Chose SQLite over PostgreSQL for CI data because it requires zero configuration and the data is machine-local" |
| A trade-off was identified | `trade_off` | "Compacting at 55% capacity loses less context but triggers more frequent compactions, increasing latency" |

**Do not store:**
- Obvious facts anyone could find by reading the code
- Session-specific state that will not be relevant later
- Speculative conclusions from reading a single file
- Anything already documented in the project's constitution or README

---

## Key Takeaways

1. **Sessions are ephemeral; memory is durable.** Do not try to make sessions do the job of memory, or vice versa.

2. **Context rot is non-linear.** Performance holds steady, then falls off a cliff. Compact before you hit the cliff, not after.

3. **Position matters.** Put critical instructions at the start and end of context. Use structural markers (XML tags, headers) to create attention anchors.

4. **Prefer the hybrid pattern** for multi-agent systems. Isolation protects each agent's context quality; the orchestrator maintains coherence.

5. **Compaction is not optional** for long-running agents. Choose a strategy that preserves structured knowledge (decisions, goals, facts) even as narrative history is compressed.

6. **Memory has layers.** Procedural memory (skills, constitution) is the most valuable. Episodic memory (what happened) is the most underused. Invest in both.

7. **Goals drift. State them explicitly, restate them often.** A scratchpad with the current goal, sub-goals, and completion criteria prevents the most common mode of agent failure.
