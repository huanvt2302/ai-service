---
trigger:
  - globs: ["backend/models.py", "backend/alembic/**"]
---

# Database Migration Rule

## When to use
Whenever modifying `backend/models.py` — adding columns, tables, indexes, constraints, or enum values.

## Non-negotiable rules

1. **NEVER** modify an existing migration file — create a new one
2. **NEVER** rename a table without a migration + update all FK references
3. **NEVER** drop a column without first making it nullable in a prior migration
4. Every migration must be reversible — implement both `upgrade()` and `downgrade()`

## Steps

### 1. Modify the SQLAlchemy model
Edit `backend/models.py` with the new column/table/relationship.

### 2. Create a new Alembic migration

```bash
cd backend
alembic revision -m "describe_the_change"
# e.g. alembic revision -m "add_rate_limit_to_api_keys"
```

Name the file descriptively: `0002_add_rate_limit_to_api_keys.py`

### 3. Implement upgrade() and downgrade()

```python
def upgrade() -> None:
    op.add_column("api_keys", sa.Column("rate_limit", sa.Integer, server_default="100"))

def downgrade() -> None:
    op.drop_column("api_keys", "rate_limit")
```

### 4. Test the migration

```bash
alembic upgrade head    # apply
alembic downgrade -1    # revert and verify downgrade works
alembic upgrade head    # re-apply
```

### 5. Update documentation

| Doc | What to update |
|---|---|
| `docs/architecture.md` | Update table list under "Data Tier" if table added/removed |
| `docs/system-design.md` | Update access pattern table if new table |
| `docs/api-spec.md` | Update response schemas if new fields exposed in API |
| `docs/changelog/` | Create new file `YYYY-MM-DD_migration_name.md`, add to index |

### Changelog entry (new file: `docs/changelog/YYYY-MM-DD_migration_name.md`)

```markdown
# YYYY-MM-DD — Migration: describe_the_change

**Type:** Database
**Scope:** Database

### Changed
* Database: Added column `api_keys.rate_limit` (INTEGER, default: 100)
* Migration: `0002_add_rate_limit_to_api_keys.py`
* Downgrade: removes the column safely
```

## Version increment rule
| Change type | Version bump |
|---|---|
| Add nullable column | PATCH (1.0.x) |
| Add new table | MINOR (1.x.0) |
| Rename column/table | MAJOR (x.0.0) — requires migration guide |
| Drop column/table | MAJOR (x.0.0) — requires deprecation period |