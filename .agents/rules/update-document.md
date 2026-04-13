---
trigger: always_on
---

# Update Docs Skill

## When to use
After **every** task completion that modifies:
- API routes (`backend/routes/`)
- Database models (`backend/models.py`, `backend/alembic/`)
- Frontend pages or components (`frontend/app/`, `frontend/components/`)
- Agent logic (`backend/routes/agents.py`, `backend/serve/`)
- Worker logic (`backend/workers/`)
- Infrastructure (`docker-compose.yml`, `monitoring/`)

## Steps

### 1. Scan code changes
Identify which files were modified and classify the domain:
`api` | `database` | `ui` | `agent` | `infrastructure` | `worker`

### 2. Detect domain impacted

| Domain | Docs to update |
|---|---|
| API route added/changed | `docs/api-spec.md`, `docs/changelog/` |
| Database schema changed | `docs/architecture.md`, `docs/changelog/` |
| Agent logic changed | `docs/agent-rules.md`, `docs/changelog/` |
| Architecture changed | `docs/architecture.md`, `docs/system-design.md`, `docs/changelog/` |
| UI page added/modified | `docs/changelog/` |
| Infrastructure changed | `docs/architecture.md`, `docs/changelog/` |

### 3. Update docs file
- Edit the relevant doc in `docs/`
- Do NOT remove existing sections unless explicitly deprecated
- Match the formatting style of the existing document

### 4. Create a new changelog file

**Path:** `docs/changelog/YYYY-MM-DD_task_name.md`

**Naming rules:**
- `YYYY-MM-DD` — today's date (local time)
- `task_name` — `snake_case`, short, descriptive (e.g. `add_stripe_billing`, `fix_auth_rate_limit`)

**Template:**
```markdown
# YYYY-MM-DD — Task Title

**Version:** X.Y.Z  
**Type:** Feature | Fix | Docs | Refactor | Security | Infrastructure  
**Scope:** Backend | Frontend | Database | Agent | Infrastructure | Docs

---

## Summary
One paragraph describing what changed and why.

---

## Added
* item

## Changed
* item

## Fixed
* item

## Removed
* item

---

## Files Changed
- `path/to/file.py` (new | modified | deleted)
```

### 5. Add entry to index

Open `docs/changelog.md` and add a row to the **Entry Index** table:

```markdown
| YYYY-MM-DD | [YYYY-MM-DD_task_name.md](./changelog/YYYY-MM-DD_task_name.md) | Type | Short description |
```

### 6. Ensure docs consistency
- Verify `docs/api-spec.md` matches actual route signatures
- Verify `docs/architecture.md` diagram reflects current service list
- Verify `docs/roadmap.md` status icons (✅/📋/❌) are current
- If any doc is stale, update it in the same task

## Enforcement
This rule is mandatory. A task is **NOT complete** until a file is created in `docs/changelog/` and indexed in `docs/changelog.md`.