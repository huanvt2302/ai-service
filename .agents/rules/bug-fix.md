---
trigger: model_decision
description: Activate when the task involves fixing a bug, regression, or unexpected behavior.
---

# Bug Fix Rule

## When to use
When fixing a bug — whether reported by a user, found in a test, or discovered during development.

## Steps

### 1. Identify root cause
Before writing any fix code, document:
- What failed?
- Where in the code did it fail? (file + line)
- What was the expected behavior?
- What was the actual behavior?

### 2. Classify the bug

| Type | Examples |
|---|---|
| Logic error | Wrong condition, off-by-one, incorrect calculation |
| Data error | Missing DB constraint, wrong default value |
| Security | Auth bypass, unscoped query, token exposure |
| Performance | N+1 query, missing index, no pagination |
| Integration | vLLM timeout not handled, Redis unavailable |

### 3. Fix code
- Fix only the bug — do NOT refactor or add features in the same PR
- If the fix requires a migration → follow `database-migration.md`
- If the fix changes an API response → follow `api-change.md`

### 4. Update changelog

```markdown
## [YYYY-MM-DD]

### Fixed
* [Component]: [What was broken] — [What the fix does]
* Example: Auth: API key lookup returned 500 when key was expired — now returns 401
```

### 5. For security bugs
Security fixes require:
1. Immediate fix (do not delay)
2. Changelog entry marked with `[SECURITY]`:
   ```markdown
   ### Fixed
   * [SECURITY] Auth: Cross-team agent_messages access via unscoped contact_id query
   ```
3. Update `docs/system-design.md` if the vulnerability was in the design
4. If the bug was in `docs/agent-rules.md` governance — update rule status

### 6. Regression note
Add a short comment in the code near the fix:

```python
# Fix: contact_id queries must always be team-scoped via agents join
# See: docs/agent-rules.md Rule 4
# Previously: direct filter on agent_messages.contact_id (cross-team leak)
```