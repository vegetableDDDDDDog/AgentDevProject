"""
Database configuration and ORM models for the Agent Platform.

This module provides SQLAlchemy ORM models for managing sessions, messages,
and agent logs in a SQLite database.
"""

import uuid
from datetime import datetime, timezone, date
from typing import Optional, List

from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, ForeignKey, JSON, event, Date, UniqueConstraint
from sqlalchemy.orm import declarative_base, Session, sessionmaker, relationship
from sqlalchemy.engine import Engine

# Database path
DATABASE_URL = "sqlite:///data/agent_platform.db"

# Enable foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn: object, connection_record: object) -> None:
    """Enable foreign key constraints for SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False,
    pool_pre_ping=True  # Verify connections before using
)

# Session factory
SessionLocal = session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for ORM models
Base = declarative_base()


# ============================================================================
# Multi-Tenant Models (Phase 2)
# ============================================================================

class Tenant(Base):
    """
    ORM model for tenants.

    Represents a tenant (organization) in multi-tenant system,
    storing tenant configuration, plan, and metadata.
    """
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)
    plan = Column(String(50), nullable=False, default='free')  # 'free', 'pro', 'enterprise'
    status = Column(String(20), nullable=False, default='active')  # 'active', 'suspended', 'deleted'
    settings = Column(JSON, nullable=True)  # LLM config, feature flags, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="tenant", cascade="all, delete-orphan")
    quota = relationship("TenantQuota", back_populates="tenant", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, plan={self.plan})>"


class User(Base):
    """
    ORM model for users.

    Represents users belonging to tenants, with authentication
    and authorization information.
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='user')  # 'admin', 'user', 'viewer'
    status = Column(String(20), nullable=False, default='active')  # 'active', 'suspended', 'deleted'
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

    # Table constraints
    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uq_tenant_email'),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tenant_id={self.tenant_id})>"


class APIKey(Base):
    """
    ORM model for API keys.

    Represents API keys used for programmatic access, with scope
    and expiration management.
    """
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    key_hash = Column(String(255), nullable=False, unique=True)
    name = Column(String(100), nullable=True)
    scopes = Column(JSON, nullable=True)  # ['chat:read', 'chat:write', 'agent:execute']
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")
    user = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"


class TenantQuota(Base):
    """
    ORM model for tenant quotas.

    Stores resource quotas and current usage for each tenant,
    including users, agents, sessions, and token limits.
    """
    __tablename__ = "tenant_quotas"

    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    max_users = Column(Integer, nullable=False, default=5)
    max_agents = Column(Integer, nullable=False, default=10)
    max_sessions_per_day = Column(Integer, nullable=False, default=100)
    max_tokens_per_month = Column(Integer, nullable=False, default=1000000)
    current_month_tokens = Column(Integer, nullable=False, default=0)
    reset_date = Column(Date, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="quota")

    def __repr__(self) -> str:
        return f"<TenantQuota(tenant_id={self.tenant_id}, max_tokens={self.max_tokens_per_month})>"


# ============================================================================
# Original Models (Extended with tenant_id)
# ============================================================================


class Session(Base):
    """
    ORM model for agent sessions.

    Represents a conversation session with an agent, storing configuration
    and metadata (stored as 'meta' column to avoid SQLAlchemy reserved word).
    """
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)  # Phase 2: Multi-tenant support
    agent_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    config = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    # Relationships
    tenant = relationship("Tenant", backref="sessions")  # Phase 2: Tenant relationship
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    agent_logs = relationship(
        "AgentLog",
        back_populates="session",
        order_by="AgentLog.created_at"
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, agent_type={self.agent_type}, tenant_id={self.tenant_id})>"


class Message(Base):
    """
    ORM model for messages within a session.

    Stores individual messages exchanged between the user and the agent,
    including role, content, and token usage information.
    """
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)  # Phase 2: Multi-tenant support
    role = Column(String(20), nullable=False)  # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    meta = Column(JSON, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="messages")
    tenant = relationship("Tenant", backref="messages")  # Phase 2: Tenant relationship

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, session_id={self.session_id}, role={self.role})>"


class AgentLog(Base):
    """
    ORM model for agent execution logs.

    Tracks agent execution events including task information,
    status, error messages, and execution time.
    """
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)  # Phase 2: Multi-tenant support
    agent_type = Column(String(50), nullable=True)
    task = Column(Text, nullable=True)
    status = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    session = relationship("Session", back_populates="agent_logs")
    tenant = relationship("Tenant", backref="agent_logs")  # Phase 2: Tenant relationship

    def __repr__(self) -> str:
        return f"<AgentLog(id={self.id}, session_id={self.session_id}, tenant_id={self.tenant_id}, status={self.status})>"


def get_db() -> Session:
    """
    Dependency injection function for FastAPI.

    Yields a database session and ensures it's closed after use.

    Yields:
        Session: SQLAlchemy database session

    Example:
        @app.get("/sessions")
        def read_sessions(db: Session = Depends(get_db)):
            return db.query(Session).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables.

    This function creates all tables defined in the ORM models if they
    don't already exist. It uses SQLAlchemy's create_all which is
    idempotent (safe to run multiple times).

    Example:
        init_db()  # Creates all tables
    """
    Base.metadata.create_all(bind=engine)


def drop_all() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data. Use only for testing/development.

    Example:
        drop_all()  # Drops all tables
        init_db()   # Recreates tables
    """
    Base.metadata.drop_all(bind=engine)
