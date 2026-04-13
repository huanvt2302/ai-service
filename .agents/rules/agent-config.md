---
trigger:
  - globs: ["backend/routes/agents.py", "backend/serve/**/*.py"]
---

# Agent Config Rule

## When to use
Whenever creating, modifying, or deleting an agent configuration or its execution logic.

## Rules (references docs/agent-rules.md)

| # | Rule | Status |
|---|---|---|
| 1 | Agent must NOT override system prompt | ⚠️ enforce in code |
| 2 | Agent must respect safety constraints | ❌ planned v1.2 |
| 3 | Agent config must be deterministic | ✅ enforced |
| 4 | Agent memory must be scoped per team | ⚠️ add join |
| 5 | Plugin execution must be sandboxed | ❌ planned v1.3 |
| 6 | No external APIs without permission | ❌ planned v1.3 |
| 7 | Prompt must be versioned | ⚠️ partial |
| 8 | Responses must be logged | ✅ enforced |
| 9 | Must support streaming | ✅ enforced |
| 10 | Updates must create changelog entry | ✅ this rule |

## Steps when modifying agent logic

### 1. Check which rule is impacted

- Modifying `system_prompt` handling → verify Rule 1 not violated
- Modifying memory query → verify Rule 4 (team scope) is maintained
- Enabling plugins → Rule 5 & 6 must be considered
- Any config change → Rule 10 (changelog) is mandatory

### 2. Validate determinism (Rule 3)
Agent fields that affect output must be validated:

```python
# temperature: must be float in [0.0, 2.0]
assert 0.0 <= agent.temperature <= 2.0

# model: must exist in /v1/models
valid_models = ["qwen3.5-plus", "text-embedding-3-small"]
assert agent.model in valid_models
```

### 3. System prompt injection order (Rule 1)
When building the messages array for the LLM call:

```python
# CORRECT — agent system prompt always first
messages = [{"role": "system", "content": agent.system_prompt}]
messages += caller_messages  # caller messages appended AFTER

# WRONG — do not allow caller to override
messages = caller_messages  # VIOLATION
```

### 4. Memory scope enforcement (Rule 4)
Always query `agent_messages` through the `agents` table:

```python
# CORRECT
msgs = db.query(AgentMessage)\
    .join(Agent)\
    .filter(Agent.team_id == current_team_id)\
    .filter(AgentMessage.contact_id == contact_id)\
    .all()

# WRONG — no team scope check
msgs = db.query(AgentMessage).filter(AgentMessage.contact_id == contact_id).all()
```

### 5. Log the change (Rule 10)
Every agent config update must create a new file `docs/changelog/YYYY-MM-DD_agent_change_name.md` and add a row to `docs/changelog.md` index:

```markdown
# YYYY-MM-DD — Agent: describe_change

**Type:** Agent  
**Scope:** Agent

---

## Changed
* Agent logic: [describe what changed]
* Agent Rule [N] impact: [describe how rules are affected]
```

### 6. Update agent-rules.md if rule status changes
If an implementation brings a rule from ❌ to ⚠️ or ✅, update the
governance table in `docs/agent-rules.md` and `docs/changelog.md`.