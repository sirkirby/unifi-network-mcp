# System Prompt Design

System prompts define who the model is, what it should do, and how it should behave. This reference covers effective system prompt anatomy, writing instructions at the right abstraction level, Claude-specific patterns, and annotated templates.

---

## System Prompt Anatomy

Every effective system prompt has five components, in this order. Ordering matters — models give more weight to content that appears earlier.

### 1. Role and Identity

One or two sentences establishing domain expertise. Sets tone, vocabulary, and decision-making framework.

```
You are a senior backend engineer specializing in distributed systems.
```

Be specific enough to shape behavior, broad enough to handle varied inputs. Avoid character fiction ("Dr. Sarah Chen, known for dry wit") — it dilutes technical focus. Avoid generics ("You are a helpful assistant") — it changes nothing.

### 2. Core Constraints

Hard rules the model must always follow. Put these BEFORE task instructions — models respect early constraints more reliably. Use RFC 2119 language (MUST, MUST NOT, SHOULD, MAY) for clarity.

```xml
<constraints>
- You MUST NOT modify database schema without explicit approval
- You MUST cite specific file and line numbers when identifying issues
- You SHOULD prefer backward-compatible solutions
- When uncertain, ask for clarification rather than guessing
</constraints>
```

The last line is critical — every system prompt should define what the model does when unsure. Without it, the model either guesses (risky) or refuses (unhelpful).

### 3. Task Instructions

What the model should do. Write at the right "altitude" — principles over procedures (see the Altitude Scale below).

```xml
<instructions>
When reviewing code, focus on correctness and security over style.
Flag potential issues but do not rewrite working code for aesthetic reasons.
When multiple approaches exist, explain the tradeoffs and recommend one.
</instructions>
```

Good task instructions answer: What is the primary objective? What gets prioritized when objectives conflict? What does "done" look like?

### 4. Output Format

Be explicit — the model won't consistently infer format preferences.

```xml
<output_format>
Respond with a JSON object:
{
  "summary": "One-sentence assessment",
  "issues": [{"severity": "critical|warning|info", "file": "path", "line": 42, "description": "...", "suggestion": "..."}],
  "overall_rating": "approve | request-changes | needs-discussion"
}
</output_format>
```

If you want markdown, say so. If you want JSON, provide the schema. Ambiguity here is the most common source of format drift.

### 5. Canonical Examples

Two to three input-output pairs demonstrating ideal behavior. Examples anchor behavior more reliably than instructions alone. Show range (positive and negative cases) and edge cases.

```xml
<example>
<input>
def get_user(id):
    query = f"SELECT * FROM users WHERE id = {id}"
    return db.execute(query)
</input>
<output>
**Critical: SQL Injection** — line 2 uses f-string with user input.
Fix: `db.execute("SELECT * FROM users WHERE id = ?", [id])`
</output>
</example>
```

---

## The Altitude Scale

The most common system prompt mistake is writing instructions at the wrong abstraction level.

### Level 1: Ground Level (Too Specific)

```
Always use 4-space indentation. Variable names must be camelCase.
Functions must not exceed 20 lines.
```

Brittle. Doesn't adapt to context. What happens when the codebase uses tabs?

### Level 2: Cruising Altitude (Right Level)

```
Follow the project's established conventions. Match surrounding
code style. Prefer clarity over cleverness.
```

Principled, adaptable. Handles novel situations because it has principles, not just rules.

### Level 3: Stratosphere (Too Vague)

```
Write good code. Be helpful. Follow best practices.
```

No actionable guidance. The model falls back to generic behavior.

### Finding Your Altitude

| Domain | Too Low | Right Altitude | Too High |
|---|---|---|---|
| Code Review | "Flag if cyclomatic complexity > 10" | "Flag functions hard to understand at a glance" | "Review the code" |
| Writing | "Sentences must be 12-15 words" | "Write concisely. Prefer short sentences. Cut filler." | "Write well" |
| Data Analysis | "Use pandas groupby then merge" | "Use efficient operations. Profile before optimizing." | "Analyze the data" |
| Security Audit | "Check for CVE-2024-1234" | "Identify injection points and trust boundaries" | "Find vulnerabilities" |

**The test:** If your instruction applies regardless of language, framework, or codebase, it's the right altitude.

---

## Claude-Specific Patterns

### XML Tag Conventions

Claude has strong native understanding of XML structure:

- `<context>`, `<instructions>`, `<constraints>`, `<examples>` for top-level sections
- Nesting up to 2-3 levels: `<examples><example><input>...</input><output>...</output></example></examples>`
- Attributes for metadata: `<document id="1" title="API Spec" path="src/api.py">`
- Descriptive tag names — `<error_log>` over `<data>`, `<user_request>` over `<input>`
- No `<system>` wrapper needed — Claude already knows it's reading a system prompt

### Extended Thinking Integration

Guide the model toward deeper reasoning without constraining its process. Say "Think deeply about edge cases before responding" (good) rather than "First list all components, then draw arrows, then rate each on a 1-5 scale" (bad). Specify what to produce, not how to think.

### Prefilling

Start the assistant's response to anchor output format:

```
Assistant: {"analysis":
```

Useful for ensuring JSON output, anchoring structure, or preventing preamble ("Sure! Here's my analysis..."). Use prefilling for format, not for constraining reasoning.

---

## Annotated Templates

### Code Review Agent

```xml
You are a senior software engineer performing code review.

<constraints>
- Focus on correctness, security, and maintainability
- Do NOT rewrite working code for style preferences alone
- Flag potential bugs with severity: critical, warning, info
- If uncertain whether something is a bug, say so explicitly
- MUST NOT approve code with known security vulnerabilities
</constraints>

<instructions>
Review the provided code changes. For each issue:
1. Identify the file and line
2. Describe the issue and why it matters
3. Suggest a fix

After reviewing, provide a summary assessment.
If no issues are found, say so — do not fabricate issues.
</instructions>
```

Constraints before instructions, "do not fabricate" prevents false positives, severity levels in constraints keep output consistent.

### Research Assistant

```xml
You are a research assistant analyzing documents and synthesizing findings.

<constraints>
- Cite sources with specific quotes or page references
- Distinguish facts in documents from your inferences
- If asked about something not in the documents, say so clearly
- MUST NOT fabricate citations or references
</constraints>

<instructions>
Analyze provided documents: identify themes, note contradictions between
sources, synthesize findings. Use <finding> tags with source attribution.
</instructions>

<output_format>
<finding source="Document Title, p. X">
[Insight with direct quote or specific reference]
</finding>
</output_format>
```

MUST NOT on fabricated citations addresses the highest-risk failure mode. Distinguishing facts from inferences prevents the model from presenting reasoning as source material.

### Data Analysis Agent

```xml
You are a data analyst working with structured datasets.

<constraints>
- Show methodology before results
- Validate data quality before analysis (nulls, duplicates, outliers)
- State assumptions explicitly
- Do not over-interpret small samples (note when n < 30)
</constraints>

<instructions>
For each analysis: understand the question, examine data quality,
choose and explain the method, present findings with caveats.
Prefer tables over prose for numerical results.
</instructions>
```

Methodology-before-results prevents jumping to conclusions. Concrete threshold (n < 30) instead of vague "be careful."

---

## Cross-Reference

See also: The `/project-governance` skill for creating and maintaining project constitutions and agent rules files — these are system prompts implemented as version-controlled documents.
