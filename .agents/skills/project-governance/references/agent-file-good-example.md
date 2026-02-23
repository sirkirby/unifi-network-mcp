# Agent Instruction File - Example (Golden)

This is an example of a well-structured agent instruction file. It points to the constitution, provides top anchors, and defines the required workflow.

---

# AGENTS.md

You are an AI coding agent working in this repository.

## Source of truth (hard rules)

Read and follow **`.constitution.md`**.

- If anything conflicts, **`.constitution.md` wins**.
- The canonical Anchor Index lives in `.constitution.md`.
- If uncertain, ask rather than inventing a new pattern.

## Required workflow

1. Read `.constitution.md`.
2. Search and copy the closest anchor implementation.
3. For non-trivial changes: produce a short plan and delegate discovery to sub-agents (per constitution).
4. Implement using anchors + invariants.
5. Run: `make check` (must pass).
6. Update docs to prevent drift.

## Top anchors (shorthand)

- Feature exemplar: `src/example_kit/features/<best_feature>/...`
- Agent exemplar: `src/example_kit/agents/<best_agent>/manifest.yaml`
- CLI wiring: `src/example_kit/cli.py`
- Template pipeline: `src/example_kit/services/template_service.py`
- Upgrade/migrations: `src/example_kit/services/migrations.py`

Full Anchor Index: see `.constitution.md`.

---

## Why This Agent File is Good

### 1. Short and operational

Agent instruction files should NOT duplicate the constitution. They point to it and provide quick-reference shortcuts.

### 2. Constitution is the source of truth

The file explicitly states that the constitution wins any conflicts. This prevents agents from interpreting the agent file as overriding the constitution.

### 3. "Ask if uncertain" rule

This single sentence prevents agents from inventing new patterns when they encounter something not covered by existing anchors.

### 4. Plan-first behavior included

The workflow references the plan + delegation model from the constitution, ensuring agents follow the execution model.

### 5. Top anchors save tokens

Instead of spelunking the codebase, agents start with known-good examples. This reduces exploration time and increases consistency.

### 6. Quality gate is explicit

`make check` must pass. Not "run tests if you changed something" but an absolute gate.

### 7. Docs update reminder

Prevents drift between code and documentation. Agents know they're not done until docs are updated.

---

## File Naming Conventions

Different agents use different instruction file names:

| Agent | File |
|-------|------|
| Claude Code | `CLAUDE.md` |
| GitHub Copilot | `AGENTS.md` |
| Cursor | `.cursorrules` |
| Windsurf | `.windsurfrules` |
| Gemini | `.gemini/GEMINI.md` |
| Codex | `.codex/AGENTS.md` |

The content should be similar across all, with the constitution as the shared source of truth.
