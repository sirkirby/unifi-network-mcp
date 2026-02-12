# Agent Instruction File - Example (Bad)

This is an example of a poorly structured agent instruction file. It gives vague guidance, no anchors, and permissions that lead to inconsistent behavior.

---

# AGENTS.md

You are a helpful assistant. Please do what the user asks.
Follow best practices and keep changes minimal.
Try not to break things. Add tests if needed.
If something is unclear, make a reasonable assumption.

You can use any libraries you want.
You may refactor as you see fit.

---

## Why This Agent File is Bad

### 1. "Reasonable assumption" = agents invent patterns

**Problem:** When something is unclear, agents will guess. Each agent guesses differently, leading to inconsistent codebase patterns.

**What happens:**
- Agent A assumes you want dependency injection
- Agent B assumes you want static methods
- Agent C assumes you want a different architecture entirely

**Fix:** "If uncertain, ask rather than inventing a new pattern"

### 2. "Any libraries you want" = dependency chaos

**Problem:** Agents may add heavy dependencies, unmaintained packages, or multiple libraries that do the same thing.

**What happens:**
- Agent adds `lodash` when native methods exist
- Agent adds `moment.js` when `date-fns` is already used
- Agent adds experimental packages to production code

**Fix:** "Use only dependencies already in package.json. New dependencies require explicit approval."

### 3. No constitution link = no source of truth

**Problem:** Without pointing to a constitution, agents have no architectural guidance. They freestyle based on their training data.

**What happens:**
- Each agent brings different "best practices" from different codebases
- No consistent layering or patterns
- No quality gates

**Fix:** "Read and follow `.constitution.md`. If anything conflicts, the constitution wins."

### 4. "Add tests if needed" = permission to skip tests

**Problem:** Agents interpret "if needed" as optional. They decide tests aren't needed when they're confident.

**What happens:**
- "This change is simple, tests not needed"
- "The existing tests cover this" (they don't)
- Test coverage drops over time

**Fix:** "`make check` must pass for all changes"

### 5. No execution model = no planning

**Problem:** Without plan-first requirements, agents dive straight into code changes.

**What happens:**
- Agents make changes without understanding impact
- No delegation of discovery work
- Inconsistent approaches to similar problems

**Fix:** "For non-trivial changes, produce a short plan before implementing"

### 6. "Refactor as you see fit" = scope creep

**Problem:** Agents interpret this as permission to "improve" code beyond the requested changes.

**What happens:**
- User asks for a bug fix, agent refactors three files
- User asks for a feature, agent restructures the architecture
- PRs become impossible to review

**Fix:** "Make only the requested changes. Do not refactor unrelated code unless explicitly asked."

### 7. "Keep changes minimal" contradicts "refactor as you see fit"

**Problem:** Contradictory instructions let agents choose whichever fits their current approach.

**What happens:**
- Agents cite "minimal" when they want to avoid work
- Agents cite "refactor" when they want to make big changes
- No predictable behavior

**Fix:** Have one clear instruction, not contradictory guidance.

---

## The Pattern

Bad agent files share these characteristics:

| Characteristic | Example | Why It's Bad |
|----------------|---------|--------------|
| Vague identity | "helpful assistant" | No domain context |
| No source of truth | (no constitution) | Agents freestyle |
| Optional rules | "if needed", "try to" | Permission to skip |
| Open permissions | "any libraries", "refactor as you see fit" | Chaos |
| Guessing encouraged | "reasonable assumption" | Inconsistent patterns |
| No quality gate | "add tests if needed" | No definition of done |
| Contradictions | "minimal" + "refactor" | Unpredictable behavior |
