"""
Agent平台的数据库配置和ORM模型。

本模块提供SQLAlchemy ORM模型，用于在SQLite数据库中管理会话、消息
和Agent日志。
"""

import uuid
from datetime import datetime, timezone, date
from typing import Optional, List

from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, ForeignKey, JSON, event, Date, UniqueConstraint
from sqlalchemy.orm import declarative_base, Session, sessionmaker, relationship
from sqlalchemy.engine import Engine

# 数据库路径
DATABASE_URL = "sqlite:///data/agent_platform.db"

# 为SQLite启用外键约束
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn: object, connection_record: object) -> None:
    """为SQLite启用外键约束。"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# 创建SQLAlchemy引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite需要此参数
    echo=False,
    pool_pre_ping=True  # 使用前验证连接
)

# Session工厂
SessionLocal = session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM模型的声明基类
Base = declarative_base()


# ============================================================================
# 多租户模型 (阶段2)
# ============================================================================

class Tenant(Base):
    """
    租户ORM模型。

    表示多租户系统中的租户（组织），
    存储租户配置、套餐和元数据。
    """
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)
    plan = Column(String(50), nullable=False, default='free')  # 'free', 'pro', 'enterprise'
    status = Column(String(20), nullable=False, default='active')  # 'active', 'suspended', 'deleted'
    settings = Column(JSON, nullable=True)  # LLM配置、特性开关等
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # 关系
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="tenant", cascade="all, delete-orphan")
    quota = relationship("TenantQuota", back_populates="tenant", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, plan={self.plan})>"


class User(Base):
    """
    用户ORM模型。

    表示属于租户的用户，包含认证
    和授权信息。
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='user')  # 'admin', 'user', 'viewer'
    status = Column(String(20), nullable=False, default='active')  # 'active', 'suspended', 'deleted'
    token_version = Column(Integer, nullable=False, default=1)  # Token 版本号，用于强制下线
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # 关系
    tenant = relationship("Tenant", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

    # 表约束
    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uq_tenant_email'),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tenant_id={self.tenant_id})>"


class APIKey(Base):
    """
    API密钥ORM模型。

    表示用于程序化访问的API密钥，包含权限范围
    和过期管理。
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

    # 关系
    tenant = relationship("Tenant", back_populates="api_keys")
    user = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"


class TenantQuota(Base):
    """
    租户配额ORM模型。

    存储每个租户的资源配额和当前使用量，
    包括用户、Agent、会话和Token限制。
    """
    __tablename__ = "tenant_quotas"

    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    max_users = Column(Integer, nullable=False, default=5)
    max_agents = Column(Integer, nullable=False, default=10)
    max_sessions_per_day = Column(Integer, nullable=False, default=100)
    max_tokens_per_month = Column(Integer, nullable=False, default=1000000)
    current_month_tokens = Column(Integer, nullable=False, default=0)
    reset_date = Column(Date, nullable=False)

    # 关系
    tenant = relationship("Tenant", back_populates="quota")

    def __repr__(self) -> str:
        return f"<TenantQuota(tenant_id={self.tenant_id}, max_tokens={self.max_tokens_per_month})>"


# ============================================================================
# 原有模型 (扩展tenant_id)
# ============================================================================


class Session(Base):
    """
    Agent会话ORM模型。

    表示与Agent的对话会话，存储配置
    和元数据（使用'meta'列避免SQLAlchemy保留字冲突）。
    """
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)  # 阶段2: 多租户支持
    agent_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    config = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    # 关系
    tenant = relationship("Tenant", backref="sessions")  # 阶段2: 租户关系
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
    会话内消息的ORM模型。

    存储用户和Agent之间交换的单条消息，
    包括角色、内容和Token使用信息。
    """
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)  # 阶段2: 多租户支持
    role = Column(String(20), nullable=False)  # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    meta = Column(JSON, nullable=True)

    # 关系
    session = relationship("Session", back_populates="messages")
    tenant = relationship("Tenant", backref="messages")  # 阶段2: 租户关系

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, session_id={self.session_id}, role={self.role})>"


class AgentLog(Base):
    """
    Agent执行日志ORM模型。

    跟踪Agent执行事件，包括任务信息、
   状态、错误消息和执行时间。
    """
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)  # 阶段2: 多租户支持
    agent_type = Column(String(50), nullable=True)
    task = Column(Text, nullable=True)
    status = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # 关系
    session = relationship("Session", back_populates="agent_logs")
    tenant = relationship("Tenant", backref="agent_logs")  # 阶段2: 租户关系

    def __repr__(self) -> str:
        return f"<AgentLog(id={self.id}, session_id={self.session_id}, tenant_id={self.tenant_id}, status={self.status})>"


def get_db() -> Session:
    """
    FastAPI的依赖注入函数。

    生成数据库会话并确保在使用后关闭。

    Yields:
        Session: SQLAlchemy数据库会话

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
    通过创建所有表来初始化数据库。

    此函数创建ORM模型中定义的所有表（如果不存在）。
    使用SQLAlchemy的create_all，具有幂等性（可安全多次运行）。

    Example:
        init_db()  # 创建所有表
    """
    Base.metadata.create_all(bind=engine)


def drop_all() -> None:
    """
    删除所有数据库表。

    警告: 这将删除所有数据。仅用于测试/开发。

    Example:
        drop_all()  # 删除所有表
        init_db()   # 重新创建表
    """
    Base.metadata.drop_all(bind=engine)
