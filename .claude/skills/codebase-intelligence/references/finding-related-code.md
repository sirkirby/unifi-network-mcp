# Finding Related Code

Find code that's semantically related to what you're working on, even if it uses different names or patterns. Discover relationships between components that grep and import analysis would miss.

## When to Use

Use this workflow when:
- Looking for similar implementations elsewhere in the codebase
- Finding all code related to a concept (not just by name)
- Understanding how two components relate conceptually
- Discovering patterns you should follow
- Mapping how data flows through the system
- Finding hidden dependencies beyond explicit imports

**Why this over grep**: Grep finds literal text. Semantic search finds code that *does the same thing* or *solves the same problem*, regardless of naming.

## What Grep Can't Do

| Grep | Semantic Search |
|------|-----------------|
| Finds "UserService" literally | Finds code about user management regardless of naming |
| Misses synonyms (auth vs authentication) | Understands concepts are related |
| Can't find "conceptually similar" code | Groups code by purpose, not text |
| No relevance ranking | Returns most relevant first |

## Commands

### Find related implementations

```bash
# Find code related to a concept
oak ci search "form validation logic" --type code

# Find similar patterns
oak ci search "retry with exponential backoff" --type code

# More results for broader exploration
oak ci search "error handling and logging" --type code -n 20
```

### Discover component relationships

```bash
# Find code related to two concepts (relationship)
oak ci search "how does AuthService interact with TokenManager"

# Search for data flow patterns
oak ci search "order creation inventory update"

# Get context about a specific relationship
oak ci context "relationship between UserService and PaymentProcessor"
```

### Get context for current work

```bash
# Find code related to files you're editing
oak ci context "similar implementations" -f src/services/user.py

# Find related code for a specific task
oak ci context "validation patterns" -f src/api/handlers.py

# Get context with specific files in focus
oak ci context "how auth middleware relates to session handling" -f src/middleware/auth.py
```

## Example: Finding Similar Implementations

**Task**: Implementing a new API endpoint, want to follow existing patterns

```bash
# 1. Find existing endpoint implementations
oak ci search "REST API endpoint handler" --type code

# 2. Find validation patterns
oak ci search "input validation for API requests" --type code

# 3. Find error handling patterns
oak ci search "API error response formatting" --type code
```

**What you'll find**: Consistent patterns used elsewhere, even if the endpoints are in different modules or use different naming conventions.

## Example: Finding All Code for a Concept

**Task**: Understanding all authentication-related code

```bash
# Grep would miss these:
# - "verify_credentials" (doesn't say "auth")
# - "session_handler" (related concept)
# - "token_refresh" (authentication adjacent)

# Semantic search finds them all:
oak ci search "user authentication and authorization" --type code -n 20
```

## Example: Understanding Component Relationships

**Question**: "How does the OrderService relate to the InventoryService?"

```bash
# 1. Search for code mentioning both concepts
oak ci search "OrderService inventory management"

# 2. Get broader context
oak ci context "relationship between orders and inventory"

# 3. Search for data flow patterns
oak ci search "order creation inventory update"
```

**What you'll find**: Semantic search reveals event handlers, shared models, and integration points that aren't obvious from imports alone.

## Tips

- Search for **what code does**, not **what it's called**
- Use natural language: "sending email notifications" not "email_sender"
- Ask about relationships: "how does X interact with Y"
- Increase `-n` limit when exploring broadly
- Use `--type code` to focus on implementation (exclude memories)
- Combine multiple searches to build complete picture
- Combine with `oak ci context` for richer understanding

## Output

Results include:
- File path and line numbers
- Relevance score (higher = more related)
- Code snippet showing the match

```bash
# JSON output (default) - good for parsing
oak ci search "database transactions" -f json

# Text output - good for reading
oak ci search "database transactions" -f text
```
