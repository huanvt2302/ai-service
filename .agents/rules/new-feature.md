---
trigger: model_decision
description: Activate when the task is implementing a new feature that does not yet exist in the codebase.
---

# New Feature Rule

## When to use
Whenever implementing a feature that does not exist yet in the codebase.

## Required deliverables

Every new feature MUST include all of the following before it is considered done:

| Deliverable | Required for |
|---|---|
| Implementation code | Always |
| `docs/changelog.md` entry | Always |
| Update to `docs/api-spec.md` | If API surface changes |
| Update to `docs/architecture.md` | If new service/component added |
| Update to `docs/roadmap.md` | Mark item as ✅ (was 📋) |
| Backward compatibility check | Always |

## Steps

### 1. Plan before coding
Before writing any code, answer:
- Does this break any existing API contract? (check `docs/api-spec.md`)
- Does this require a DB migration? (if yes → follow `database-migration.md` rule)
- Does this add a new service/process? (if yes → update `docs/architecture.md`)
- Does this touch agent logic? (if yes → follow `agent-config.md` rule)

### 2. Implement
- Follow `docs/coding-standards.md`
- No inline business logic in controllers
- Add typed functions
- Files must stay under 500 lines

### 3. Update changelog (mandatory)

```markdown
## [YYYY-MM-DD]

### Added
* Feature: [feature name] — [brief description]
* Files changed: [list key files]
```

### 4. Update roadmap

Open `docs/roadmap.md` and change the feature row:

```markdown
| Feature name | ✅ | Completed in v1.x.y |
```

### 5. Update relevant docs
- `docs/api-spec.md` — if new endpoints
- `docs/architecture.md` — if new components
- `docs/system-design.md` — if new scaling/caching behavior

### 6. Verify no breaking changes
- Existing endpoints must return the same schema
- Existing DB columns must not be removed or renamed
- Frontend `lib/api.ts` types must be compatible