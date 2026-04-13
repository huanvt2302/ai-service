# 2026-04-10 — Changelog Structure Migration

**Version:** 1.0.2  
**Type:** Documentation  
**Scope:** Changelog, Docs, Agent Rules

---

## Summary

Migrated `docs/changelog.md` (single file) to `docs/changelog/YYYY-MM-DD_task_info.md` (per-task files). Updated all agent rules and the index file to reflect the new structure.

---

## Changed

* Changelog structure: `docs/changelog.md` (monolithic) → `docs/changelog/YYYY-MM-DD_task_info.md` (per-task files)
* `docs/changelog.md` is now an index file pointing to all entries in `docs/changelog/`
* `.agents/rules/update-document.md` — updated changelog append instructions to use new folder structure
* `.agents/rules/api-change.md` — updated changelog reference
* `.agents/rules/database-migration.md` — updated changelog reference
* `.agents/rules/agent-config.md` — updated changelog reference
* `.agents/rules/new-feature.md` — updated changelog reference
* `.agents/rules/bug-fix.md` — updated changelog reference
* `scripts/check_changelog.py` — updated tracked path to `docs/changelog/`

## Added

* `docs/changelog/2026-04-10_initial_platform_release.md` — v1.0.0 release entry
* `docs/changelog/2026-04-10_governance_docs_structure.md` — governance docs entry
* `docs/changelog/2026-04-10_changelog_structure_migration.md` — this file

---

## Migration Guide

**Old format** (single file):
```
docs/changelog.md
```

**New format** (per-task files):
```
docs/changelog/
  YYYY-MM-DD_task_name.md
```

**Naming convention:**
- Date: `YYYY-MM-DD` (UTC+7 local date)
- Task name: `snake_case`, short, descriptive
- Example: `2026-04-10_add_stripe_billing.md`

**File template:** See `.agents/rules/update-document.md` → Step 4.

---

## Files Changed
- `docs/changelog.md` (converted to index)
- `docs/changelog/2026-04-10_initial_platform_release.md` (new)
- `docs/changelog/2026-04-10_governance_docs_structure.md` (new)
- `docs/changelog/2026-04-10_changelog_structure_migration.md` (this file)
- `.agents/rules/*.md` (updated references)
- `scripts/check_changelog.py` (updated tracked path)
