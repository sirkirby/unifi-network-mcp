# Constitution Creation Guide

Detailed guide for creating and maintaining project constitutions.

## Purpose

A project constitution establishes:
- **Hard rules** that must be followed (no exceptions)
- **Golden paths** showing how to implement common patterns
- **Anchor files** as canonical examples to copy
- **Quality gates** defining when work is complete
- **Non-goals** to prevent scope creep

Agent instruction files point to the constitution and provide quick-reference anchors.

## Constitution Structure

### Required Sections

```markdown
# Project Constitution

## Metadata
- Project, version, status, tech stack

## 1. Scope and Non-Goals (Hard Constraints)
- What the project IS and IS NOT
- Definitions (e.g., what "local-first" means)

## 2. Golden Paths
- How to add features, agents, commands, templates, config
- Anchor Index with specific file paths

## 3. Architecture Invariants (Hard Rules)
- Layering rules
- Extension patterns

## 4. No-Magic-Literals
- Where constants must live
- Type safety requirements

## 5. CLI Behavior
- Idempotence rules
- Error handling standards

## 6. Upgrade and Migrations
- Template ownership
- Migration patterns

## 7. Quality Gates (Definition of Done)
- What must pass before changes are complete

## 8. Execution Model (Optional)
- Plan-first requirements
- Sub-agent delegation rules
```

## Creating a Constitution

### Step 1: Analyze the project

```bash
# Understand the project structure
ls -la
cat README.md
cat pyproject.toml  # or package.json, Cargo.toml, etc.
```

### Step 2: Identify existing patterns

Look for:
- Configuration files and their conventions
- Service/model/controller layering
- Test patterns
- Build/lint/format tooling

### Step 3: Create the constitution

Create `oak/constitution.md` (or `.constitution.md` at root):

```markdown
# Project Constitution

## Metadata
- **Project:** your-project
- **Version:** 1.0.0
- **Status:** Draft
- **Last Updated:** YYYY-MM-DD
- **Tech Stack:** [list technologies]

## 1. Scope and Non-Goals
[Define what this project is and is NOT]

## 2. Golden Paths
[List how common changes should be made]

### Anchor Index
[Point to specific files as canonical examples]

## 3. Architecture Invariants
[Hard rules about structure]

## 4. No-Magic-Literals
[Where values must live]

## 5. CLI/API Behavior
[Idempotence, error handling]

## 6. Quality Gates
- `make check` / `npm test` / etc. must pass
- Docs updated to prevent drift
```

### Step 4: Create agent instruction files

After creating the constitution, create agent files that reference it:

```bash
oak rules sync-agents
```

## Adding Rules to Existing Constitution

**CRITICAL:** The constitution is the single source of truth. Rules MUST be added to the constitution FIRST, then synced to agent files. Never add a rule only to an agent file (CLAUDE.md, AGENTS.md, etc.) — those files reference the constitution, not the other way around.

### Step 1: Read current constitution and discover agent files

```bash
# Read the constitution (source of truth)
cat oak/constitution.md  # or .constitution.md

# Discover all agent instruction files dynamically
oak rules detect-existing
oak rules detect-existing --json  # machine-readable output
```

**Do NOT hardcode agent file names.** Agents are configured dynamically in `.oak/config.yaml` and each agent's manifest defines its own `installation.instruction_file` path.

### Step 2: Add the full rule to the constitution

Find the appropriate section and add the complete rule with:
- The rule statement using RFC 2119 language (MUST, MUST NOT, SHOULD, etc.)
- Rationale explaining WHY the rule exists
- Verification steps (how to check compliance)
- Troubleshooting guidance (what to do when the rule is violated)

Use RFC 2119 language:

| Keyword | Meaning |
|---------|---------|
| **MUST** | Absolute requirement |
| **MUST NOT** | Absolute prohibition |
| **SHOULD** | Strong recommendation (exceptions need justification) |
| **SHOULD NOT** | Strong discouragement |
| **MAY** | Optional |

Example rules:
```markdown
- All API endpoints MUST validate input using Pydantic models
- Database queries MUST use parameterized statements
- Services SHOULD be stateless; if state is needed, document why
- Teams MAY use dependency injection frameworks
```

### Step 3: Sync the rule to ALL agent instruction files

After the constitution is updated, sync to all configured agent files:

```bash
# Preview what files will be checked/updated
oak rules sync-agents --dry-run

# Sync constitution references to all agent files
oak rules sync-agents
```

If manual updates are needed, use `oak rules detect-existing --json` to get the full list of agent files. For each file, add a concise reference:

```markdown
## [Rule Name]

**MUST NOT** [brief prohibition]. See §[section] of `oak/constitution.md` for the full rule, rationale, and verification command.
```

**Important:** Agent instruction file paths are defined in each agent's manifest (`installation.instruction_file`). Do not assume fixed file names — always discover dynamically via `oak rules detect-existing`.

## Example Workflow

User: "We need to establish coding standards for this Python project"

1. **Analyze**: Read `pyproject.toml`, check for existing linters/formatters
2. **Create constitution** with:
   - Tech stack (Python 3.12+, pytest, ruff, mypy)
   - No-magic-literals rule (use constants.py)
   - Architecture (services/models/cli layers)
   - Quality gate (`make check` or equivalent)
   - Anchor files (point to best existing modules)
3. **Create agent files** referencing the constitution
4. **Sync**: `oak rules sync-agents`
