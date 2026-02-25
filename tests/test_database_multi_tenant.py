"""
测试多租户数据库模型。

测试新的多租户支持，包括：
- Tenant, User, APIKey, TenantQuota 模型
- Session, Message, AgentLog 中的 tenant_id 外键
- 数据完整性和级联删除
"""

import pytest
import uuid
from datetime import datetime, timezone, date

from services.database import SessionLocal, Base, engine, Tenant, User, APIKey, TenantQuota, Session, Message, AgentLog
from sqlalchemy import text


@pytest.fixture(scope="function")
def db_session():
    """
    为每个测试创建新的数据库会话。
    """
    # 创建所有表
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        # 测试后删除所有表
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_tenant(db_session):
    """
    创建带配额的测试租户。
    """
    tenant_id = str(uuid.uuid4())

    tenant = Tenant(
        id=tenant_id,
        name="test-tenant",
        display_name="Test Tenant",
        plan="pro",
        status="active",
        settings={"llm_provider": "glm", "glm_api_key": "test-key"}
    )
    db_session.add(tenant)

    quota = TenantQuota(
        tenant_id=tenant_id,
        max_users=10,
        max_agents=20,
        max_sessions_per_day=200,
        max_tokens_per_month=2000000,
        current_month_tokens=0,
        reset_date=date(2026, 2, 14)
    )
    db_session.add(quota)

    db_session.commit()
    return tenant


class TestTenantModel:
    """测试租户模型。"""

    def test_create_tenant(self, db_session):
        """测试创建租户。"""
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name="test-tenant",
            display_name="Test Tenant",
            plan="free",
            status="active"
        )
        db_session.add(tenant)
        db_session.commit()

        retrieved = db_session.query(Tenant).filter(Tenant.name == "test-tenant").first()
        assert retrieved is not None
        assert retrieved.name == "test-tenant"
        assert retrieved.plan == "free"
        assert retrieved.status == "active"

    def test_tenant_relationships(self, db_session, test_tenant):
        """测试租户关系。"""
        # 访问关系
        assert test_tenant.quota is not None
        assert test_tenant.quota.max_users == 10
        assert test_tenant.quota.max_agents == 20

    def test_unique_tenant_name(self, db_session):
        """测试租户名称唯一性。"""
        tenant_id1 = str(uuid.uuid4())
        tenant_id2 = str(uuid.uuid4())

        tenant1 = Tenant(
            id=tenant_id1,
            name="duplicate-name",
            display_name="Tenant 1",
            plan="free"
        )
        db_session.add(tenant1)
        db_session.commit()

        # Try to create duplicate tenant name
        tenant2 = Tenant(
            id=tenant_id2,
            name="duplicate-name",  # Duplicate name
            display_name="Tenant 2",
            plan="free"
        )
        db_session.add(tenant2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestUserModel:
    """测试用户模型。"""

    def test_create_user(self, db_session, test_tenant):
        """测试创建用户。"""
        user_id = str(uuid.uuid4())

        user = User(
            id=user_id,
            tenant_id=test_tenant.id,
            email="user@example.com",
            password_hash="hashed_password",
            role="user",
            status="active"
        )
        db_session.add(user)
        db_session.commit()

        retrieved = db_session.query(User).filter(User.id == user_id).first()
        assert retrieved is not None
        assert retrieved.email == "user@example.com"
        assert retrieved.tenant_id == test_tenant.id
        assert retrieved.role == "user"

    def test_user_tenant_relationship(self, db_session, test_tenant):
        """测试用户属于租户。"""
        user = User(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            email="user@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        db_session.commit()

        # 访问租户关系
        assert user.tenant is not None
        assert user.tenant.id == test_tenant.id
        assert user.tenant.name == "test-tenant"

    def test_unique_email_per_tenant(self, db_session, test_tenant):
        """测试租户内邮箱唯一性。"""
        user1 = User(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            email="same@example.com",
            password_hash="hash1"
        )
        db_session.add(user1)
        db_session.commit()

        # 尝试在同一租户中创建重复邮箱
        user2 = User(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            email="same@example.com",  # 重复邮箱
            password_hash="hash2"
        )
        db_session.add(user2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestSessionMultiTenant:
    """测试多租户支持的Session模型。"""

    def test_session_has_tenant_id(self, db_session, test_tenant):
        """测试session有tenant_id字段。"""
        session = Session(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            agent_type="test_agent"
        )
        db_session.add(session)
        db_session.commit()

        retrieved = db_session.query(Session).filter(Session.id == session.id).first()
        assert retrieved is not None
        assert retrieved.tenant_id == test_tenant.id
        assert retrieved.agent_type == "test_agent"

    def test_session_tenant_relationship(self, db_session, test_tenant):
        """测试session属于租户。"""
        session = Session(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            agent_type="test_agent"
        )
        db_session.add(session)
        db_session.commit()

        # 访问租户关系
        assert session.tenant is not None
        assert session.tenant.id == test_tenant.id

    def test_cascade_delete_tenant_deletes_sessions(self, db_session, test_tenant):
        """测试删除租户级联删除session。"""
        session = Session(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            agent_type="test_agent"
        )
        db_session.add(session)
        db_session.commit()

        session_id = session.id
        tenant_id = test_tenant.id

        # 删除租户
        db_session.delete(test_tenant)
        db_session.commit()

        # Session应该被删除
        retrieved = db_session.query(Session).filter(Session.id == session_id).first()
        assert retrieved is None


class TestMessageMultiTenant:
    """测试多租户支持的Message模型。"""

    def test_message_has_tenant_id(self, db_session, test_tenant):
        """测试message有tenant_id字段。"""
        session = Session(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            agent_type="test_agent"
        )
        db_session.add(session)
        db_session.commit()

        message = Message(
            id=str(uuid.uuid4()),
            session_id=session.id,
            tenant_id=test_tenant.id,
            role="user",
            content="Hello, world!"
        )
        db_session.add(message)
        db_session.commit()

        retrieved = db_session.query(Message).filter(Message.id == message.id).first()
        assert retrieved is not None
        assert retrieved.tenant_id == test_tenant.id
        assert retrieved.content == "Hello, world!"

    def test_message_tenant_relationship(self, db_session, test_tenant):
        """测试message属于租户。"""
        session = Session(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            agent_type="test_agent"
        )
        db_session.add(session)
        db_session.commit()

        message = Message(
            id=str(uuid.uuid4()),
            session_id=session.id,
            tenant_id=test_tenant.id,
            role="user",
            content="Test message"
        )
        db_session.add(message)
        db_session.commit()

        # 访问租户关系
        assert message.tenant is not None
        assert message.tenant.id == test_tenant.id


class TestAgentLogMultiTenant:
    """测试多租户支持的AgentLog模型。"""

    def test_agent_log_has_tenant_id(self, db_session, test_tenant):
        """测试agent log有tenant_id字段。"""
        agent_log = AgentLog(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            agent_type="test_agent",
            task="Test task",
            status="completed"
        )
        db_session.add(agent_log)
        db_session.commit()

        retrieved = db_session.query(AgentLog).filter(AgentLog.id == agent_log.id).first()
        assert retrieved is not None
        assert retrieved.tenant_id == test_tenant.id
        assert retrieved.status == "completed"

    def test_agent_log_tenant_relationship(self, db_session, test_tenant):
        """测试agent log属于租户。"""
        agent_log = AgentLog(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            agent_type="test_agent",
            task="Test task"
        )
        db_session.add(agent_log)
        db_session.commit()

        # 访问租户关系
        assert agent_log.tenant is not None
        assert agent_log.tenant.id == test_tenant.id


class TestTenantIsolation:
    """测试租户数据隔离。"""

    def test_tenants_separate_data(self, db_session):
        """测试不同租户拥有独立的数据。"""
        # Create two tenants
        tenant1_id = str(uuid.uuid4())
        tenant2_id = str(uuid.uuid4())

        tenant1 = Tenant(id=tenant1_id, name="tenant1", display_name="Tenant 1", plan="free")
        tenant2 = Tenant(id=tenant2_id, name="tenant2", display_name="Tenant 2", plan="free")
        db_session.add_all([tenant1, tenant2])
        db_session.commit()

        # Create sessions for each tenant
        session1 = Session(
            id=str(uuid.uuid4()),
            tenant_id=tenant1_id,
            agent_type="agent1"
        )
        session2 = Session(
            id=str(uuid.uuid4()),
            tenant_id=tenant2_id,
            agent_type="agent2"
        )
        db_session.add_all([session1, session2])
        db_session.commit()

        # Query sessions for tenant1
        tenant1_sessions = db_session.query(Session).filter(Session.tenant_id == tenant1_id).all()
        assert len(tenant1_sessions) == 1
        assert tenant1_sessions[0].agent_type == "agent1"

        # Query sessions for tenant2
        tenant2_sessions = db_session.query(Session).filter(Session.tenant_id == tenant2_id).all()
        assert len(tenant2_sessions) == 1
        assert tenant2_sessions[0].agent_type == "agent2"

    def test_tenant_filter_isolation(self, db_session):
        """测试按tenant_id过滤正确隔离数据。"""
        # 创建多个租户及其sessions
        for i in range(3):
            tenant_id = str(uuid.uuid4())
            tenant = Tenant(
                id=tenant_id,
                name=f"tenant-{i}",
                display_name=f"Tenant {i}",
                plan="free"
            )
            db_session.add(tenant)

            for j in range(2):
                session = Session(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    agent_type=f"agent-{i}-{j}"
                )
                db_session.add(session)

        db_session.commit()

        # 每个租户应该恰好有2个sessions
        for i in range(3):
            # 查找租户ID
            tenant = db_session.query(Tenant).filter(Tenant.name == f"tenant-{i}").first()
            sessions = db_session.query(Session).filter(Session.tenant_id == tenant.id).all()
            assert len(sessions) == 2
