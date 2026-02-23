# Project Constitution - Example (Golden)

This is an example of a well-structured, enforceable constitution. It is explicit, has anchors, defines non-goals, and includes quality gates.

---

## Metadata

- **Project:** ExampleKit
- **Status:** Adopted
- **Version:** 1.0.0
- **Last Updated:** 2026-01-22
- **Tech Stack:** Python 3.13+, Typer, Pydantic, Rich, Jinja2

## 1. Scope and Non-Goals (Hard Constraints)

### 1.1 Purpose

ExampleKit is a local-first CLI that installs and maintains project assets (templates, commands, configs) to support AI-assisted development workflows.

### 1.2 Explicit Non-Goals

ExampleKit is **not**:

- an agent framework, agent replacement, or agent orchestrator
- a package manager
- a CI/CD orchestrator
- a code formatter or linter runner (it integrates with existing tools)
- a remote service (network use is optional and feature-scoped)

### 1.3 Local-First Definition

"Local-first" means:

- prefer local LLM + embedding providers over cloud providers when possible
- store transactional data in SQLite
- store vector data in a local vector DB (e.g., ChromaDB)
- projects must remain usable without mandatory network access

## 2. Golden Paths (Copy These Patterns)

All changes must follow a golden path. If no path applies, stop and ask.

### 2.1 Golden Paths

- Add a new feature (vertical slice)
- Add a new agent
- Add a command
- Add a template
- Add a config value

### 2.2 Canonical Anchor Index (Single Source of Truth)

If an anchor doesn't fit, ask. Do not invent new patterns.

#### Add a new feature (vertical slice)

- `src/example_kit/features/<best_feature>/manifest.yaml`
- `src/example_kit/features/<best_feature>/service.py`
- `src/example_kit/features/<best_feature>/commands/`
- `src/example_kit/features/<best_feature>/templates/`

#### Add a new agent

- `src/example_kit/agents/<best_agent>/manifest.yaml`
- `src/example_kit/services/agent_service.py`
- `src/example_kit/constants.py`

#### Add a command

- `src/example_kit/cli.py`
- `src/example_kit/commands/<best_small_cmd>.py`
- `src/example_kit/services/<service_used_by_cmd>.py`

## 3. Architecture Invariants (Hard Rules)

### 3.1 Layering (Do Not Break)

- CLI layer parses args and delegates
- Commands layer orchestrates
- Services layer holds business logic
- Models are Pydantic types/enums
- Storage lives behind services (YAML/SQLite/vector DB)

### 3.2 Extension Over Patching

Prefer extending with new services/modules + registration over in-place hacks.
Fix root causes, not symptoms. No shortcuts.

## 4. No-Magic-Literals (Hard Ban Everywhere)

No literal strings or numbers anywhere (including tests). All literals must live in:

- `config/paths.py` (paths only)
- `config/messages.py` (user-facing text only)
- `config/settings.py` (runtime settings w/ env var support)
- `models/enums.py` (type-safe values)
- `constants.py` (keys, patterns, registries, feature config)

## 5. CLI Behavior

### 5.1 Idempotence

Commands should be safe to re-run by default. If destructive, require `--force`.

### 5.2 Errors and Logging

- Errors must be specific, actionable, and consistently formatted
- Logging must have levels usable by humans and agents
- Do not print raw tracebacks unless `--debug`

## 6. Upgrade and Migrations

### 6.1 Templates

Installed templates are managed by the tool and overwritten on upgrade. No user overrides.

### 6.2 Migrations

Migrations are reserved for major install-asset changes that mutate user project structure/data.
Feature-owned DB migrations are allowed and should run automatically post-upgrade when needed.

### 6.3 Dry Run

Upgrades must support dry-run plan output.

## 7. Quality Gates (Definition of Done)

A change is not done unless:

- `make check` passes
- docs are updated to prevent drift
- tests cover critical paths and failure modes

## 8. Execution Model (Specialized + Background Agents)

### 8.1 Plan First (Hard Rule)

Before non-trivial changes, the primary agent must produce a short plan including:

- approach, impacted areas, delegated tasks + expected outputs, verification steps

Trivial exception requires all:

- single-file edit, no new behavior, no config/templates/migrations/schema changes, no new tests required

### 8.2 Delegate for Discovery, Not Final Code

Use sub-agents for: repo discovery, design tradeoffs, test matrices, migration impact, docs drafts.
Primary agent integrates using anchors and enforces invariants.

### 8.3 Conflict Resolution

Prefer anchors; if uncertain, ask. If adopting a new pattern, update this constitution.

---

## Why This Constitution is Good

1. **Explicit scope and non-goals** - Agents know what NOT to do
2. **Concrete anchors** - "Copy this file" is enforceable; "follow good patterns" is not
3. **Defined terms** - "Local-first" has a specific meaning, not a vibe
4. **Quality gates** - `make check` must pass; not "add tests if needed"
5. **Execution model** - Plan-first requirement prevents freestyling
6. **Hard rules with narrow deviation lanes** - "Ask if uncertain" prevents invention
