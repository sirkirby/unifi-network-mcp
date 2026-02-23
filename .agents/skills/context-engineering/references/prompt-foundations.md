# Prompt Engineering Foundations

Eight core techniques for writing effective prompts. Each section covers: what it is, when to use it, how to apply it, a concrete example, and common mistakes.

---

## 1. Be Clear and Direct

Specificity eliminates ambiguity. Tell the model exactly what you want — format, length, style, and constraints.

**How to apply:**
- State the task, format, and constraints up front
- Use imperative verbs: "List", "Analyze", "Write", "Compare"
- Specify exclusions when they matter
- Define success criteria

**Example — bad vs good:**

```
Bad:  Review this code.

Good: Review this Python function for:
      1. Security vulnerabilities (injection, XSS)
      2. Performance issues (N+1 queries, unnecessary allocations)
      3. Correctness bugs (off-by-one, null handling)

      For each issue: line number, severity (critical/warning/info),
      and corrected code. If none found, say "None found."
```

**Mistakes:** Assuming the model infers format preferences. Using vague qualifiers ("good", "comprehensive") without defining them. Omitting constraints then being surprised by the output shape.

---

## 2. Use Examples (Multishot Prompting)

Provide 3-5 input-output examples demonstrating the pattern you want. Examples are the most reliable way to specify format, tone, and edge case handling.

**How to apply:**
- 3-5 examples minimum (one or two won't establish a pattern)
- Vary them: happy path, edge cases, boundary conditions, negative cases
- Show exact input-output structure
- Order simple to complex

**Example:**

```xml
Classify each customer message into exactly one category.

<examples>
<example>
<input>I can't log in even with the right password</input>
<output>category: authentication | priority: high</output>
</example>
<example>
<input>How much does the enterprise plan cost?</input>
<output>category: billing | priority: low</output>
</example>
<example>
<input>Your product crashed during my presentation!!!</input>
<output>category: bug-report | priority: critical</output>
</example>
<example>
<input></input>
<output>category: invalid | priority: none</output>
</example>
</examples>

Now classify: <input>{{MESSAGE}}</input>
```

The last example teaches the model how to handle malformed input rather than leaving it to guess.

**Mistakes:** Only showing happy-path examples. Examples too similar to each other. Inconsistent formatting across examples (the model mirrors inconsistency).

---

## 3. Chain of Thought (CoT)

Instruct the model to reason step by step before answering. Dramatically improves accuracy on logic, math, and multi-step analysis.

**Three levels:**

**Basic** — add "Think step by step." Simple, effective for straightforward reasoning.

**Guided** — provide numbered steps when the reasoning process matters:
```
Determine if this function has a bug:
1. Identify what it should do from name and docstring
2. Trace logic with a normal input
3. Trace with edge cases (empty, null, boundary)
4. Compare actual vs expected behavior
5. Conclude: bug or no bug, with evidence
```

**Structured** — wrap reasoning in tags to separate thinking from output:
```xml
Analyze whether this migration is safe for production.

Work through your analysis inside <reasoning> tags, then give your
verdict inside <verdict> tags. Consider: table locks, reversibility,
data backfill volume, partial failure scenarios.
```

| Level | Use when |
|---|---|
| Basic | Simple math, single-step deductions |
| Guided | Multi-step debugging, analysis where process matters |
| Structured | Complex decisions, when downstream systems consume the reasoning |

**Mistakes:** Using CoT for simple factual lookups (adds latency, no accuracy gain). Over-constraining the thinking format. Asking for "just the answer" on hard problems.

---

## 4. Use XML Tags for Structure

Claude treats XML tags as first-class structural elements — the most reliable way to separate context, instructions, examples, and output format.

**When to use:** Any prompt with more than one logical section, when mixing data with instructions, when specifying output format.

**Example:**
```xml
<context>
Debugging a failing test suite. Project: Python 3.12, pytest.
</context>

<test_output>
FAILED test_auth.py::test_login_redirect - expected 302, got 200
FAILED test_auth.py::test_expired_token - connection pool exhausted
</test_output>

<instructions>
For each failure: identify root cause, determine if related, suggest fix.
</instructions>

<output_format>
## [test name]
**Root cause:** [one sentence]
**Related:** [yes/no and why]
**Fix:** [code block]
</output_format>
```

**Nesting** for hierarchy (two levels is usually sufficient):
```xml
<documents>
  <document id="1" title="API Spec">...content...</document>
  <document id="2" title="Error Logs">...content...</document>
</documents>
```

**Mistakes:** Generic tag names (`<data>`) instead of specific ones (`<error_log>`). Over-nesting beyond two levels. Mixing XML tags with markdown headers for the same purpose.

---

## 5. Give Claude a Role (System Prompts)

The system prompt establishes persistent behavioral context — role, constraints, and output conventions that frame every response.

**How to apply:**
- Define role, expertise, and boundaries
- Set the right altitude: specific enough to be useful, general enough for varied inputs
- Include what to do when uncertain

**Example — bad vs good:**

```
Bad:  You are a helpful coding assistant. Be thorough and accurate.
```
"Helpful" and "thorough" are not actionable — they contain no specific guidance.

```xml
Good:
<role>
Senior backend engineer. Python + PostgreSQL.
Production system handling financial transactions.
</role>

<constraints>
- Never sacrifice data consistency for performance
- Flag non-idempotent operations
- When unsure, say "I'm not confident because..." rather than guessing
</constraints>

<output_conventions>
- Python type hints in all code examples
- Include error handling (no happy-path-only code)
- Reference specific line numbers when reviewing
</output_conventions>
```

**Mistakes:** System prompt so long it dilutes the important parts. Only negative instructions ("don't do X") without positive guidance. Role too narrow, causing refusals on legitimate requests.

---

## 6. Chain Complex Prompts

Break complex tasks into sequential steps where output of step N feeds step N+1. Better results than asking for everything at once.

**When to use:** Tasks with distinct phases (research, analyze, synthesize). When quality at each step matters. When different steps need different instructions.

**Example pipeline:**
```
Step 1 (Extract):  "Extract all function signatures and docstrings."
Step 2 (Analyze):  "For each function, identify missing error handling,
                    unused params, unclear naming. Rate severity."
Step 3 (Synthesize): "Group by severity. Write corrected code for
                      critical/warning issues. Summarize in a table."
```

**Gate outputs between steps** — validate before passing forward:
```python
extracted = call_model(step_1_prompt, document)

# Gate: verify extraction produced results
if not extracted.functions:
    raise ValueError("Extraction empty — check input format")

analysis = call_model(step_2_prompt, extracted)
```

**Mistakes:** Passing too much context between steps (carry only what the next step needs). Not validating intermediates. Steps too granular (each should do meaningful work).

---

## 7. Long Context Window Tips

Position and organization of information in the context window significantly affects output quality. The "lost in the middle" effect means information buried in the center of very long contexts gets less attention.

**Key techniques:**

**Front-load and repeat critical instructions:**
```xml
<instructions>
<!-- FIRST: anchor behavior -->
Find all security vulnerabilities. Focus on injection, auth bypass, data exposure.
</instructions>

<codebase>
...thousands of lines...
</codebase>

<reminder>
<!-- LAST: reinforce -->
Focus only on security vulnerabilities.
Format: file, line, type, severity, fix.
</reminder>
```

**Tag-delineate sections** when including multiple documents:
```xml
<documents>
  <document title="Auth Module" path="src/auth.py">...code...</document>
  <document title="Schema" path="schema.sql">...schema...</document>
</documents>
```

**Include retrieval hints** for very long contexts: "Find the users table in the Schema document and check for a unique constraint on email."

**Order by relevance:** most relevant documents first. For bug analysis: error/stack trace, then source file, then config, then tests, then docs.

**Mistakes:** Dumping context without structure. Critical instructions only in the middle. Including irrelevant context "just in case" (dilutes attention).

---

## 8. Extended Thinking

Extended thinking allocates dedicated tokens for the model to reason internally before producing a visible response. Unlike CoT, this happens in a separate, larger thinking space and can use significantly more tokens.

**When to use:**
- Complex math or proofs
- Multi-file code analysis with component interactions
- Architecture decisions with many tradeoffs
- Debugging where root cause is non-obvious

**When NOT to use:** Simple factual questions, straightforward code generation, tasks where speed matters more than depth.

**How to apply:**

Set thinking budget based on complexity: small for simple debugging, large for architecture review or multi-step planning.

Let the model reason freely — don't constrain thinking format:
```
Good: "Analyze this distributed system for consistency issues.
       Think deeply about edge cases before responding."

Bad:  "In your thinking, first list all components, then draw
       arrows between them, then..."
```

Specify what to *produce*, not how to *think*. Combine with structured output:
```xml
<task>
Review this migration plan. Consider data integrity, rollback safety,
and performance impact on a 50M-row table.
</task>

<output_format>
1. GO / NO-GO recommendation
2. Risk summary (one paragraph)
3. Required changes before deploy (bulleted list)
</output_format>
```

**Mistakes:** Enabling for every prompt (wastes tokens on simple tasks). Controlling the thinking format. Using thinking as substitute for providing good context.

---

## Anti-Patterns Reference

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| "Be helpful" | Too vague, no actionable guidance | Specify exact behavior, constraints, output format |
| Contradictory instructions | Model picks one unpredictably | Resolve conflicts; prioritize with "IMPORTANT" |
| Wall of text prompt | Key info buried, position bias | Structure with XML; front-load critical info |
| No examples | Model guesses output format | Add 3-5 diverse multishot examples |
| "Do everything at once" | Exceeds single-prompt capacity | Chain into sequential steps with gates |
| Overly rigid templates | Brittle to edge cases | Define principles and show examples instead |
| "Don't do X" (only negatives) | Model attention anchors on X | State what TO do instead |
| Expecting one-shot perfection | Unrealistic for complex tasks | Iterate: test varied inputs, refine on failures |
| Kitchen-sink system prompt | Dilutes important instructions | Keep focused: role, constraints, output conventions |
| No output validation | Hallucinations and drift undetected | Validate between chained steps |
