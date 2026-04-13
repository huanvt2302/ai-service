import hashlib
import secrets
import redis as redis_lib
from datetime import datetime, timezone, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User, ApiKey, ApiKeyStatus
from config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Redis client for rate limiting
_redis = None

def get_redis():
    global _redis
    if _redis is None:
        _redis = redis_lib.from_url(settings.redis_url, decode_responses=True)
    return _redis


# ── Password helpers ────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    # Fix: password truncated to 72 chars due to bcrypt 72-byte limitations
    # Previously: passwords > 72 chars caused a ValueError
    return pwd_context.hash(password[:72])

def verify_password(plain: str, hashed: str) -> bool:
    # Fix: password truncated to 72 chars due to bcrypt 72-byte limitations
    # Previously: passwords > 72 chars caused a ValueError
    return pwd_context.verify(plain[:72], hashed)


# ── API Key helpers ────────────────────────────────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, prefix, key_hash)"""
    raw = secrets.token_urlsafe(32)
    full_key = f"sk-{raw}"
    prefix = full_key[:12]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash

def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


# ── JWT helpers ────────────────────────────────────────────────────────

def create_access_token(user_id: str, team_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "team_id": team_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ── Rate limiting (Redis sliding window) ──────────────────────────────

def check_rate_limit(api_key_id: str, limit: int = 100, window_seconds: int = 60) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    r = get_redis()
    key = f"rate:{api_key_id}"
    now = datetime.now(timezone.utc).timestamp()
    window_start = now - window_seconds

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 5)
    results = pipe.execute()
    count = results[2]
    return count <= limit


# ── Auth dependencies ─────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_team_from_api_key(
    request: Request,
    db: Session = Depends(get_db),
):
    """Validates x-api-key header for external gateway calls."""
    api_key_value = request.headers.get("x-api-key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key_value:
        raise HTTPException(status_code=401, detail="API key required")

    key_hash = hash_api_key(api_key_value)
    api_key = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.status == ApiKeyStatus.active,
    ).first()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    # Check expiry
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        api_key.status = ApiKeyStatus.expired
        db.commit()
        raise HTTPException(status_code=401, detail="API key expired")

    # Rate limit check
    if not check_rate_limit(str(api_key.id)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Update last_used
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return api_key
