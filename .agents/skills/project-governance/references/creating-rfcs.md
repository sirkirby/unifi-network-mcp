# Creating RFCs

Create RFC (Request for Comments) documents for formal technical planning and decision-making.

## When to Use

Use this workflow when:
- Planning a significant architectural change
- Proposing a new feature that needs team review
- Documenting a technical decision (ADR-style)
- Changes that affect multiple teams or systems

**Note**: This is for formal RFC/ADR workflows. For quick implementation planning, use the agent's native plan mode instead.

## How It Works

1. **You gather** the problem context and proposed solution
2. **Create** the RFC using the CLI
3. **Iterate** on the document based on feedback

## Quick Start

```bash
# Create an RFC interactively
oak rfc create --title "Add caching layer" --template feature

# List existing RFCs
oak rfc list

# Validate an RFC
oak rfc validate oak/rfc/RFC-001-add-caching-layer.md
```

## RFC Templates

| Template | Use For |
|----------|---------|
| `feature` | New features, capabilities |
| `architecture` | System architecture changes |
| `engineering` | Development practices, tooling |
| `process` | Team processes, workflows |

## RFC Structure

A good RFC includes:

```markdown
# RFC-XXX: Title

## Status
Draft | Under Review | Adopted | Abandoned

## Context
What problem are we solving? Why now?

## Decision
What are we proposing?

## Consequences
- Positive outcomes
- Negative outcomes
- Risks and mitigations

## Alternatives Considered
What else did we consider? Why not those?
```

## Workflow

### 1. Create the RFC

```bash
oak rfc create --title "Your RFC Title" --template feature --author "Your Name"
```

This creates a file in `oak/rfc/` with the proper structure.

### 2. Fill in the content

Edit the generated file to add:
- Problem context
- Proposed solution
- Trade-offs and alternatives
- Implementation plan (if applicable)

### 3. Share for review

The RFC is now ready for team review. Once approved:

```bash
oak rfc adopt oak/rfc/RFC-XXX-your-rfc.md
```

Or if abandoned:

```bash
oak rfc abandon oak/rfc/RFC-XXX-your-rfc.md --reason "Superseded by RFC-YYY"
```

## Tips

- **Keep it focused** - One decision per RFC
- **Include context** - Future readers need to understand the "why"
- **Document alternatives** - Shows you considered options
- **Be honest about trade-offs** - Nothing is perfect

## File Location

RFCs are stored in `oak/rfc/` with the naming convention:
```
RFC-XXX-short-title.md
```
