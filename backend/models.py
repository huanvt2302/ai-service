from sqlalchemy import (
    Column, String, Boolean, Integer, BigInteger, Float, Text,
    DateTime, ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid
import enum
from datetime import datetime, timezone

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


# ── Enums ─────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"

class ApiKeyStatus(str, enum.Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"

class DocStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"

class PlanType(str, enum.Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"

class ServiceType(str, enum.Enum):
    chat = "chat"
    embeddings = "embeddings"
    stt = "stt"
    tts = "tts"
    coding = "coding"


# ── Models ────────────────────────────────────────────────────────────────

class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(SAEnum(PlanType), default=PlanType.free, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    users = relationship("User", back_populates="team", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="team", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="team", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="team", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="team", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="team", uselist=False)
    webhooks = relationship("Webhook", back_populates="team", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SAEnum(UserRole), default=UserRole.member, nullable=False)
    avatar_url = Column(String(512))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    team = relationship("Team", back_populates="users")
    api_keys = relationship("ApiKey", back_populates="user")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    prefix = Column(String(20), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    status = Column(SAEnum(ApiKeyStatus), default=ApiKeyStatus.active, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    team = relationship("Team", back_populates="api_keys")
    user = relationship("User", back_populates="api_keys")
    usage_logs = relationship("UsageLog", back_populates="api_key")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    service = Column(SAEnum(ServiceType), nullable=False)
    model = Column(String(100))
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Float)
    status_code = Column(Integer)
    error_message = Column(Text)
    endpoint = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    team = relationship("Team", back_populates="usage_logs")
    api_key = relationship("ApiKey", back_populates="usage_logs")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    personality = Column(Text)
    system_prompt = Column(Text)
    behavior_rules = Column(Text)
    model = Column(String(100), default="qwen3.5-plus")
    temperature = Column(Float, default=0.7)
    plugins_enabled = Column(Boolean, default=False)
    memory_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    team = relationship("Team", back_populates="agents")
    messages = relationship("AgentMessage", back_populates="agent", cascade="all, delete-orphan")


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    role = Column(String(20), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    agent = relationship("Agent", back_populates="messages")


class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    doc_count = Column(Integer, default=0)
    embedding_model = Column(String(100), default="text-embedding-3-small")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    team = relationship("Team", back_populates="collections")
    documents = relationship("Document", back_populates="collection", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(512), nullable=False)
    file_path = Column(String(512))
    file_size = Column(BigInteger, default=0)
    mime_type = Column(String(100))
    chunk_count = Column(Integer, default=0)
    status = Column(SAEnum(DocStatus), default=DocStatus.pending, nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    collection = relationship("Collection", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    metadata_ = Column("metadata", JSON, default={})
    created_at = Column(DateTime(timezone=True), default=utcnow)

    document = relationship("Document", back_populates="chunks")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan = Column(SAEnum(PlanType), default=PlanType.free, nullable=False)

    # Quotas
    token_quota = Column(BigInteger, default=100_000)
    stt_quota = Column(Integer, default=60)         # minutes
    tts_quota = Column(Integer, default=60)         # minutes
    coding_quota = Column(BigInteger, default=50_000)

    # Usage this period
    tokens_used = Column(BigInteger, default=0)
    stt_used = Column(Integer, default=0)
    tts_used = Column(Integer, default=0)
    coding_used = Column(BigInteger, default=0)

    billing_period_start = Column(DateTime(timezone=True), default=utcnow)
    billing_period_end = Column(DateTime(timezone=True))
    next_billing_date = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    team = relationship("Team", back_populates="subscription")


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    url = Column(String(512), nullable=False)
    secret = Column(String(255))
    events = Column(JSON, default=[])  # ["usage.exceeded", "key.revoked", ...]
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    team = relationship("Team", back_populates="webhooks")
