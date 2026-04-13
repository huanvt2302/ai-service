"""Auth routes: register, login, me"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import get_db
from models import User, Team, Subscription, PlanType
from auth import (
    hash_password, verify_password, create_access_token, get_current_user
)
import re
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    team_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def make_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "-", name.lower().strip())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:50] + "-" + str(uuid.uuid4())[:8]


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Check email uniqueness
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Validate password
    if len(req.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    # Create team
    team = Team(name=req.team_name, slug=make_slug(req.team_name))
    db.add(team)
    db.flush()

    # Create default subscription
    sub = Subscription(team_id=team.id)
    db.add(sub)

    # Create user
    user = User(
        team_id=team.id,
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id), str(team.id), user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email, User.is_active == True).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(str(user.id), str(user.team_id), user.email)
    return TokenResponse(access_token=token)


@router.get("/me")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "team_id": str(current_user.team_id),
        "team_name": current_user.team.name if current_user.team else None,
        "avatar_url": current_user.avatar_url,
    }
