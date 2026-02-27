#!/usr/bin/env python3
"""
创建新用户的脚本

用法:
    python create_user.py user@example.com password123
    python create_user.py user@example.com password123 --admin  # 创建管理员用户
"""

import sys
import getpass
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from services.database import SessionLocal, User, Tenant
from services.auth_service import AuthService
import uuid


def create_tenant(db: Session, name: str) -> Tenant:
    """创建新租户"""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name=name,
        display_name=name,  # 添加 display_name
        plan='free',
        status='active'
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def create_user(db: Session, email: str, password: str, role: str = "user") -> User:
    """创建新用户"""
    # 检查用户是否已存在
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        print(f"❌ 用户 {email} 已存在")
        return existing_user

    # 创建默认租户（如果还没有租户）
    tenant = db.query(Tenant).first()
    if not tenant:
        print("创建默认租户...")
        tenant = create_tenant(db, "默认租户")

    # 使用 AuthService 哈希密码
    auth_service = AuthService()
    hashed_password = auth_service.hash_password(password)

    try:
        # 创建用户
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=hashed_password,
            role=role,
            tenant_id=tenant.id,
            status="active"
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"\n✅ 用户创建成功！")
        print(f"  邮箱: {user.email}")
        print(f"  角色: {user.role}")
        print(f"  租户: {tenant.display_name}")
        print(f"  用户ID: {user.id}")
        print(f"\n可以使用以下凭据登录:")
        print(f"  邮箱: {email}")
        print(f"  密码: {password}")

        return user

    except Exception as e:
        print(f"❌ 创建用户失败: {e}")
        db.rollback()
        raise


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python create_user.py <邮箱> [密码] [--admin]")
        print("\n示例:")
        print("  python create_user.py user@example.com password123")
        print("  python create_user.py admin@example.com admin123 --admin")
        print("\n如果不提供密码，将提示输入。")
        sys.exit(1)

    email = sys.argv[1]
    role = "admin" if "--admin" in sys.argv else "user"

    # 获取密码
    if len(sys.argv) >= 3 and not sys.argv[2].startswith("--"):
        password = sys.argv[2]
    else
        password = getpass.getpass("请输入密码: ")

    # 验证密码长度
    if len(password) < 8:
        print("❌ 密码长度至少为 8 个字符")
        sys.exit(1)

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 创建用户
        create_user(db, email, password, role)

    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
