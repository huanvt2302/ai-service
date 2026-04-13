# Changelog Index — NeuralAPI AI Platform

> **MANDATORY:** Every change to API, UI, database, agent logic, prompt logic, or infrastructure MUST create a new file in `docs/changelog/`.
>
> **File naming:** `docs/changelog/YYYY-MM-DD_task_info.md`  
> **Format:** See `.agents/rules/update-document.md` → Step 4

---

## How to add a changelog entry

1. Create a new file: `docs/changelog/YYYY-MM-DD_short_task_name.md`
2. Use the template below
3. Add a row to the index table on this page

### File template

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

---

## Entry Index

| Date | File | Type | Description |
|---|---|---|---|
| 2026-04-10 | [2026-04-10_initial_platform_release.md](./changelog/2026-04-10_initial_platform_release.md) | Feature | v1.0.0 — Full platform initial release |
| 2026-04-10 | [2026-04-10_governance_docs_structure.md](./changelog/2026-04-10_governance_docs_structure.md) | Docs | Governance docs + agent rules |
| 2026-04-10 | [2026-04-10_changelog_structure_migration.md](./changelog/2026-04-10_changelog_structure_migration.md) | Docs | Migrated changelog to per-task file structure |
| 2026-04-10 | [2026-04-10_fix_agent_rule_triggers.md](./changelog/2026-04-10_fix_agent_rule_triggers.md) | Docs | Fixed rule triggers: always_on → globs/model_decision |
| 2026-04-11 | [2026-04-11_fix_docker_standalone_build.md](./changelog/2026-04-11_fix_docker_standalone_build.md) | Fix | Docker frontend build: add standalone output, remove duplicate config |
| 2026-04-11 | [2026-04-11_fix_bcrypt_password_length_limit.md](./changelog/2026-04-11_fix_bcrypt_password_length_limit.md) | Fix | Fix bcrypt 72-byte password length limit ValueError |
| 2026-04-11 | [2026-04-11_global_ui_redesign.md](./changelog/2026-04-11_global_ui_redesign.md) | Refactor | Global frontend Flat Design UI rebuild |
| 2026-04-11 | [2026-04-11_dashboard_promax_redesign.md](./changelog/2026-04-11_dashboard_promax_redesign.md) | Refactor | Dashboard Data-Dense Glassmorphism redesign |
| 2026-04-11 | [2026-04-11_create_project_overview.md](./changelog/2026-04-11_create_project_overview.md) | Docs | Created project overview document |
| 2026-04-13 | [2026-04-13_hybrid_cloud_burst_architecture.md](./changelog/2026-04-13_hybrid_cloud_burst_architecture.md) | Infrastructure | Hybrid Local-First + GCP Cloud Run burst layer (Docker Swarm, Hybrid Router, Burst Controller) |

---

## Planned (Roadmap)

See [docs/roadmap.md](./roadmap.md) for upcoming feature plans.

| Target Version | Theme |
|---|---|
| v1.1.0 | Hardening — service layer, caching, team-scope enforcement |
| v1.2.0 | Intelligence — safety layer, Stripe, STT/TTS |
| v1.3.0 | Ecosystem — plugins, tool-calling, MCP |
| v2.0.0 | Enterprise — SSO, audit logs, fine-tuning |
