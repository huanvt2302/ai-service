# 2026-04-11 — Fix Docker Frontend Standalone Build

**Version:** 1.0.1  
**Type:** Fix  
**Scope:** Frontend | Infrastructure

---

## Summary
The Docker multi-stage build for the `frontend` service was failing because the Dockerfile expects a Next.js standalone output at `/app/.next/standalone`, but `output: 'standalone'` was never set in the Next.js configuration. Additionally, two conflicting config files (`next.config.js` and `next.config.mjs`) coexisted — Next.js would silently prefer the `.mjs` file in newer versions, causing `next.config.js` settings (env vars, image domains) to be ignored. Both issues are now resolved.

---

## Fixed
* Docker build failure: `"/app/.next/standalone": not found` — caused by missing `output: 'standalone'` in Next.js config
* Docker build failure: `"/app/public": not found` — `public/` directory did not exist in the source tree
* Duplicate/conflicting Next.js config files (`next.config.js` vs `next.config.mjs`)

## Changed
* `frontend/next.config.js` — added `output: 'standalone'` to enable standalone server bundle generation required by the Dockerfile runner stage
* `frontend/Dockerfile` — added `RUN mkdir -p ./public` before the `COPY public/` step so builds succeed even when `public/` is empty

## Added
* `frontend/public/.gitkeep` — ensures the `public/` directory is tracked in git and always present during Docker build

## Removed
* `frontend/next.config.mjs` — redundant empty config file removed to prevent override of `next.config.js`

---

## Files Changed
- `frontend/next.config.js` (modified)
- `frontend/next.config.mjs` (deleted)
- `frontend/Dockerfile` (modified)
- `frontend/public/.gitkeep` (new)
