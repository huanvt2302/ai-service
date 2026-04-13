# Agent Rules — NeuralAPI AI Platform

**Version:** 1.0.0  
**Last Updated:** 2026-04-10  
**Status:** Enforced  
**Scope:** All AI agents created via `/v1/agents` and executed via `/v1/chat/completions` or `/v1/memchat/completions`

---

## Overview

These rules govern the creation, configuration, execution, and lifecycle of AI agents on the NeuralAPI platform. Violations of these rules are considered architecture-level defects and must be fixed before merging.

---

## Rule 1 — Agent Must Not Override System Prompt

**Rule:** An agent's `system_prompt` field is set at configuration time by the team owner. Runtime callers (`/v1/chat/completions`, `/v1/memchat/completions`) MUST NOT be permitted to override or prepend additional system-level instructions that contradict the agent config.

**Implementation:**
- Gateway must inject the agent's `system_prompt` as the first `system` message before all others
- Any `system` role messages from the caller are appended AFTER the agent's system prompt, not before
- The agent system prompt is stored in `agents.system_prompt` and is versioned

**Enforcement:**
```python
# Correct order in gateway:
messages = [{"role": "system", "content": agent.system_prompt}] + caller_messages
```

**Violation example (NOT allowed):**
```python
# WRONG — caller's system overrides agent config
messages = caller_messages  # May contain conflicting system prompt
```

---

## Rule 2 — Agent Must Respect Safety Constraints

**Rule:** Every agent execution must pass through a safety pre-check layer before sending to LLM.

**Current implementation:** Not yet enforced at code level (planned v1.2).

**Required behavior (for v1.2):**
- Input must be checked against a blocklist of disallowed patterns (PII, illegal content requests)
- Output must be post-processed to remove accidental PII leakage
- Safety check failures must be logged with `status_code=400` in `usage_logs`
- The LLM must never be called with blocked inputs

**Configuration:**
```python
class Agent(Base):
    safety_level: str  # "none" | "basic" | "strict"  # planned field
```

---

## Rule 3 — Agent Config Must Be Deterministic

**Rule:** The following agent fields MUST produce deterministic behavior when set:
- `temperature` — must be stored as float, range `[0.0, 2.0]`
- `model` — must be a string matching an entry in GET /v1/models
- `system_prompt` — must be a versioned, immutable string (versioning: Rule 7)

**Enforcement:**
- `temperature` is validated at creation time (FastAPI pydantic model)
- `model` defaults to `settings.default_chat_model` if not specified
- Changing `system_prompt` creates a new version (Rule 7)

**Tests required:** Any change to agent execution logic must include a test asserting identical output for identical inputs when `temperature=0.0`.

---

## Rule 4 — Agent Memory Must Be Scoped Per Team

**Rule:** Agent conversation history (`agent_messages`) must NEVER be shared across teams.

**Implementation:**
- `agent_messages.agent_id` → `agents.id` → `agents.team_id`
- All memory queries filter by `agent_id` which is inherently team-scoped
- `contact_id` is a free-form UUID but is only queryable within the team's agents

**Verification:**
```sql
-- Every agent_messages query MUST join through agents to enforce team scope:
SELECT am.* FROM agent_messages am
JOIN agents a ON a.id = am.agent_id
WHERE a.team_id = $team_id AND am.contact_id = $contact_id
```

**Violation pattern (NOT allowed):**
```python
# WRONG — queries agent_messages by contact_id without team scoping
db.query(AgentMessage).filter(AgentMessage.contact_id == contact_id)
```

---

## Rule 5 — Agent Plugin Execution Must Be Sandboxed

**Rule:** When `plugins_enabled = true`, plugin code must execute in an isolated subprocess or sandbox environment with:
- No network access (unless explicitly allowed by team admin)
- No filesystem access outside a designated `/sandbox/` directory
- CPU and memory limits enforced
- Execution timeout: 10 seconds maximum

**Current implementation:** Plugin execution is not yet implemented (planned v1.3).

**Planned enforcement:**
- Use Python `subprocess` with restricted environment variables
- Or use a WASM-based sandbox (e.g., wasmtime)
- Plugin results must be logged in `usage_logs` with `service="plugin"`

---

## Rule 6 — Agent Cannot Call External APIs Without Permission

**Rule:** Agents with `plugins_enabled = false` (default) MUST NOT make outbound HTTP requests.

When `plugins_enabled = true`:
- Only pre-approved external domains may be called
- Domain allowlist stored in `agents.allowed_domains` (planned JSON field)
- All external calls are logged
- External calls consuming tokens are charged to the team's quota

**Current implementation:** Not enforced at runtime (planned v1.3). Agents currently only generate text — no tool-calling is implemented.

---

## Rule 7 — Agent Prompt Must Be Versioned

**Rule:** Every change to `agents.system_prompt` must:
1. Increment `agents.prompt_version` (planned field, currently implicit via `updated_at`)
2. Log the previous prompt value to a `agent_prompt_versions` table (planned v1.2)
3. Include a changelog entry if the change affects behavior

**Interim implementation (current):**
- `agents.updated_at` is auto-updated on PUT
- Full audit trail is not yet implemented
- Until `agent_prompt_versions` is created, engineers MUST document prompt changes in `docs/changelog.md`

**Planned schema:**
```sql
CREATE TABLE agent_prompt_versions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
  version INT NOT NULL,
  system_prompt TEXT NOT NULL,
  changed_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Rule 8 — Agent Responses Must Be Logged

**Rule:** Every agent execution (chat or memchat) must produce a `usage_logs` row with:
- `service = "chat"`
- `model` = model used
- `input_tokens` and `output_tokens`
- `latency_ms`
- `status_code` (HTTP status of the LLM response)
- `endpoint` = `/v1/chat/completions` or `/v1/memchat/completions`

**Memory chat additionally logs:**
- The user message to `agent_messages` before calling LLM
- The assistant response to `agent_messages` after receiving LLM output (planned v1.2 — currently only user message is saved)

**Enforcement:** `log_usage()` is called in `routes/gateway.py` in both streaming and non-streaming paths.

---

## Rule 9 — Agent Must Support Streaming

**Rule:** All agents must support both `stream: true` and `stream: false` modes.

**Implementation:**
- `POST /v1/chat/completions` checks `body.get("stream", False)`
- Streaming path: `StreamingResponse` with `text/event-stream` content type
- Non-streaming path: returns full JSON response
- Both paths call `log_usage()` on completion

**Agent configs do NOT control streaming** — the caller decides per-request.

---

## Rule 10 — Agent Updates Must Create Changelog Entry

**Rule:** Any modification to an existing agent's configuration — including `system_prompt`, `personality`, `behavior_rules`, `model`, `temperature`, or toggle fields — MUST be accompanied by an entry in `docs/changelog.md`.

**Format:**
```markdown
## [YYYY-MM-DD]

### Changed
* Agent "{name}" (id: {uuid}): Updated system_prompt — previous behavior: ..., new behavior: ...
```

**Enforcement:** This rule is enforced by code review policy. PRs that modify agent logic without a changelog update will be rejected.

---

## Governance Summary

| Rule | Status | Version Target |
|---|---|---|
| 1 — No system prompt override | ⚠️ Partial (logic present, not tested) | v1.1 |
| 2 — Safety constraints | ❌ Not implemented | v1.2 |
| 3 — Deterministic config | ✅ Implemented | v1.0 |
| 4 — Memory team scoping | ⚠️ Partial (join needed) | v1.1 |
| 5 — Plugin sandboxing | ❌ Not implemented | v1.3 |
| 6 — No unauthorized external APIs | ❌ Not implemented | v1.3 |
| 7 — Prompt versioning | ⚠️ Partial (updated_at only) | v1.2 |
| 8 — Response logging | ✅ Implemented | v1.0 |
| 9 — Streaming support | ✅ Implemented | v1.0 |
| 10 — Changelog on update | ✅ Policy enforced | v1.0 |
