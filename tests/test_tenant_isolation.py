"""
租户隔离测试

测试租户隔离服务的各项功能，包括租户上下文管理、
租户隔离中间件、数据访问控制等。
"""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.database import Base, Tenant, User, TenantQuota, Session
from services.tenant_service import TenantService, TenantContext, TenantQuotaInfo
from services.tenant_query import TenantQuery
from services.exceptions import (
    TenantNotFoundException,
    TenantSuspendedException,
    QuotaExceededException
)


# ============================================================================
# 测试数据库设置
# ============================================================================

# 创建内存数据库用于测试
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionfactory = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


@pytest.fixture
def db():
    """创建测试数据库会话"""
    # 创建所有表
    Base.metadata.create_all(bind=test_engine)

    # 创建会话
    session = TestSessionLocal()

    yield session

    # 清理
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def sample_tenant(db):
    """创建示例租户"""
    tenant = Tenant(
        id="tenant-001",
        name="test_tenant",
        display_name="测试租户",
        plan="free",
        status="active",
        settings={"llm_provider": "glm"}
    )
    db.add(tenant)

    # 创建配额
    quota = TenantQuota(
        tenant_id="tenant-001",
        max_users=5,
        max_agents=10,
        max_sessions_per_day=100,
        max_tokens_per_month=1000000,
        current_month_tokens=0,
        reset_date=date.today()
    )
    db.add(quota)

    db.commit()
    return tenant


@pytest.fixture
def suspended_tenant(db):
    """创建暂停的租户"""
    tenant = Tenant(
        id="tenant-suspended",
        name="suspended_tenant",
        display_name="暂停租户",
        plan="free",
        status="suspended",
        settings={}
    )
    db.add(tenant)

    quota = TenantQuota(
        tenant_id="tenant-suspended",
        max_users=5,
        max_agents=10,
        max_sessions_per_day=100,
        max_tokens_per_month=1000000,
        current_month_tokens=0,
        reset_date=date.today()
    )
    db.add(quota)

    db.commit()
    return tenant


@pytest.fixture
def sample_users(db, sample_tenant):
    """创建示例用户"""
    users = []
    for i in range(3):
        user = User(
            tenant_id=sample_tenant.id,
            email=f"user{i}@example.com",
            password_hash="hash123",
            role="user",
            status="active"
        )
        db.add(user)
        users.append(user)

    db.commit()
    return users


# ============================================================================
# TenantService 测试
# ============================================================================

class TestTenantService:
    """测试租户服务"""

    def test_get_tenant_context_success(self, db, sample_tenant):
        """测试成功获取租户上下文"""
        service = TenantService()
        context = service.get_tenant_context(db, sample_tenant.id)

        assert context is not None
        assert context.tenant_id == sample_tenant.id
        assert context.tenant_name == "test_tenant"
        assert context.display_name == "测试租户"
        assert context.plan == "free"
        assert context.status == "active"
        assert context.is_active() is True

    def test_get_tenant_context_not_found(self, db):
        """测试租户不存在"""
        service = TenantService()

        with pytest.raises(TenantNotFoundException):
            service.get_tenant_context(db, "non-existent-id")

    def test_get_tenant_context_suspended(self, db, suspended_tenant):
        """测试租户被暂停"""
        service = TenantService()

        with pytest.raises(TenantSuspendedException):
            service.get_tenant_context(db, suspended_tenant.id)

    def test_check_user_quota_success(self, db, sample_tenant, sample_users):
        """测试用户数配额检查 - 未超限"""
        service = TenantService()
        context = service.get_tenant_context(db, sample_tenant.id)

        # 3个用户，限制5个，应该通过
        assert service.check_user_quota(db, context) is True

    def test_check_user_quota_exceeded(self, db, sample_tenant):
        """测试用户数配额检查 - 已超限"""
        # 创建5个用户（达到上限）
        for i in range(5):
            user = User(
                tenant_id=sample_tenant.id,
                email=f"fulluser{i}@example.com",
                password_hash="hash123",
                role="user",
                status="active"
            )
            db.add(user)
        db.commit()

        service = TenantService()
        context = service.get_tenant_context(db, sample_tenant.id)

        # 应该抛出异常
        with pytest.raises(QuotaExceededException) as exc_info:
            service.check_user_quota(db, context)

        assert exc_info.value.args[0] == "users"

    def test_get_current_user_count(self, db, sample_tenant, sample_users):
        """测试获取当前用户数"""
        service = TenantService()

        count = service.get_current_user_count(db, sample_tenant.id)
        assert count == 3

    def test_has_feature(self, db, sample_tenant):
        """测试特性检查"""
        service = TenantService()
        context = service.get_tenant_context(db, sample_tenant.id)

        # free 套餐有 basic_chat
        assert context.has_feature("basic_chat") is True

        # free 套餐没有 advanced_agents
        assert context.has_feature("advanced_agents") is False

    def test_get_setting(self, db, sample_tenant):
        """测试获取配置"""
        service = TenantService()
        context = service.get_tenant_context(db, sample_tenant.id)

        # 存在的配置
        assert context.get_setting("llm_provider") == "glm"

        # 不存在的配置
        assert context.get_setting("non_existent", "default") == "default"


# ============================================================================
# TenantQuery 测试
# ============================================================================

class TestTenantQuery:
    """测试租户感知查询"""

    @pytest.fixture
    def sample_sessions(self, db, sample_tenant):
        """创建示例会话"""
        sessions = []
        for i in range(3):
            session = Session(
                tenant_id=sample_tenant.id,
                agent_type=f"agent_{i}",
                config={},
                meta={}
            )
            db.add(session)
            sessions.append(session)

        # 创建另一个租户的会话
        other_tenant = Tenant(
            id="tenant-other",
            name="other_tenant",
            display_name="其他租户",
            plan="free",
            status="active",
            settings={}
        )
        db.add(other_tenant)
        db.commit()

        other_session = Session(
            tenant_id="tenant-other",
            agent_type="other_agent",
            config={},
            meta={}
        )
        db.add(other_session)
        db.commit()

        return sessions

    def test_filter_by_tenant(self, db, sample_tenant, sample_sessions):
        """测试租户过滤"""
        # 只返回当前租户的会话
        query = TenantQuery.filter_by_tenant(db, Session, sample_tenant.id)
        sessions = query.all()

        assert len(sessions) == 3
        for session in sessions:
            assert session.tenant_id == sample_tenant.id

    def test_get_by_id(self, db, sample_tenant, sample_sessions):
        """测试根据 ID 获取资源"""
        target_session = sample_sessions[0]

        # 正确的租户
        session = TenantQuery.get_by_id(
            db, Session, target_session.id, sample_tenant.id
        )
        assert session is not None
        assert session.id == target_session.id

        # 错误的租户
        session = TenantQuery.get_by_id(
            db, Session, target_session.id, "wrong-tenant-id"
        )
        assert session is None

    def test_count(self, db, sample_tenant, sample_sessions):
        """测试统计数量"""
        count = TenantQuery.count(db, Session, sample_tenant.id)
        assert count == 3


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
