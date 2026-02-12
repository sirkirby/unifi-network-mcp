# Constitution - Example (Bad)

This is an example of a poorly structured constitution. It contains vague guidance, no anchors, and unenforceable rules.

---

This project should be clean and well designed. Use best practices and write readable code.
Try to keep it simple and follow SOLID. Use Pythonic patterns when appropriate.
We want cross-platform support. Avoid magic numbers when possible.
Use tests and keep coverage high.

Architecture:

- CLI
- Services
- Models

Upgrade:

- Should be safe.
- Don't break users.

Agents:

- Should follow the rules.
- Prefer good patterns.

---

## Why This Constitution is Bad

### 1. "Best practices" is a vibe, not a rule

**Problem:** What are "best practices"? Every agent will interpret this differently.

**Fix:** Specify the practice: "All functions MUST have type hints" or "Use `ruff` for linting with config from `pyproject.toml`"

### 2. No non-goals = scope creep

**Problem:** Without explicit boundaries, agents may add features, refactor unrelated code, or make "improvements" beyond the task.

**Fix:** Add a section like "This project is NOT: a framework, an orchestrator, a package manager"

### 3. "When possible" and "when appropriate" are loophole generators

**Problem:** "Avoid magic numbers when possible" gives permission to use magic numbers whenever the agent decides it's not possible.

**Fix:** Make it absolute: "No literal strings or numbers anywhere. Use constants.py"

### 4. No anchors = freestyle

**Problem:** "Use Pythonic patterns" doesn't tell agents which patterns or where to find examples in the codebase.

**Fix:** Point to specific files: "For new services, copy `src/services/auth_service.py`"

### 5. No quality gates = optional rules

**Problem:** "Keep coverage high" is subjective. What's high? 50%? 80%? 100%?

**Fix:** Define the gate: "`make check` must pass, which includes coverage >= 80%"

### 6. No execution model = inconsistent behavior

**Problem:** Without plan-first rules or delegation guidance, agents work differently each time.

**Fix:** Add: "Before non-trivial changes, produce a plan with approach, impacted files, and verification steps"

### 7. Architecture section is just labels

**Problem:** "CLI, Services, Models" describes what exists but not how to use them or what the rules are.

**Fix:** Define the layering: "CLI parses args and delegates. Services hold business logic. Models are Pydantic types. Do not put business logic in CLI commands."

### 8. Upgrade rules are aspirational

**Problem:** "Should be safe" and "Don't break users" are intentions, not implementation guidelines.

**Fix:** Be specific: "Upgrades must support `--dry-run`. Templates are overwritten on upgrade. User data is never deleted without `--force`."

---

## The Pattern

Bad constitutions share these characteristics:

| Characteristic | Example | Why It's Bad |
|----------------|---------|--------------|
| Vague verbs | "should", "try to", "prefer" | Not enforceable |
| No examples | "follow good patterns" | Agents invent patterns |
| No metrics | "keep coverage high" | Subjective interpretation |
| Loopholes | "when possible", "if needed" | Permission to skip |
| Missing scope | (no non-goals section) | Unlimited scope creep |
| No gates | "add tests" | No definition of done |
