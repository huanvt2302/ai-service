"""Usage analytics routes"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timezone, timedelta
from database import get_db
from models import UsageLog, User, Subscription
from auth import get_current_user
from typing import Optional

router = APIRouter(prefix="/v1/usage", tags=["usage"])


@router.get("/summary")
def usage_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    team_id = current_user.team_id

    # Total tokens
    totals = db.query(
        func.coalesce(func.sum(UsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(UsageLog.input_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(UsageLog.output_tokens), 0).label("output_tokens"),
        func.count(UsageLog.id).label("total_requests"),
        func.avg(UsageLog.latency_ms).label("avg_latency_ms"),
    ).filter(
        UsageLog.team_id == team_id,
        UsageLog.created_at >= since,
    ).first()

    # Success rate
    success = db.query(func.count(UsageLog.id)).filter(
        UsageLog.team_id == team_id,
        UsageLog.created_at >= since,
        UsageLog.status_code.between(200, 299),
    ).scalar() or 0

    total_req = totals.total_requests or 1
    success_rate = round((success / total_req) * 100, 1)

    # Daily breakdown
    daily = db.query(
        cast(UsageLog.created_at, Date).label("date"),
        func.count(UsageLog.id).label("requests"),
        func.coalesce(func.sum(UsageLog.total_tokens), 0).label("tokens"),
        func.avg(UsageLog.latency_ms).label("avg_latency"),
    ).filter(
        UsageLog.team_id == team_id,
        UsageLog.created_at >= since,
    ).group_by("date").order_by("date").all()

    # By service
    by_service = db.query(
        UsageLog.service,
        func.count(UsageLog.id).label("requests"),
        func.coalesce(func.sum(UsageLog.total_tokens), 0).label("tokens"),
    ).filter(
        UsageLog.team_id == team_id,
        UsageLog.created_at >= since,
    ).group_by(UsageLog.service).all()

    # Subscription / quota
    sub = db.query(Subscription).filter(Subscription.team_id == team_id).first()

    return {
        "summary": {
            "total_tokens": int(totals.total_tokens),
            "input_tokens": int(totals.input_tokens),
            "output_tokens": int(totals.output_tokens),
            "total_requests": int(totals.total_requests),
            "avg_latency_ms": round(float(totals.avg_latency_ms or 0), 2),
            "success_rate": success_rate,
        },
        "quota": {
            "token_quota": sub.token_quota if sub else 100000,
            "tokens_used": sub.tokens_used if sub else 0,
            "stt_quota": sub.stt_quota if sub else 60,
            "stt_used": sub.stt_used if sub else 0,
            "tts_quota": sub.tts_quota if sub else 60,
            "tts_used": sub.tts_used if sub else 0,
            "coding_quota": sub.coding_quota if sub else 50000,
            "coding_used": sub.coding_used if sub else 0,
        } if sub else None,
        "daily": [
            {
                "date": str(r.date),
                "requests": int(r.requests),
                "tokens": int(r.tokens),
                "avg_latency": round(float(r.avg_latency or 0), 2),
            }
            for r in daily
        ],
        "by_service": [
            {
                "service": r.service.value if hasattr(r.service, "value") else r.service,
                "requests": int(r.requests),
                "tokens": int(r.tokens),
            }
            for r in by_service
        ],
    }


@router.get("/logs")
def usage_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    service: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(UsageLog).filter(UsageLog.team_id == current_user.team_id)
    if service:
        q = q.filter(UsageLog.service == service)

    total = q.count()
    logs = q.order_by(UsageLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": str(l.id),
                "service": l.service.value if hasattr(l.service, "value") else l.service,
                "model": l.model,
                "input_tokens": l.input_tokens,
                "output_tokens": l.output_tokens,
                "total_tokens": l.total_tokens,
                "latency_ms": l.latency_ms,
                "status_code": l.status_code,
                "endpoint": l.endpoint,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ],
    }
