"""Teams management routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Team, Subscription
from auth import get_current_user

router = APIRouter(prefix="/v1/teams", tags=["teams"])


@router.get("/current")
def get_current_team(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    team = current_user.team
    sub = db.query(Subscription).filter(Subscription.team_id == team.id).first()
    members = db.query(User).filter(User.team_id == team.id, User.is_active == True).all()

    return {
        "id": str(team.id),
        "name": team.name,
        "slug": team.slug,
        "plan": team.plan.value if hasattr(team.plan, "value") else team.plan,
        "member_count": len(members),
        "members": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value if hasattr(u.role, "value") else u.role,
                "avatar_url": u.avatar_url,
                "created_at": u.created_at.isoformat(),
            }
            for u in members
        ],
        "subscription": {
            "plan": sub.plan.value if sub and hasattr(sub.plan, "value") else (sub.plan if sub else "free"),
            "token_quota": sub.token_quota if sub else 100000,
            "tokens_used": sub.tokens_used if sub else 0,
        } if sub else None,
    }


@router.patch("/current")
def update_team(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    team = current_user.team
    if "name" in body:
        team.name = body["name"]
    db.commit()
    return {"message": "Team updated"}
