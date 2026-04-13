# Agent Rules — NeuralAPI AI Platform

This folder contains **agent governance rules** for the NeuralAPI project.
Rules tell AI agents and engineers exactly what to do (and verify) in each situation.

---

## Rules Index

| File | Trigger Type | Trigger Condition | Purpose |
|---|---|---|---|
| `update-document.md` | `always_on` | Every task, no exceptions | Update `docs/` after every task |
| `api-change.md` | `globs` | `backend/routes/**/*.py`, `backend/main.py` | Backward-compatible API changes |
| `database-migration.md` | `globs` | `backend/models.py`, `backend/alembic/**` | Safe Alembic migrations |
| `agent-config.md` | `globs` | `backend/routes/agents.py`, `backend/serve/**/*.py` | Agent governance (10 rules) |
| `new-feature.md` | `model_decision` | When task is adding a new feature | Required deliverables checklist |
| `bug-fix.md` | `model_decision` | When task is fixing a bug/regression | Bug classification + changelog |

---

## Trigger Types Explained

### `always_on`
Fires on **every task**, regardless of what files are being changed.

```yaml
---
trigger: always_on
---
```

**Used by:** `update-document.md` — documentation must always be updated.

---

### `globs`
Fires **only when specific files are modified**. Uses glob patterns to match file paths.

```yaml
---
trigger:
  - globs: ["backend/routes/**/*.py", "backend/main.py"]
---
```

**Used by:**
- `api-change.md` → triggers when any route file changes
- `database-migration.md` → triggers when `models.py` or alembic files change
- `agent-config.md` → triggers when agent logic files change

---

### `model_decision`
Fires when the **AI agent determines** the current task matches the rule's intent. Requires the agent to read the `description` field and decide.

```yaml
---
trigger: model_decision
description: Activate when the task is implementing a new feature that does not yet exist in the codebase.
---
```

**Used by:**
- `new-feature.md` → model decides if this is a new feature
- `bug-fix.md` → model decides if this is a bug fix

---

## The Non-Negotiable Chain

The `always_on` rule (`update-document.md`) enforces this chain **after every task**:

```
Implement → Update spec → Update architecture (if needed) → Create changelog file → Add to index
```

---

## Adding New Rules

1. Create a new `.md` file in this folder
2. Add frontmatter with the appropriate `trigger` type:
   ```yaml
   ---
   trigger: always_on
   # OR
   trigger:
     - globs: ["path/to/files/**"]
   # OR
   trigger: model_decision
   description: When to apply this rule.
   ---
   ```
3. Use the standard rule structure:
   - **When to use** — clear condition
   - **Steps** — ordered, actionable
   - **Enforcement** — what blocks progress
4. Add the rule to the index table in this file
5. Create changelog entry: `docs/changelog/YYYY-MM-DD_add_rule_name.md`
6. Add to index in `docs/changelog.md`

---

## Relationship to /docs

| `.agents/rules/` | `docs/` |
|---|---|
| HOW to do tasks correctly | WHAT the system looks like |
| Instructions for agents/engineers | Reference documentation |
| Enforces the update workflow | Gets updated BY the workflow |

Rules in `.agents/rules/` **point to** docs in `docs/`.  
Docs in `docs/` are the **output** of following those rules.
