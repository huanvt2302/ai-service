"""Billing and quota routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Subscription, PlanType, User
from auth import get_current_user
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/v1/billing", tags=["billing"])

PLAN_LIMITS = {
    "free": {"token_quota": 100_000, "stt_quota": 60, "tts_quota": 60, "coding_quota": 50_000},
    "pro": {"token_quota": 5_000_000, "stt_quota": 600, "tts_quota": 600, "coding_quota": 2_000_000},
    "enterprise": {"token_quota": 50_000_000, "stt_quota": 6000, "tts_quota": 6000, "coding_quota": 20_000_000},
}

PLAN_PRICES = {"free": 0, "pro": 49, "enterprise": 299}


@router.get("/quota")
def get_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = db.query(Subscription).filter(Subscription.team_id == current_user.team_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {
        "plan": sub.plan.value if hasattr(sub.plan, "value") else sub.plan,
        "price_usd": PLAN_PRICES.get(sub.plan.value if hasattr(sub.plan, "value") else sub.plan, 0),
        "billing_period_start": sub.billing_period_start.isoformat() if sub.billing_period_start else None,
        "next_billing_date": sub.next_billing_date.isoformat() if sub.next_billing_date else None,
        "quotas": [
            {
                "name": "Token Usage",
                "service": "chat",
                "used": sub.tokens_used or 0,
                "limit": sub.token_quota or 0,
                "unit": "tokens",
            },
            {
                "name": "STT Minutes",
                "service": "stt",
                "used": sub.stt_used or 0,
                "limit": sub.stt_quota or 0,
                "unit": "minutes",
            },
            {
                "name": "TTS Minutes",
                "service": "tts",
                "used": sub.tts_used or 0,
                "limit": sub.tts_quota or 0,
                "unit": "minutes",
            },
            {
                "name": "Coding Tokens",
                "service": "coding",
                "used": sub.coding_used or 0,
                "limit": sub.coding_quota or 0,
                "unit": "tokens",
            },
        ],
    }


@router.post("/upgrade")
def upgrade_plan(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = body.get("plan", "pro")
    if plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    sub = db.query(Subscription).filter(Subscription.team_id == current_user.team_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    limits = PLAN_LIMITS[plan]
    sub.plan = plan
    sub.token_quota = limits["token_quota"]
    sub.stt_quota = limits["stt_quota"]
    sub.tts_quota = limits["tts_quota"]
    sub.coding_quota = limits["coding_quota"]
    sub.next_billing_date = datetime.now(timezone.utc) + timedelta(days=30)
    db.commit()

    return {"message": f"Upgraded to {plan}", "plan": plan}
