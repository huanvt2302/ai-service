"""Webhook management routes"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from models import Webhook, User
from auth import get_current_user
import secrets

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])

VALID_EVENTS = [
    "usage.exceeded",
    "key.revoked",
    "key.created",
    "document.processed",
    "agent.created",
    "billing.updated",
]


class WebhookRequest(BaseModel):
    name: str
    url: str
    events: List[str] = []


@router.get("")
def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hooks = db.query(Webhook).filter(Webhook.team_id == current_user.team_id).order_by(Webhook.created_at.desc()).all()
    return [_wh_dict(h) for h in hooks]


@router.post("")
def create_webhook(
    req: WebhookRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate events
    invalid = [e for e in req.events if e not in VALID_EVENTS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid events: {invalid}")

    hook = Webhook(
        team_id=current_user.team_id,
        name=req.name,
        url=str(req.url),
        secret=secrets.token_urlsafe(32),
        events=req.events,
    )
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return _wh_dict(hook)


@router.delete("/{hook_id}")
def delete_webhook(
    hook_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hook = db.query(Webhook).filter(Webhook.id == hook_id, Webhook.team_id == current_user.team_id).first()
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(hook)
    db.commit()
    return {"message": "Webhook deleted"}


def _wh_dict(h: Webhook) -> dict:
    return {
        "id": str(h.id),
        "name": h.name,
        "url": h.url,
        "events": h.events,
        "is_active": h.is_active,
        "last_triggered_at": h.last_triggered_at.isoformat() if h.last_triggered_at else None,
        "created_at": h.created_at.isoformat(),
        "secret_prefix": h.secret[:8] + "..." if h.secret else None,
    }
