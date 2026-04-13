# Roadmap — NeuralAPI AI Platform

**Last Updated:** 2026-04-10  
**Current Version:** 1.0.0

---

## Legend

| Symbol | Meaning |
|---|---|
| ✅ | Completed |
| 🔨 | In Progress |
| 📋 | Planned |
| ❌ | Blocked |
| 🔬 | Research phase |

---

## v1.0.0 — Foundation ✅ (Released 2026-04-10)

**Theme:** Full-stack platform scaffold with all core modules working end-to-end.

| Feature | Status |
|---|---|
| Multi-tenant architecture (team-scoped everything) | ✅ |
| JWT authentication + API key management | ✅ |
| Redis sliding-window rate limiting | ✅ |
| FastAPI gateway with SSE streaming | ✅ |
| PostgreSQL + pgvector (IVFFlat index) | ✅ |
| Alembic migrations (9 tables + enums) | ✅ |
| RQ document ingestion workers | ✅ |
| Ray Serve + vLLM deployment | ✅ |
| EmbeddingDeployment (sentence-transformers) | ✅ |
| Prometheus metrics middleware | ✅ |
| Docker Compose (8 services) | ✅ |
| Next.js 14 dark-mode console UI | ✅ |
| Dashboard (KPIs, charts, quota bars) | ✅ |
| API Keys UI | ✅ |
| Usage Analytics (4 Recharts) | ✅ |
| AI Agent Builder | ✅ |
| RAG Management (upload, chunk, search) | ✅ |
| Billing (quota meters, plan upgrade) | ✅ |
| Team Workspace | ✅ |
| Webhooks | ✅ |
| API Docs page | ✅ |
| Architecture documentation | ✅ |
| Governance rules (agent-rules, coding-standards) | ✅ |

---

## v1.1.0 — Hardening 📋 (Target: 2026-05)

**Theme:** Code quality, security, and caching improvements without breaking changes.

### Backend
| Feature | Priority | Notes |
|---|---|---|
| Extract `services/` layer | HIGH | Decouple business logic from routes |
| Extract `repositories/` layer | HIGH | Decouple DB queries from business logic |
| API key LRU cache (60s, 128 entries) | HIGH | Reduce DB hit on every API call |
| Agent system prompt protection (Rule 1) | HIGH | See `docs/agent-rules.md` Rule 1 |
| Agent memory team-scope enforcement (Rule 4) | HIGH | Fix direct `contact_id` query |
| JWT refresh tokens | MEDIUM | Reduce re-login friction |
| `agent_prompt_versions` table + migration | MEDIUM | Prompt audit trail |
| Pagination for all list endpoints | MEDIUM | Current: keys and logs paginated; rest not |

### Frontend
| Feature | Priority | Notes |
|---|---|---|
| Real-time usage update (SSE or polling) | HIGH | Dashboard auto-refresh every 30s |
| Toast notifications for actions | MEDIUM | Create key, revoke, upload success/error |
| Agent test chat pane | MEDIUM | In-browser test for agent configs |
| Webhook delivery log | LOW | Show recent webhook delivery attempts |

### Infrastructure
| Feature | Priority | Notes |
|---|---|---|
| Grafana dashboard auto-provisioning | MEDIUM | JSON dashboard via volume mount |
| Redis health check in startup | MEDIUM | Fail clearly if Redis unavailable |
| Alembic migration in CI | HIGH | Ensure migrations run before tests |

---

## v1.2.0 — Intelligence 📋 (Target: 2026-07)

**Theme:** Smarter agents, richer analytics, production billing.

### Backend
| Feature | Priority | Notes |
|---|---|---|
| Safety constraint layer (Rule 2) | HIGH | Input/output filtering for agents |
| Stripe billing integration | HIGH | Real payment processing |
| STT endpoint (Whisper API) | MEDIUM | `/v1/audio/transcriptions` |
| TTS endpoint | MEDIUM | `/v1/audio/speech` |
| Agent response logging (assistant turn) | MEDIUM | Rule 8 completion |
| PostgreSQL RLS | LOW | Defense-in-depth multi-tenancy |
| Prompt version history UI | MEDIUM | View/revert previous prompts |
| Custom rate limits per API key | MEDIUM | `api_keys.rate_limit` column |

---

## v1.3.0 — Ecosystem 📋 (Target: 2026-09)

**Theme:** Plugin ecosystem, tool calling, external integrations.

| Feature | Priority | Notes |
|---|---|---|
| Plugin sandboxing (WASM/subprocess) | HIGH | Rules 5 & 6 compliance |
| Tool-calling for agents | HIGH | Function calling support |
| External API allowlist per agent | HIGH | Rule 6 enforcement |
| MCP (Model Context Protocol) support | MEDIUM | Interop with Claude agents |
| Code interpreter plugin | MEDIUM | Sandboxed Python execution |
| Web search plugin | LOW | With domain allowlist |
| Vector DB multi-backend (Qdrant, Weaviate) | LOW | Pluggable vector store |

---

## v2.0.0 — Enterprise 🔬 (Target: 2026-Q4)

**Theme:** Enterprise-grade security, compliance, and scalability.

| Feature | Status | Notes |
|---|---|---|
| SSO / SAML support | 🔬 | Enterprise plan feature |
| Audit logging (all admin actions) | 🔬 | Compliance (SOC2) |
| Data residency controls | 🔬 | EU/US data isolation |
| Fine-tuning pipeline | 🔬 | Ray + vLLM fine-tune jobs |
| A/B testing for agent prompts | 🔬 | Split traffic by contact_id |
| Multi-region deployment | 🔬 | Caddy or Nginx geo-routing |
| GraphQL API | 🔬 | Alternative to REST for complex queries |

---

## Breaking Change Policy

- **PATCH** (1.0.x): Bug fixes only. No API changes. No schema changes.
- **MINOR** (1.x.0): New features. Backward-compatible API additions. New optional DB columns.
- **MAJOR** (x.0.0): Breaking changes. API removals/renames. Table renames with migrations. Minimum 30-day deprecation notice.

Every breaking change MUST:
1. Add deprecation warning to old endpoint (if applicable)
2. Provide migration guide in `docs/changelog.md`
3. Bump version in `backend/main.py` (`version="x.y.z"`)
4. Update `docs/api-spec.md`
