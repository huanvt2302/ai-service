"""Webhook management routes"""
import hmac
import hashlib
import json
import logging
import httpx
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from models import Webhook, User
from auth import get_current_user

logger = logging.getLogger(__name__)
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


# ── Dispatch utility ──────────────────────────────────────────────────────────

def _sign_payload(secret: str, payload: bytes) -> str:
    """Return an HMAC-SHA256 hex digest for webhook payload verification (GitHub-style)."""
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def dispatch_webhook_event(db: Session, team_id, event: str, data: dict) -> None:
    """Fire a signed POST to all active team webhooks subscribed to *event*.

    Best-effort: errors are logged but never raise. Callers should invoke this
    after the primary operation has been committed so a webhook failure doesn't
    roll back business logic.

    Args:
        db: Active SQLAlchemy session (read-only — no commit performed).
        team_id: UUID of the team whose webhooks to notify.
        event: Event name, e.g. ``"document.processed"``.
        data: Arbitrary dict included as the ``data`` field in the POST body.
    """
    from datetime import datetime, timezone

    hooks = (
        db.query(Webhook)
        .filter(
            Webhook.team_id == team_id,
            Webhook.is_active.is_(True),
        )
        .all()
    )

    if not hooks:
        return

    payload_dict = {
        "event": event,
        "team_id": str(team_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    payload_bytes = json.dumps(payload_dict, default=str).encode()

    async with httpx.AsyncClient(timeout=10) as client:
        for hook in hooks:
            subscribed_events: list = hook.events or []
            if event not in subscribed_events:
                continue

            try:
                signature = _sign_payload(hook.secret or "", payload_bytes)
                resp = await client.post(
                    hook.url,
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-NeuralAPI-Event": event,
                        "X-NeuralAPI-Signature": signature,
                    },
                )
                logger.info(
                    f"[Webhook] Dispatched '{event}' to {hook.url} "
                    f"(hook={hook.id}, status={resp.status_code})"
                )
                # Update last_triggered_at (best-effort, ignore failures)
                try:
                    hook.last_triggered_at = datetime.now(timezone.utc)
                    db.add(hook)
                    db.commit()
                except Exception:
                    db.rollback()
            except Exception as exc:
                logger.warning(
                    f"[Webhook] Failed to deliver '{event}' to {hook.url} "
                    f"(hook={hook.id}): {exc}"
                )

