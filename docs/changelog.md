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
| 2026-04-13 | [2026-04-13_infrastructure_updates.md](./changelog/2026-04-13_infrastructure_updates.md) | Infra/Fix | Hybrid Cloud Burst architecture & macOS Docker vLLM CPU fixes |
| 2026-04-13 | [2026-04-13_replace_vllm_with_ollama.md](./changelog/2026-04-13_replace_vllm_with_ollama.md) | Refactor | Replaced vLLM with Ollama Docker for macOS ARM64 stability |
| 2026-04-13 | [2026-04-13_fix_json_decode_error.md](./changelog/2026-04-13_fix_json_decode_error.md) | Fix | Fix JSONDecodeError due to unescaped control chars in payloads |
| 2026-04-13 | [2026-04-13_fix_gateway_vllm_404.md](./changelog/2026-04-13_fix_gateway_vllm_404.md) | Fix | Handle non-200 vLLM proxy response & JSON decode error |
| 2026-04-13 | [2026-04-13_update_ollama_model_qwen25_latest.md](./changelog/2026-04-13_update_ollama_model_qwen25_latest.md) | Infra | Update Ollama model from qwen2.5:3b to qwen2.5:latest (7B) |
| 2026-04-13 | [2026-04-13_update_ollama_model_qwen35_9b.md](./changelog/2026-04-13_update_ollama_model_qwen35_9b.md) | Infra | Switch Ollama to Qwen3.5 9B (official latest, 6.6GB, 256K ctx) |
| 2026-04-13 | [2026-04-13_replace_ollama_with_llamacpp.md](./changelog/2026-04-13_replace_ollama_with_llamacpp.md) | Refactor | Replace Ollama with llama.cpp server (GGUF, OpenAI-compatible, macOS ARM64) |

---

## Planned (Roadmap)

See [docs/roadmap.md](./roadmap.md) for upcoming feature plans.

| Target Version | Theme |
|---|---|
| v1.1.0 | Hardening — service layer, caching, team-scope enforcement |
| v1.2.0 | Intelligence — safety layer, Stripe, STT/TTS |
| v1.3.0 | Ecosystem — plugins, tool-calling, MCP |
| v2.0.0 | Enterprise — SSO, audit logs, fine-tuning |
