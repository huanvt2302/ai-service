"""API Key management routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from models import ApiKey, ApiKeyStatus, User
from auth import get_current_user, generate_api_key
import uuid

router = APIRouter(prefix="/v1/keys", tags=["api-keys"])


class CreateKeyRequest(BaseModel):
    name: str
    expires_in_days: Optional[int] = None  # None = never expires


class KeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    status: str
    created_at: str
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None
    full_key: Optional[str] = None  # only returned on creation


@router.get("", response_model=list[KeyResponse])
def list_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    keys = db.query(ApiKey).filter(
        ApiKey.team_id == current_user.team_id,
        ApiKey.status != ApiKeyStatus.revoked,
    ).order_by(ApiKey.created_at.desc()).all()

    return [
        KeyResponse(
            id=str(k.id),
            name=k.name,
            prefix=k.prefix,
            status=k.status.value,
            created_at=k.created_at.isoformat(),
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
        )
        for k in keys
    ]


@router.post("", response_model=KeyResponse)
def create_key(
    req: CreateKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    full_key, prefix, key_hash = generate_api_key()

    expires_at = None
    if req.expires_in_days:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_in_days)

    api_key = ApiKey(
        team_id=current_user.team_id,
        user_id=current_user.id,
        name=req.name,
        prefix=prefix,
        key_hash=key_hash,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return KeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        prefix=api_key.prefix,
        status=api_key.status.value,
        created_at=api_key.created_at.isoformat(),
        expires_at=expires_at.isoformat() if expires_at else None,
        full_key=full_key,  # Only shown once
    )


@router.delete("/{key_id}")
def revoke_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.team_id == current_user.team_id,
    ).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.status = ApiKeyStatus.revoked
    db.commit()
    return {"message": "API key revoked"}
