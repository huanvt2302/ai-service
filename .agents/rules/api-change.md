---
trigger:
  - globs: ["backend/routes/**/*.py", "backend/main.py"]
---

# API Change Rule

## When to use
Whenever adding, modifying, or removing any FastAPI route in `backend/routes/`.

## Steps

### 1. Classify the change type

| Change | Impact Level |
|---|---|
| Add new optional query param | Low — backward compatible |
| Add new endpoint | Low — backward compatible |
| Change request body field (required→optional) | Medium — verify clients |
| Rename endpoint or HTTP method | **High — breaking change** |
| Remove endpoint | **High — breaking change** |
| Change response schema | **High — breaking change** |

### 2. For LOW impact changes
- Add the new route
- Update `docs/api-spec.md` — add new endpoint section
   - Create a new changelog file: `docs/changelog/YYYY-MM-DD_api_change_name.md`
   - Add row to index in `docs/changelog.md`
   - Use `### Added` section

### 3. For HIGH impact (breaking) changes
Before making the change:
1. Add a deprecation notice to the OLD endpoint response:
   ```json
   { "X-Deprecated": "Use /v2/endpoint instead. Removed after 2026-06-01." }
   ```
2. Create the NEW endpoint alongside the old one
3. Update `docs/api-spec.md` with migration guide
4. Update `docs/roadmap.md` — mark old endpoint for removal
5. Bump minor version in `backend/main.py`
6.   - Create a new changelog file: `docs/changelog/YYYY-MM-DD_api_breaking_change_name.md`
   - Add row to index in `docs/changelog.md`
   - Use `### Changed` section

### 4. Update API spec
Always update `docs/api-spec.md`:
- Request body schema
- Response body schema
- Error codes
- Auth header requirement
- Example curl command

### 5. Verify backward compatibility
- Run existing routes to confirm they still return the same schema
- Check frontend `lib/api.ts` — update TypeScript types if response shape changed

## Format for api-spec.md entry

```markdown
### METHOD /v1/your-endpoint

Description of what this endpoint does.

**Auth:** JWT Bearer | x-api-key | None

**Request:**
\`\`\`json
{ "field": "value" }
\`\`\`

**Response 200:**
\`\`\`json
{ "result": "value" }
\`\`\`

**Errors:**
- `401` — Not authenticated
- `404` — Resource not found
```