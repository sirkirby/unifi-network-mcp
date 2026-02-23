# Agent Instruction Files Guide

Create and maintain agent instruction files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.windsurfrules`, etc.) that point to the project constitution and provide quick-reference anchors.

## Purpose

Agent instruction files are **short, operational documents** that:
- Point to the constitution as the source of truth
- Provide top anchor shortcuts for common tasks
- Define the required workflow (read constitution, copy anchors, run gates)
- Do NOT duplicate the constitution

## Creating Agent Files

### Option 1: Use OAK's sync command

```bash
oak rules sync-agents
```

### Option 2: Create manually

See `agent-file-good-example.md` for a complete example.

Template:

```markdown
# CLAUDE.md (or AGENTS.md)

You are an AI coding agent working in this repository.

## Source of truth
Read and follow **`.constitution.md`** (or `oak/constitution.md`).
- If anything conflicts, the constitution wins.
- If uncertain, ask rather than inventing patterns.

## Required workflow
1. Read the constitution
2. Find and copy the closest anchor
3. Run quality gates
4. Update docs

## Top anchors
[List 3-5 most common anchor files]
```

## Discovering Agent Files

Do NOT hardcode agent file names. Use OAK's built-in commands:

```bash
# Discover all agent instruction files dynamically
oak rules detect-existing
oak rules detect-existing --json  # machine-readable output
```

Agent files are configured dynamically in `.oak/config.yaml` and each agent's manifest defines its own `installation.instruction_file` path.

## File Naming Conventions

> **Note:** This table is for background context only. Always use
> `oak rules detect-existing` to get the actual file paths for your
> project — agents may be configured with different paths than the
> defaults shown here.

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

## Syncing After Constitution Changes

When the constitution is updated, sync changes to all agent files:

```bash
# Preview what files will be checked/updated
oak rules sync-agents --dry-run

# Sync constitution references to all agent files
oak rules sync-agents
```

## What Makes a Good Agent File

1. **Short and operational** — does NOT duplicate the constitution
2. **Constitution is the source of truth** — explicitly states the constitution wins conflicts
3. **"Ask if uncertain" rule** — prevents agents from inventing new patterns
4. **Plan-first behavior** — references the execution model from the constitution
5. **Top anchors** — agents start with known-good examples
6. **Quality gate is explicit** — `make check` must pass, not "run tests if needed"
7. **Docs update reminder** — prevents drift between code and documentation
