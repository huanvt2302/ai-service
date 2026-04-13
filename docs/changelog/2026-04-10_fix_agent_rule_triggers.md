# 2026-04-10 — Fix Agent Rule Triggers

**Version:** 1.0.3  
**Type:** Docs  
**Scope:** Agent Rules

---

## Summary

Fixed incorrect `trigger: always_on` on all agent rules. Each rule now uses the appropriate trigger type so it only activates in the relevant context.

---

## Changed

* `.agents/rules/api-change.md` — `always_on` → `globs: ["backend/routes/**/*.py", "backend/main.py"]`
* `.agents/rules/database-migration.md` — `always_on` → `globs: ["backend/models.py", "backend/alembic/**"]`
* `.agents/rules/agent-config.md` — `always_on` → `globs: ["backend/routes/agents.py", "backend/serve/**/*.py"]`
* `.agents/rules/new-feature.md` — `always_on` → `model_decision` (agent decides based on task intent)
* `.agents/rules/bug-fix.md` — `always_on` → `model_decision` (agent decides based on task intent)
* `.agents/rules/update-document.md` — remains `always_on` (intentional — docs must always be updated)
* `.agents/rules/README.md` — updated trigger types explanation with all 3 trigger modes

---

## Trigger Types After Fix

| Rule | Trigger | Condition |
|---|---|---|
| `update-document.md` | `always_on` | Every task |
| `api-change.md` | `globs` | Route files modified |
| `database-migration.md` | `globs` | models.py or alembic/ modified |
| `agent-config.md` | `globs` | Agent logic files modified |
| `new-feature.md` | `model_decision` | Task = new feature |
| `bug-fix.md` | `model_decision` | Task = bug fix |

---

## Files Changed
- `.agents/rules/api-change.md` (modified)
- `.agents/rules/database-migration.md` (modified)
- `.agents/rules/agent-config.md` (modified)
- `.agents/rules/new-feature.md` (modified)
- `.agents/rules/bug-fix.md` (modified)
- `.agents/rules/README.md` (modified)
