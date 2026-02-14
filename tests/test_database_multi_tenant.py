"""
Test multi-tenant database models.

Tests the new multi-tenant support including:
- Tenant, User, APIKey, TenantQuota models
- tenant_id foreign keys in Session, Message, AgentLog
- Data integrity and cascade deletes
"""

import pytest
import uuid
from datetime import datetime, timezone, date

from services.database import SessionLocal, Base, engine, Tenant, User, APIKey, TenantQuota, Session, Message, AgentLog
from sqlalchemy import text


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_tenant(db_session):
    """
    Create a test tenant with quota.
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
    """Test Tenant model."""

    def test_create_tenant(self, db_session):
        """Test creating a tenant."""
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
        """Test tenant relationships."""
        # Access relationships
        assert test_tenant.quota is not None
        assert test_tenant.quota.max_users == 10
        assert test_tenant.quota.max_agents == 20

    def test_unique_tenant_name(self, db_session):
        """Test tenant name uniqueness."""
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
    """Test User model."""

    def test_create_user(self, db_session, test_tenant):
        """Test creating a user."""
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
        """Test user belongs to tenant."""
        user = User(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            email="user@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        db_session.commit()

        # Access tenant relationship
        assert user.tenant is not None
        assert user.tenant.id == test_tenant.id
        assert user.tenant.name == "test-tenant"

    def test_unique_email_per_tenant(self, db_session, test_tenant):
        """Test email uniqueness within tenant."""
        user1 = User(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            email="same@example.com",
            password_hash="hash1"
        )
        db_session.add(user1)
        db_session.commit()

        # Try to create duplicate email in same tenant
        user2 = User(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            email="same@example.com",  # Duplicate email
            password_hash="hash2"
        )
        db_session.add(user2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestSessionMultiTenant:
    """Test Session model with multi-tenant support."""

    def test_session_has_tenant_id(self, db_session, test_tenant):
        """Test session has tenant_id field."""
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
        """Test session belongs to tenant."""
        session = Session(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            agent_type="test_agent"
        )
        db_session.add(session)
        db_session.commit()

        # Access tenant relationship
        assert session.tenant is not None
        assert session.tenant.id == test_tenant.id

    def test_cascade_delete_tenant_deletes_sessions(self, db_session, test_tenant):
        """Test deleting tenant cascades to sessions."""
        session = Session(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            agent_type="test_agent"
        )
        db_session.add(session)
        db_session.commit()

        session_id = session.id
        tenant_id = test_tenant.id

        # Delete tenant
        db_session.delete(test_tenant)
        db_session.commit()

        # Session should be deleted
        retrieved = db_session.query(Session).filter(Session.id == session_id).first()
        assert retrieved is None


class TestMessageMultiTenant:
    """Test Message model with multi-tenant support."""

    def test_message_has_tenant_id(self, db_session, test_tenant):
        """Test message has tenant_id field."""
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
        """Test message belongs to tenant."""
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

        # Access tenant relationship
        assert message.tenant is not None
        assert message.tenant.id == test_tenant.id


class TestAgentLogMultiTenant:
    """Test AgentLog model with multi-tenant support."""

    def test_agent_log_has_tenant_id(self, db_session, test_tenant):
        """Test agent log has tenant_id field."""
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
        """Test agent log belongs to tenant."""
        agent_log = AgentLog(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            agent_type="test_agent",
            task="Test task"
        )
        db_session.add(agent_log)
        db_session.commit()

        # Access tenant relationship
        assert agent_log.tenant is not None
        assert agent_log.tenant.id == test_tenant.id


class TestTenantIsolation:
    """Test tenant data isolation."""

    def test_tenants_separate_data(self, db_session):
        """Test that different tenants have separate data."""
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
        """Test filtering by tenant_id isolates data correctly."""
        # Create multiple tenants with sessions
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

        # Each tenant should have exactly 2 sessions
        for i in range(3):
            # Find tenant ID
            tenant = db_session.query(Tenant).filter(Tenant.name == f"tenant-{i}").first()
            sessions = db_session.query(Session).filter(Session.tenant_id == tenant.id).all()
            assert len(sessions) == 2
