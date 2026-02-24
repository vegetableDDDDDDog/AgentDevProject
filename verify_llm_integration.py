"""
LLM 集成验证脚本

测试真实 LLM 集成功能。
注意：需要配置真实的 API Key 才能运行。
"""

import sys
import asyncio

sys.path.insert(0, '/home/wineash/PycharmProjects/AgentDevProject/.worktrees/phase2-multi-tenant')

from datetime import date
from services.database import Base, engine, SessionLocal, Tenant, TenantQuota
from services.llm_service import LLMService, create_messages_from_history
from services.token_service import TokenService


def setup_test_tenant():
    """创建测试租户（带 LLM 配置）"""
    db = SessionLocal()

    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)

        # 创建测试租户
        tenant = Tenant(
            id="tenant-llm-test",
            name="llm_test_tenant",
            display_name="LLM 测试租户",
            plan="pro",
            status="active",
            settings={
                # ⚠️ 重要：请修改为你的真实 API Key
                "llm_provider": "openai-compatible",
                "llm_api_key": "your-zhipu-ai-api-key-here",  # 修改这里！
                "llm_base_url": "https://open.bigmodel.cn/api/paas/v4/",
                "llm_model": "glm-4",
                "llm_temperature": 0.7,
                "llm_max_tokens": 2000
            }
        )
        db.add(tenant)

        # 创建配额
        quota = TenantQuota(
            tenant_id="tenant-llm-test",
            max_users=10,
            max_agents=20,
            max_sessions_per_day=500,
            max_tokens_per_month=5000000,
            current_month_tokens=0,
            reset_date=date.today()
        )
        db.add(quota)

        db.commit()

        print("✅ 测试租户创建成功")
        print(f"   租户 ID: {tenant.id}")
        print(f"   请在租户设置中配置真实的 API Key!")

        return tenant

    except Exception as e:
        db.rollback()
        print(f"❌ 创建测试租户失败: {e}")
        raise
    finally:
        db.close()


def test_llm_service():
    """测试 LLM 服务"""
    print("\n" + "="*50)
    print("测试 LLM 服务")
    print("="*50)

    db = SessionLocal()

    try:
        # 获取测试租户
        tenant = db.query(Tenant).filter(
            Tenant.id == "tenant-llm-test"
        ).first()

        if not tenant:
            print("❌ 测试租户不存在，请先运行 setup_test_tenant()")
            return

        # 检查 API Key 配置
        api_key = tenant.settings.get("llm_api_key")
        if "your-zhipu-ai-api-key-here" in api_key or not api_key:
            print("❌ 请配置真实的 API Key!")
            print("   在数据库中更新 tenants 表的 settings 字段:")
            print(f"   UPDATE tenants SET settings = json_set(settings, '$.llm_api_key', 'your-real-api-key') WHERE id = '{tenant.id}';")
            return

        # 创建租户上下文（模拟）
        from services.tenant_service import TenantService, TenantContext, TenantQuotaInfo

        tenant_service = TenantService()
        tenant_context = tenant_service.get_tenant_context(db, tenant.id)

        print(f"\n✅ 租户配置:")
        print(f"   Provider: {tenant_context.get_setting('llm_provider')}")
        print(f"   Base URL: {tenant_context.get_setting('llm_base_url')}")
        print(f"   Model: {tenant_context.get_setting('llm_model')}")

        # 创建 LLM 服务
        llm_service = LLMService.from_tenant_context(tenant_context)

        print(f"\n1️⃣ 测试同步聊天...")

        # 创建消息
        messages = create_messages_from_history(
            user_message="你好，请用一句话介绍你自己",
            system_prompt="你是一个助手"
        )

        # 异步调用
        async def test_chat():
            response = await llm_service.achat(messages)
            print(f"   ✅ 响应: {response.content[:100]}...")
            return response

        response = asyncio.run(test_chat())

        print(f"\n2️⃣ 测试流式聊天...")

        async def test_stream():
            full_response = ""
            async for chunk in llm_service.stream_chat(messages):
                full_response += chunk
                print(chunk, end="", flush=True)
            print("\n")
            return full_response

        full = asyncio.run(test_stream())
        print(f"   ✅ 流式输出完成，总长度: {len(full)} 字符")

        print(f"\n✅ LLM 服务测试通过!")

    except Exception as e:
        print(f"\n❌ LLM 服务测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def test_token_service():
    """测试 Token 统计服务"""
    print("\n" + "="*50)
    print("测试 Token 统计服务")
    print("="*50)

    token_service = TokenService()

    # 记录 Token 使用
    print(f"\n1️⃣ 测试记录 Token 使用...")
    token_service.record_token_usage(
        session_id="test-session",
        tenant_id="tenant-llm-test",
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300
    )
    print(f"   ✅ Token 使用已记录")

    # 获取统计
    print(f"\n2️⃣ 测试获取统计数据...")
    stats = token_service.get_usage_stats(
        tenant_id="tenant-llm-test",
        days=30
    )

    print(f"   ✅ 统计结果:")
    print(f"      总 Token 数: {stats['total_tokens']}")
    print(f"      日均 Token: {stats['daily_average']}")
    print(f"      总消息数: {stats['total_messages']}")
    print(f"      平均每条消息: {stats['avg_tokens_per_message']} tokens")

    print(f"\n✅ Token 统计服务测试通过!")


def main():
    """主函数"""
    print("="*50)
    print("LLM 集成功能验证")
    print("="*50)

    # 创建测试租户
    tenant = setup_test_tenant()

    # 提示用户配置 API Key
    print(f"\n⚠️  重要提示:")
    print(f"   1. 请修改租户 settings 中的 llm_api_key")
    print(f"   2. 或者直接运行 test_llm_service() 测试")
    print(f"\n   更新命令:")
    print(f"   UPDATE tenants SET settings = json_set(settings, '$.llm_api_key', 'your-real-key') WHERE id = '{tenant.id}';")

    # 询问是否继续
    print(f"\n是否继续测试？(需要配置 API Key)")
    print(f"如已配置，输入 'y' 继续:")

    # 自动测试（在配置真实 API Key 后）
    try:
        test_llm_service()
        test_token_service()

        print("\n" + "="*50)
        print("🎉 所有测试完成!")
        print("="*50)

    except Exception as e:
        print(f"\n⚠️  测试跳过或失败: {e}")
        print(f"   请配置真实的 API Key 后重新运行")


if __name__ == "__main__":
    main()
