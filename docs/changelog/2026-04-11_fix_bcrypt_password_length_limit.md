# 2026-04-11 — Fix bcrypt password length limit error

**Version:** 0.1.0
**Type:** Fix
**Scope:** Backend

---

## Summary
Fixed a `ValueError` caused when users attempted to register or log in with passwords longer than 72 bytes, AND fixed a fatal `ValueError` crash during backend startup when importing `passlib`. The passlib `bcrypt` backend runs an internal test `detect_wrap_bug` with a long password, which crashes on `bcrypt>=4.1.0`. The issue was fixed by pinning `bcrypt==4.0.1` in `requirements.txt` and structurally truncating password inputs in `backend/auth.py` to 72 characters before they are passed to the `CryptContext` functions.

---

## Fixed
* Fixed server error on login or registration due to passwords exceeding bcrypt's 72-byte limit.

---

## Files Changed
- `backend/auth.py` (modified)
- `backend/requirements.txt` (modified)
