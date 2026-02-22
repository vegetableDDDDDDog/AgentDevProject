"""
JWT 认证服务快速测试

验证 AuthService 的基本功能是否正常工作。
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.auth_service import AuthService
from services.database import SessionLocal, Base, engine, User, Tenant
import uuid


def test_password_hashing():
    """测试密码哈希功能"""
    print("=" * 70)
    print("测试 1: 密码哈希")
    print("=" * 70)

    service = AuthService()

    # 哈希密码
    plain_password = "test_password_123"
    print(f"\n原始密码: {plain_password}")

    hashed = service.hash_password(plain_password)
    print(f"哈希密码: {hashed[:30]}...")

    # 验证密码
    is_valid = service.verify_password(plain_password, hashed)
    print(f"验证结果: {'✅ 正确' if is_valid else '❌ 错误'}")

    # 验证错误密码
    is_valid = service.verify_password("wrong_password", hashed)
    print(f"错误密码验证: {'❌ 正确（应该失败）' if not is_valid else '✅ 错误（不应该成功）'}")

    return is_valid


def test_token_generation():
    """测试 Token 生成"""
    print("\n" + "=" * 70)
    print("测试 2: Token 生成")
    print("=" * 70)

    service = AuthService()

    # 创建测试用户对象（不需要数据库）
    class TestUser:
        def __init__(self):
            self.id = str(uuid.uuid4())
            self.tenant_id = str(uuid.uuid4())
            self.role = "admin"
            self.token_version = 1

    user = TestUser()

    # 生成 Access token
    access_token = service.create_access_token(user)
    print(f"\nAccess Token: {access_token[:30]}...")
    print(f"Token 类型: JWT (HS256)")

    # 生成 Refresh token
    refresh_token = service.create_refresh_token(user)
    print(f"Refresh Token: {refresh_token[:30]}...")

    # 验证 Token
    try:
        payload = service.verify_access_token(access_token)
        print(f"\n✅ Token 验证成功")
        print(f"  用户 ID: {payload.sub}")
        print(f"  租户 ID: {payload.tenant_id}")
        print(f"  角色: {payload.role}")
        print(f"  Token 类型: {payload.token_type}")
        return True
    except Exception as e:
        print(f"\n❌ Token 验证失败: {e}")
        return False


def test_complete_flow():
    """测试完整登录流程"""
    print("\n" + "=" * 70)
    print("测试 3: 完整登录流程")
    print("=" * 70)

    db = SessionLocal()
    service = AuthService()

    try:
        # 创建测试租户
        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            id=tenant_id,
            name="test-tenant",
            display_name="Test Tenant",
            plan="free",
            status="active"
        )
        db.add(tenant)

        # 创建测试用户
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            email="test@example.com",
            password_hash=service.hash_password("password123"),
            role="user",
            status="active"
        )
        db.add(user)
        db.commit()

        print(f"\n✅ 测试数据创建成功")
        print(f"  租户 ID: {tenant_id}")
        print(f"  用户 ID: {user_id}")
        print(f"  邮箱: test@example.com")

        # 测试登录
        print(f"\n测试登录...")
        result = service.authenticate_user(db, "test@example.com", "password123")

        print(f"✅ 登录成功")
        print(f"  Access Token: {result['access_token'][:30]}...")
        print(f"  Refresh Token: {result['refresh_token'][:30]}...")
        print(f"  用户信息: {result['user']}")

        # 验证 Token
        payload = service.verify_access_token(result['access_token'])
        print(f"\n✅ Token 验证成功")
        print(f"  Payload: {payload.__dict__}")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🧪 JWT 认证服务快速测试")
    print("=" * 70)

    # 测试 1: 密码哈希
    test1 = test_password_hashing()

    # 测试 2: Token 生成
    test2 = test_token_generation()

    # 测试 3: 完整流程
    test3 = test_complete_flow()

    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"密码哈希: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"Token 生成: {'✅ 通过' if test2 else '❌ 失败'}")
    print(f"完整流程: {'✅ 通过' if test3 else '❌ 失败'}")
    print("=" * 70)

    if test1 and test2 and test3:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败")
        sys.exit(1)
