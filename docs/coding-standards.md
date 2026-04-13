# Coding Standards — NeuralAPI AI Platform

**Version:** 1.0.0  
**Last Updated:** 2026-04-10  
**Scope:** All code in `backend/` and `frontend/`

---

## 1. Typed Functions

### Backend (Python)

All functions must use type hints for parameters AND return values.

```python
# ✅ CORRECT
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def get_quota(team_id: UUID, db: Session) -> Subscription | None:
    return db.query(Subscription).filter(Subscription.team_id == team_id).first()

# ❌ WRONG
def hash_password(password):
    return pwd_context.hash(password)
```

Pydantic models must be used for all request and response schemas:

```python
# ✅ CORRECT
class CreateKeyRequest(BaseModel):
    name: str
    expires_in_days: Optional[int] = None

class KeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    status: str

# ❌ WRONG — returning raw dicts from route handlers without schema
@router.post("/v1/keys")
def create_key(body: dict, ...):  # WRONG: untyped body
    return {"id": "...", "name": body["name"]}
```

### Frontend (TypeScript)

All functions must have explicit return types. Avoid `any` except when interfacing with untyped external APIs.

```typescript
// ✅ CORRECT
export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  return n.toLocaleString()
}

async function fetchUsageSummary(days: number): Promise<UsageSummary> {
  return request<UsageSummary>(`/v1/usage/summary?days=${days}`)
}

// ❌ WRONG
function formatNumber(n) {
  return n.toLocaleString()
}
```

---

## 2. No Inline Business Logic in Controllers

Route handlers (controllers) must be thin. Business logic belongs in service functions.

```python
# ✅ CORRECT — route delegates to service
@router.post("/v1/billing/upgrade")
def upgrade_plan(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return billing_service.upgrade(current_user.team_id, body.get("plan"), db)

# ❌ WRONG — route contains business logic
@router.post("/v1/billing/upgrade")
def upgrade_plan(...):
    plan = body.get("plan")
    if plan not in ["free", "pro", "enterprise"]:
        raise HTTPException(...)
    sub = db.query(Subscription).filter(...).first()
    sub.token_quota = PLAN_LIMITS[plan]["token_quota"]
    ...
    # 40 more lines of business logic inline
```

**Rule:** A route handler should contain at most:
1. Input extraction
2. Auth/permission check
3. One service call
4. Return statement

---

## 3. Service Layer Required

Complex operations require a dedicated service function in `backend/services/`:

| When | Where to put it |
|---|---|
| Multiple DB operations in sequence | `services/` module |
| Business rule (quota check + log + increment) | `services/billing_service.py` |
| Cross-table operations | `services/` module |
| Reused logic across routes | `services/` module |

```
backend/
  services/
    billing_service.py    ← upgrade(), check_quota(), reset_period()
    usage_service.py      ← log_usage(), get_summary()
    rag_service.py        ← chunk_text(), generate_embeddings(), store_chunks()
    auth_service.py       ← create_team_with_user(), validate_api_key()
```

> **Note:** The current codebase has service logic inside route files. Extraction into `services/` is required before adding any new complex feature.

---

## 4. Repository Pattern for DB Access

Database access must go through well-defined functions, not inline query chains scattered across routes.

```python
# ✅ CORRECT — query encapsulated
def get_api_key_by_hash(key_hash: str, db: Session) -> ApiKey | None:
    return db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.status == ApiKeyStatus.active,
    ).first()

# ❌ WRONG — raw query inline in route handler
api_key = db.query(ApiKey).filter(
    ApiKey.key_hash == key_hash,
    ApiKey.status == ApiKeyStatus.active
).first()
```

Planned: Add `backend/repositories/` package with one file per model.

---

## 5. Consistent Naming Conventions

### Python (Backend)

| Concept | Convention | Example |
|---|---|---|
| Files | `snake_case.py` | `billing_service.py` |
| Classes | `PascalCase` | `ApiKey`, `UsageLog` |
| Functions | `snake_case` | `get_current_user()` |
| Variables | `snake_case` | `team_id`, `expires_at` |
| Constants | `UPPER_SNAKE_CASE` | `JWT_ALGORITHM`, `PLAN_LIMITS` |
| Pydantic models | `PascalCase` + suffix | `CreateKeyRequest`, `KeyResponse` |
| DB table names | `snake_case`, plural | `api_keys`, `usage_logs` |
| DB columns | `snake_case` | `team_id`, `created_at` |

### TypeScript (Frontend)

| Concept | Convention | Example |
|---|---|---|
| Files | `kebab-case.tsx` | `auth-context.tsx` |
| Components | `PascalCase` | `Sidebar`, `DashboardLayout` |
| Hooks | `use` prefix | `useAuth()`, `useBilling()` |
| API functions | camelCase verb | `fetchUsage()`, `createKey()` |
| Types/Interfaces | `PascalCase` | `UsageSummary`, `ApiKey` |
| Constants | `UPPER_SNAKE_CASE` | `API_URL`, `PLAN_LIMITS` |
| CSS classes | Tailwind utilities (lowercase) | `text-sm`, `bg-card` |

---

## 6. Avoid Large Files (> 500 Lines)

Files exceeding 500 lines must be split. This is mandatory, not advisory.

**Current violations (to be fixed):**
- `backend/routes/gateway.py` — acceptable at ~200 lines
- `frontend/app/(dashboard)/usage/page.tsx` — monitor size

**How to split:**
- Extract helper functions to `utils.py` / `utils.ts`
- Extract DB operations to `repositories/`
- Extract business logic to `services/`
- Extract large React components into sub-components in `components/`

**Warning threshold:** 400 lines. At 400+, add a `TODO: split this file` comment.  
**Hard limit:** 500 lines. Must be split before merging.

---

## 7. Comments for Complex Logic

Complex algorithmic or business logic must have an explanatory comment. This includes:

- Redis sliding-window implementation
- pgvector cosine similarity queries
- JWT payload construction
- Quota enforcement logic
- RQ job error handling

```python
# ✅ CORRECT — complex Redis logic explained
def check_rate_limit(api_key_id: str, limit: int = 100, window_seconds: int = 60) -> bool:
    """
    Sliding window rate limiter using Redis sorted set.
    
    We use the timestamp as both the score and value.
    1. Remove all timestamps older than (now - window) → ZREMRANGEBYSCORE
    2. Add current timestamp → ZADD
    3. Count requests in window → ZCARD
    4. Allow if count <= limit
    
    This is O(log N + M) where M = removed entries.
    Atomic via Redis pipeline.
    """
    r = get_redis()
    now = datetime.now(timezone.utc).timestamp()
    ...

# ❌ WRONG — uncommented complex logic
def check_rate_limit(api_key_id: str) -> bool:
    r = get_redis()
    now = datetime.now(timezone.utc).timestamp()
    pipe = r.pipeline()
    pipe.zremrangebyscore(...)
    pipe.zadd(...)
    pipe.zcard(...)
    pipe.expire(...)
    results = pipe.execute()
    return results[2] <= 100
```

---

## 8. Additional Rules

### Environment Variables
- Never hardcode secrets, URLs, or credentials
- All config via `config.py` (backend) or `process.env` (frontend)
- All env vars must be documented in `.env.example`

### Error Handling
- Never swallow exceptions silently
- Always log the exception with `print(f"[context] {e}")` at minimum
- FastAPI route handlers should raise `HTTPException` — not return error dicts

### Database Migrations
- Every schema change requires a new Alembic migration file
- Migration files are numbered sequentially: `0001_initial.py`, `0002_add_index.py`
- Never modify existing migration files — create a new one
- Run `alembic upgrade head` in CI before tests

### Imports
- No circular imports
- Group imports: stdlib → third-party → local, separated by blank lines
- Use explicit imports (no wildcard `from module import *`)

### Git Hygiene
- Commits follow: `<type>(<scope>): <message>`  
  Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`  
  Example: `feat(rag): add collection search endpoint`
- Every PR must update `docs/changelog.md`
- Branch naming: `feature/`, `fix/`, `docs/`, `refactor/`
