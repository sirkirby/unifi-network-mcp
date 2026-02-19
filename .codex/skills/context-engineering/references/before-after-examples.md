# Before/After Examples

Concrete transformations showing how context engineering techniques improve real prompts. Each example: **Before** (problematic), **Diagnosis** (what's wrong), **Techniques Applied**, **After** (improved).

---

## 1. Vague Prompt to Structured Prompt

### Before
```
Help me with this code. It's not working right and I need it fixed.
```

### Diagnosis
- "Not working" gives zero actionable detail -- no code, no error, no expected behavior
- No output format specified

### Techniques Applied
- **Be Clear and Direct**: state the exact problem and expected vs actual behavior
- **XML Tags**: separate code, error, and instructions

### After
```xml
<code language="python">
def calculate_discount(price, tier):
    if tier == "gold": return price * 0.8
    if tier == "silver": return price * 0.9
    return price
</code>

<error>calculate_discount(100, "Gold") returns 100 instead of 80.</error>

<instructions>
1. Identify why the function fails for "Gold" (capital G)
2. Fix the bug
3. Add handling for invalid tier values (return price unchanged, log a warning)
</instructions>

<output_format>Root cause (one sentence), fixed code, test cases.</output_format>
```

**Why it works:** The model knows exactly what is broken, what the expected behavior is, and what to produce. No ambiguity about scope or success criteria.

---

## 2. Wall of Text to XML-Structured Context

### Before
```
Here's my API spec and some error logs and the database schema. The API
spec says we have a /users endpoint that accepts POST with name and email.
The email should be unique. Here are the error logs: [2024-01-15 14:23:01]
IntegrityError: duplicate key violates "users_email_key" Request: POST
/users {"name": "Jane", "email": "jane@test.com"} And the schema is
CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT
NOT NULL UNIQUE). Why am I getting these errors?
```

### Diagnosis
- Three data sources in one paragraph with no separation
- Question buried at the end -- model reads data without knowing the goal

### Techniques Applied
- **XML Tags**: each data source in its own labeled section
- **Long Context Tips**: front-load the question

### After
```xml
<question>
Why do duplicate key errors occur on POST /users? Provide: root cause, fix, error response.
</question>

<error_logs>
[2024-01-15 14:23:01] IntegrityError: duplicate key violates "users_email_key"
  Request: POST /users {"name": "Jane", "email": "jane@test.com"}
[2024-01-15 14:25:12] IntegrityError: duplicate key violates "users_email_key"
  Request: POST /users {"name": "John", "email": "jane@test.com"}
</error_logs>

<database_schema>
CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE);
</database_schema>

<api_spec>POST /users — Body: { name, email } — email must be unique</api_spec>
```

**Why it works:** Each data source is labeled. The question is front-loaded so the model reads data with the goal already in mind.

---

## 3. Bloated System Prompt to Altitude-Optimized

### Before (22 generic directives)
```
You are an AI assistant. Be helpful, harmless, honest. Be polite.
Use clear language. Be concise but thorough. Prioritize accuracy.
Always cite sources. Be creative when appropriate. Ask clarifying
questions. Be empathetic. Use examples. Stay on topic. [... 10 more ...]
```

### Diagnosis
- None specific enough to change behavior -- "be helpful" is default
- Contradictions: "be concise" vs "be thorough"
- No role, no domain, no output conventions

### Techniques Applied
- **Altitude optimization**: raise to principled guidance
- **System prompt design**: define role with domain expertise

### After
```xml
<role>
Code reviewer. Domain: Django REST APIs with PostgreSQL. Senior level.
</role>

<constraints>
- Flag security issues as CRITICAL regardless of other priorities
- If a change affects schema, always mention migration safety
- When trade-offs exist, state both options and recommend one
- Say "I'm not sure" rather than guessing on library-specific behavior
</constraints>

<output_conventions>
- Reference file:line_number for each finding
- Severity: CRITICAL, WARNING, SUGGESTION
- Include corrected code for CRITICAL and WARNING items
</output_conventions>
```

**Why it works:** 22 vague directives became 7 specific rules. Generic advice is gone; domain-specific guidance takes its place.

---

## 4. Context-Stuffed Agent to Compress and Isolate

### Before
```
System prompt permanently includes:
- Full API docs (8K tokens), database schema (3K), error codes (2K),
  coding standards (1.5K), changelog (4K) = ~18,500 tokens always loaded
```

### Diagnosis
- Most reference data used rarely (~5% per conversation)
- 18K tokens permanently occupied; position bias weakens middle sections
- Stale data in the system prompt is worse than no data

### Techniques Applied
- **Isolate**: move reference data behind tool calls
- **Compress**: summarize what remains
- **Select**: retrieve only what the current query needs

### After
```
System prompt (800 tokens): role, principles, tool instructions

Tools:
- search_api_docs(endpoint) -> docs for one endpoint
- query_schema(table_name) -> schema for one table
- lookup_error_code(code) -> one error definition
- get_coding_standards(topic) -> relevant standards
```

**Why it works:** 18,500 to 800 tokens (95% reduction). Data always current (retrieved live). Model attention focused. Cost drops proportionally.

---

## 5. Stateless Agent to Memory-Augmented

### Before
```
User: "Can you help me with the auth module?"
Agent: Starts from scratch. Doesn't know about the circular import
       bug fixed last week or the refactor merged yesterday.
```

### Diagnosis
- No persistent memory -- each session reinvents the wheel
- Same gotchas hit repeatedly; user re-explains context every time

### Techniques Applied
- **Write**: store observations as they emerge
- **Select**: retrieve relevant memories at session start

### After
```
Session start: Agent receives injected context:
  - Recent session summaries, active gotchas, unresolved observations

During work: Agent stores learnings:
  oak_remember("Auth circular import caused by module-level import
  of UserModel. Fixed by moving inside function.",
  memory_type="bug_fix", context="src/services/auth_service.py")

Next session: "Help with the auth module?"
  Agent already knows about the circular import and last week's refactor.
```

**Why it works:** The agent compounds knowledge across sessions. Gotchas caught once stay caught.

---

## 6. Poor Few-Shot to Diverse Multishot

### Before (2 trivial examples)
```
Convert descriptions to SQL queries.
Example: "Get all users" -> SELECT * FROM users;
Example: "Get active users" -> SELECT * FROM users WHERE active = true;
Now convert: "Get the top 5 customers by total spending last quarter"
```

### Diagnosis
- 2 examples, both trivially simple (single table, no joins)
- Actual task requires JOIN, GROUP BY, ORDER BY, LIMIT, date filtering
- No schema -- model guesses table and column names

### Techniques Applied
- **Multishot examples**: 5 diverse examples, simple to complex
- **XML Tags**: structure examples and provide schema

### After
```xml
Convert natural language to PostgreSQL using this schema:

<schema>
users(id, name, email, created_at)
orders(id, user_id, total_amount, created_at, status)
products(id, name, price, category)
order_items(order_id, product_id, quantity)
</schema>

<examples>
<example>
<input>Get all users</input>
<output>SELECT * FROM users;</output>
</example>
<example>
<input>Active orders with user names</input>
<output>SELECT u.name, o.id, o.total_amount
FROM orders o JOIN users u ON u.id = o.user_id WHERE o.status = 'active';</output>
</example>
<example>
<input>Count orders per user, highest first</input>
<output>SELECT u.name, COUNT(o.id) AS order_count
FROM users u LEFT JOIN orders o ON o.user_id = u.id
GROUP BY u.id, u.name ORDER BY order_count DESC;</output>
</example>
<example>
<input>Revenue by product category this year</input>
<output>SELECT p.category, SUM(oi.quantity * p.price) AS revenue
FROM order_items oi JOIN products p ON p.id = oi.product_id
JOIN orders o ON o.id = oi.order_id
WHERE o.created_at >= DATE_TRUNC('year', CURRENT_DATE)
GROUP BY p.category ORDER BY revenue DESC;</output>
</example>
<example>
<input>Users who never placed an order</input>
<output>SELECT u.name, u.email FROM users u
LEFT JOIN orders o ON o.user_id = u.id WHERE o.id IS NULL;</output>
</example>
</examples>

<input>Get the top 5 customers by total spending last quarter</input>
```

**Why it works:** Examples progress simple to complex, covering JOINs, GROUP BY, LEFT JOIN for negation, date functions. Schema is explicit.

---

## 7. Unconstrained Output to Prefilled and Formatted

### Before
```
Analyze this error log and tell me what happened.
[error log contents]
```

### Diagnosis
- No output structure -- could be a paragraph, list, or narrative
- "What happened" is open-ended; no actionable structure

### Techniques Applied
- **Output format**: define exact structure expected
- **Be Clear and Direct**: bound the scope of analysis

### After
```xml
<instructions>
Analyze this error log. Identify root cause, impact, and fix.
Respond in exactly this JSON format -- no additional commentary.
</instructions>

<error_log>[error log contents]</error_log>

<output_format>
{
  "root_cause": {
    "error": "specific error message",
    "location": "file:line or service",
    "explanation": "one sentence"
  },
  "impact": {
    "user_facing": "what the user experienced",
    "scope": "affected users/requests if determinable"
  },
  "fix": {
    "immediate": "what to do now",
    "preventive": "what to change to prevent recurrence"
  }
}
</output_format>
```

**Why it works:** The JSON schema acts as a contract. The model produces parseable output, and the three-part structure ensures analysis is actionable, not just descriptive.

---

## Pattern Summary

| Transformation | Key Technique | Typical Improvement |
|---|---|---|
| Vague to Structured | Clarity + XML tags | Consistent, relevant responses |
| Wall of text to XML sections | XML structure | Better information extraction |
| Low altitude to Right altitude | Altitude optimization | Smaller prompt, better adherence |
| Context-stuffed to Tool-based | Isolate + Select | 90%+ token reduction, fresher data |
| Stateless to Memory-augmented | Write + Select | Compounding effectiveness over time |
| Single example to Diverse multishot | Multishot examples | Edge case handling, format consistency |
| Unconstrained to Formatted | Output format + Prefill | Parseable, actionable output |

Each transformation applies techniques from [Prompt Engineering Foundations](prompt-foundations.md). For system-level patterns, see [System Prompt Design](system-prompt-design.md). For agent-specific strategies, see [Agent Context Patterns](agent-context-patterns.md).
