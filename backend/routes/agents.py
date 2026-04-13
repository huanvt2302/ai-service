"""Agent builder routes"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import Agent, User
from auth import get_current_user

router = APIRouter(prefix="/v1/agents", tags=["agents"])


class AgentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    personality: Optional[str] = None
    system_prompt: Optional[str] = None
    behavior_rules: Optional[str] = None
    model: str = "qwen3.5-plus"
    temperature: float = 0.7
    plugins_enabled: bool = False
    memory_enabled: bool = False


@router.get("")
def list_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agents = db.query(Agent).filter(
        Agent.team_id == current_user.team_id,
        Agent.is_active == True,
    ).order_by(Agent.created_at.desc()).all()
    return [_agent_dict(a) for a in agents]


@router.post("")
def create_agent(
    req: AgentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = Agent(
        team_id=current_user.team_id,
        **req.model_dump(),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _agent_dict(agent)


@router.get("/{agent_id}")
def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = _get_or_404(agent_id, current_user.team_id, db)
    return _agent_dict(agent)


@router.put("/{agent_id}")
def update_agent(
    agent_id: str,
    req: AgentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = _get_or_404(agent_id, current_user.team_id, db)
    for k, v in req.model_dump().items():
        setattr(agent, k, v)
    db.commit()
    db.refresh(agent)
    return _agent_dict(agent)


@router.delete("/{agent_id}")
def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = _get_or_404(agent_id, current_user.team_id, db)
    agent.is_active = False
    db.commit()
    return {"message": "Agent deleted"}


def _get_or_404(agent_id: str, team_id, db: Session) -> Agent:
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.team_id == team_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _agent_dict(a: Agent) -> dict:
    return {
        "id": str(a.id),
        "name": a.name,
        "description": a.description,
        "personality": a.personality,
        "system_prompt": a.system_prompt,
        "behavior_rules": a.behavior_rules,
        "model": a.model,
        "temperature": a.temperature,
        "plugins_enabled": a.plugins_enabled,
        "memory_enabled": a.memory_enabled,
        "is_active": a.is_active,
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat(),
    }
