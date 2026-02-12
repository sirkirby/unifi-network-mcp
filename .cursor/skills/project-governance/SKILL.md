---
name: project-governance
description: >-
  Create and maintain project constitutions, agent instruction files
  (CLAUDE.md, AGENTS.md, .cursorrules), and RFC/ADR documents. Use when
  establishing coding standards, adding project rules, creating agent guidance
  files, syncing rules across agents, proposing architectural decisions,
  creating RFCs, reviewing RFCs, or improving AI agent consistency.
allowed-tools: Bash, Read, Edit, Write
user-invocable: true
---

# Project Governance

Create, modify, and maintain project constitutions, agent instruction files, and RFC/ADR documents that guide AI agents and formalize technical decisions.

## Quick Start

### Create a constitution

```bash
# Analyze the project, then create oak/constitution.md
# See references/constitution-guide.md for the full process
```

### Create an RFC

```bash
oak rfc create --title "Add caching layer" --template feature
oak rfc list
oak rfc validate oak/rfc/RFC-001-add-caching-layer.md
```

### Sync agent instruction files

```bash
oak rules sync-agents          # Sync constitution references to all agent files
oak rules detect-existing      # Discover all configured agent instruction files
```

## Commands Reference

### Rules commands

| Command | Purpose |
|---------|---------|
| `oak rules sync-agents` | Sync constitution references to all agent instruction files |
| `oak rules sync-agents --dry-run` | Preview what files will be checked/updated |
| `oak rules detect-existing` | Discover all configured agent instruction files |
| `oak rules detect-existing --json` | Machine-readable output of agent files |

### RFC commands

| Command | Purpose |
|---------|---------|
| `oak rfc create --title "..." --template <type>` | Create a new RFC |
| `oak rfc list` | List all RFCs |
| `oak rfc validate <path>` | Validate RFC structure and content |
| `oak rfc show <path>` | Show RFC details |
| `oak rfc adopt <path>` | Mark RFC as adopted |
| `oak rfc abandon <path> --reason "..."` | Mark RFC as abandoned |

## When to Use

- **Creating a new constitution** for a project that doesn't have one
- **Adding rules** when you identify patterns that should be standardized
- **Syncing agent files** after constitution changes
- **Creating CLAUDE.md, AGENTS.md, or .cursorrules** for a new project
- **Proposing a new feature** that needs team review (RFC)
- **Making architectural decisions** that should be documented (ADR)
- **Reviewing an RFC** for completeness and technical soundness

## Constitution Structure

A good constitution is **explicit, enforceable, and anchored**:

| Quality | Good | Bad |
|---------|------|-----|
| Specificity | "All API endpoints MUST validate input using Pydantic models" | "Use best practices" |
| Anchors | "Copy `src/features/auth/service.py` for new services" | "Follow good patterns" |
| Non-goals | "This tool is NOT a CI/CD orchestrator" | (no boundaries) |
| Gates | "`make check` must pass for all changes" | "Add tests if needed" |

Required sections: Metadata, Scope and Non-Goals, Golden Paths with Anchor Index, Architecture Invariants, No-Magic-Literals, CLI Behavior, Quality Gates. See `references/constitution-guide.md` for the full structure and creation process.

## RFC Templates

| Template | Use For |
|----------|---------|
| `feature` | New features, capabilities |
| `architecture` | System architecture changes |
| `engineering` | Development practices, tooling |
| `process` | Team processes, workflows |

## Key Workflows

### Adding a rule to an existing constitution

1. **Read** the current constitution (`oak/constitution.md`)
2. **Add** the full rule to the appropriate section using RFC 2119 language (MUST, SHOULD, MAY)
3. **Sync** to all agent files: `oak rules sync-agents`

**CRITICAL:** Rules MUST be added to the constitution FIRST, then synced to agent files. Never add a rule only to an agent file.

### RFC lifecycle

1. **Create**: `oak rfc create --title "..." --template feature --author "Name"`
2. **Fill in**: Problem context, proposed solution, trade-offs, alternatives
3. **Review**: Use the review checklist (see `references/reviewing-rfcs.md`)
4. **Adopt or abandon**: `oak rfc adopt <path>` or `oak rfc abandon <path> --reason "..."`

### RFC review checklist (summary)

- Structure: Clear title, correct status, all required sections
- Context: Problem clearly stated, "why now?" addressed, scope defined
- Decision: Solution clear, technical approach explained
- Consequences: Positive/negative outcomes listed, mitigations proposed
- Alternatives: Other options considered, reasons for rejection explained

## Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| "Use best practices" | Not enforceable | Specify the practice |
| "When possible" | Loophole generator | Define when it's required |
| No anchors | Agents freestyle | Point to specific files |
| No non-goals | Scope creep | Explicitly exclude things |
| "Add tests if needed" | Permission to skip | Define coverage requirements |
| "Make reasonable assumptions" | Inconsistent patterns | Say "ask if uncertain" |

## Files

- Constitution: `oak/constitution.md` or `.constitution.md`
- Agent files: Run `oak rules detect-existing` to discover all agent instruction files
- RFCs: `oak/rfc/RFC-XXX-short-title.md`

## Deep Dives

For detailed guidance, consult the reference documents:

- **`references/constitution-guide.md`** — Full constitution creation process and structure
- **`references/constitution-good-example.md`** — Complete example of a well-structured constitution
- **`references/constitution-bad-example.md`** — Anti-patterns to avoid
- **`references/agent-files-guide.md`** — Creating and syncing agent instruction files
- **`references/agent-file-good-example.md`** — Well-structured agent file example
- **`references/agent-file-bad-example.md`** — Poorly structured agent file example
- **`references/creating-rfcs.md`** — Detailed RFC creation workflow
- **`references/reviewing-rfcs.md`** — RFC review checklist and feedback format
