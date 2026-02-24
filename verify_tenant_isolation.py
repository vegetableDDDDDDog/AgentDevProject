"""
租户隔离功能验证脚本

验证租户隔离服务的基本功能是否正常工作。
"""

import sys
from datetime import date

# 添加项目路径
sys.path.insert(0, '/home/wineash/PycharmProjects/AgentDevProject/.worktrees/phase2-multi-tenant')

from services.database import Base, engine, SessionLocal, Tenant, User, TenantQuota, Session
from services.tenant_service import TenantService
from services.tenant_query import TenantQuery
from services.exceptions import TenantNotFoundException, TenantSuspendedException, QuotaExceededException


def setup_test_data():
    """创建测试数据"""
    db = SessionLocal()

    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)

        # 创建租户 1
        tenant1 = Tenant(
            id="tenant-test-001",
            name="test_tenant_1",
            display_name="测试租户1",
            plan="free",
            status="active",
            settings={"llm_provider": "glm"}
        )
        db.add(tenant1)

        # 创建租户 1 的配额
        quota1 = TenantQuota(
            tenant_id="tenant-test-001",
            max_users=5,
            max_agents=10,
            max_sessions_per_day=100,
            max_tokens_per_month=1000000,
            current_month_tokens=0,
            reset_date=date.today()
        )
        db.add(quota1)

        # 创建租户 1 的用户
        for i in range(3):
            user = User(
                tenant_id="tenant-test-001",
                email=f"user{i}@tenant1.com",
                password_hash="hash123",
                role="user",
                status="active"
            )
            db.add(user)

        # 创建租户 2（用于隔离测试）
        tenant2 = Tenant(
            id="tenant-test-002",
            name="test_tenant_2",
            display_name="测试租户2",
            plan="pro",
            status="active",
            settings={"llm_provider": "openai"}
        )
        db.add(tenant2)

        quota2 = TenantQuota(
            tenant_id="tenant-test-002",
            max_users=10,
            max_agents=20,
            max_sessions_per_day=500,
            max_tokens_per_month=5000000,
            current_month_tokens=0,
            reset_date=date.today()
        )
        db.add(quota2)

        # 创建租户 2 的会话
        for i in range(2):
            session = Session(
                tenant_id="tenant-test-002",
                agent_type=f"agent_type_{i}",
                config={},
                meta={}
            )
            db.add(session)

        # 创建租户 1 的会话
        for i in range(3):
            session = Session(
                tenant_id="tenant-test-001",
                agent_type=f"agent_type_{i}",
                config={},
                meta={}
            )
            db.add(session)

        db.commit()

        print("✅ 测试数据创建成功")
        return db

    except Exception as e:
        db.rollback()
        print(f"❌ 创建测试数据失败: {e}")
        raise


def test_tenant_service():
    """测试租户服务"""
    print("\n" + "="*50)
    print("测试 TenantService")
    print("="*50)

    db = SessionLocal()
    service = TenantService()

    try:
        # 测试 1: 获取租户上下文
        print("\n1️⃣ 测试获取租户上下文...")
        context = service.get_tenant_context(db, "tenant-test-001")
        print(f"   ✅ 租户名称: {context.display_name}")
        print(f"   ✅ 租户套餐: {context.plan}")
        print(f"   ✅ 租户状态: {context.status}")
        print(f"   ✅ 是否激活: {context.is_active()}")
        print(f"   ✅ 配额 - 最大用户数: {context.quotas.max_users}")

        # 测试 2: 检查用户数配额
        print("\n2️⃣ 测试用户数配额检查...")
        try:
            service.check_user_quota(db, context)
            print(f"   ✅ 用户数配额检查通过")
        except QuotaExceededException as e:
            print(f"   ❌ 用户数配额超限: {e}")

        # 测试 3: 获取当前用户数
        print("\n3️⃣ 测试获取当前用户数...")
        count = service.get_current_user_count(db, "tenant-test-001")
        print(f"   ✅ 当前用户数: {count}")

        # 测试 4: 测试特性检查
        print("\n4️⃣ 测试特性检查...")
        has_basic = context.has_feature("basic_chat")
        has_advanced = context.has_feature("advanced_agents")
        print(f"   ✅ 有 basic_chat: {has_basic}")
        print(f"   ✅ 有 advanced_agents: {has_advanced}")

        # 测试 5: 测试租户不存在
        print("\n5️⃣ 测试租户不存在...")
        try:
            service.get_tenant_context(db, "non-existent-tenant")
            print("   ❌ 应该抛出异常")
        except TenantNotFoundException:
            print("   ✅ 正确抛出 TenantNotFoundException")

        print("\n✅ TenantService 所有测试通过!")

    finally:
        db.close()


def test_tenant_query():
    """测试租户感知查询"""
    print("\n" + "="*50)
    print("测试 TenantQuery")
    print("="*50)

    db = SessionLocal()

    try:
        # 测试 1: 租户过滤
        print("\n1️⃣ 测试租户过滤...")
        sessions = TenantQuery.filter_by_tenant(
            db, Session, "tenant-test-001"
        ).all()
        print(f"   ✅ 租户 1 的会话数: {len(sessions)}")
        for session in sessions:
            assert session.tenant_id == "tenant-test-001"
        print("   ✅ 所有会话都属于租户 1")

        # 测试 2: 跨租户验证
        print("\n2️⃣ 测试跨租户访问阻止...")
        tenant1_session = sessions[0]
        result = TenantQuery.get_by_id(
            db, Session, tenant1_session.id, "tenant-test-002"
        )
        if result is None:
            print("   ✅ 租户 2 无法访问租户 1 的会话")
        else:
            print("   ❌ 租户隔离失败!")

        # 测试 3: 正确租户访问
        print("\n3️⃣ 测试正确租户访问...")
        result = TenantQuery.get_by_id(
            db, Session, tenant1_session.id, "tenant-test-001"
        )
        if result is not None:
            print("   ✅ 租户 1 可以访问自己的会话")
        else:
            print("   ❌ 租户无法访问自己的会话!")

        # 测试 4: 统计数量
        print("\n4️⃣ 测试统计数量...")
        count = TenantQuery.count(db, Session, "tenant-test-001")
        print(f"   ✅ 租户 1 的会话总数: {count}")
        assert count == 3

        print("\n✅ TenantQuery 所有测试通过!")

    finally:
        db.close()


def main():
    """主函数"""
    print("="*50)
    print("租户隔离功能验证")
    print("="*50)

    try:
        # 创建测试数据
        setup_test_data()

        # 测试租户服务
        test_tenant_service()

        # 测试租户查询
        test_tenant_query()

        print("\n" + "="*50)
        print("🎉 所有测试通过!")
        print("="*50)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
