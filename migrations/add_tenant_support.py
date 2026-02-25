"""
为现有数据库添加多租户支持。

此迁移脚本为现有表添加tenant_id列，
并将现有数据迁移到默认租户。
"""

import sys
import os
from datetime import datetime, timezone, date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from services.database import engine, SessionLocal, Base, Tenant, User, APIKey, TenantQuota, Session, Message, AgentLog
import uuid


def migrate_add_tenant_support():
    """
    为现有数据库添加多租户支持。

    步骤:
    1. 创建新的多租户表（tenants, users, api_keys, tenant_quotas）
    2. 为现有表添加tenant_id列
    3. 创建默认租户
    4. 将现有数据迁移到默认租户
    5. 验证迁移成功
    """

    print("=" * 70)
    print("Adding Multi-Tenant Support to Agent Platform")
    print("=" * 70)

    with engine.connect() as conn:
        try:
            # ========================================================================
            # Step 1: Create new multi-tenant tables
            # ========================================================================
            print("\n[Step 1/5] Creating new multi-tenant tables...")

            # Create tenants table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    display_name VARCHAR(200) NOT NULL,
                    plan VARCHAR(50) NOT NULL DEFAULT 'free',
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    settings JSON,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("  ✅ Created 'tenants' table")

            # Create users table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR PRIMARY KEY,
                    tenant_id VARCHAR NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    email VARCHAR(255) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'user',
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    last_login_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_id, email)
                )
            """))
            print("  ✅ Created 'users' table")

            # Create api_keys table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id VARCHAR PRIMARY KEY,
                    tenant_id VARCHAR NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    user_id VARCHAR REFERENCES users(id) ON DELETE SET NULL,
                    key_hash VARCHAR(255) NOT NULL UNIQUE,
                    name VARCHAR(100),
                    scopes JSON,
                    expires_at TIMESTAMP,
                    last_used_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("  ✅ Created 'api_keys' table")

            # Create tenant_quotas table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tenant_quotas (
                    tenant_id VARCHAR PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
                    max_users INTEGER NOT NULL DEFAULT 5,
                    max_agents INTEGER NOT NULL DEFAULT 10,
                    max_sessions_per_day INTEGER NOT NULL DEFAULT 100,
                    max_tokens_per_month INTEGER NOT NULL DEFAULT 1000000,
                    current_month_tokens INTEGER NOT NULL DEFAULT 0,
                    reset_date DATE NOT NULL
                )
            """))
            print("  ✅ Created 'tenant_quotas' table")

            conn.commit()

            # ========================================================================
            # Step 2: Add tenant_id columns to existing tables
            # ========================================================================
            print("\n[Step 2/5] Adding tenant_id columns to existing tables...")

            # Check if sessions table exists and has tenant_id column
            sessions_table = conn.execute(text("""
                SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'
            """)).fetchone()

            if sessions_table:
                # Check if tenant_id column already exists
                has_tenant_id = conn.execute(text("""
                    PRAGMA table_info(sessions)
                """)).fetchall()
                column_names = [row[1] for row in has_tenant_id]

                if 'tenant_id' not in column_names:
                    conn.execute(text("""
                        ALTER TABLE sessions ADD COLUMN tenant_id VARCHAR REFERENCES tenants(id) ON DELETE CASCADE
                    """))
                    print("  ✅ Added 'tenant_id' to 'sessions' table")
                else:
                    print("  ℹ️  'sessions.tenant_id' already exists, skipping")

            # Add tenant_id to messages table
            messages_table = conn.execute(text("""
                SELECT name FROM sqlite_master WHERE type='table' AND name='messages'
            """)).fetchone()

            if messages_table:
                has_tenant_id = conn.execute(text("""
                    PRAGMA table_info(messages)
                """)).fetchall()
                column_names = [row[1] for row in has_tenant_id]

                if 'tenant_id' not in column_names:
                    conn.execute(text("""
                        ALTER TABLE messages ADD COLUMN tenant_id VARCHAR REFERENCES tenants(id) ON DELETE CASCADE
                    """))
                    print("  ✅ Added 'tenant_id' to 'messages' table")
                else:
                    print("  ℹ️  'messages.tenant_id' already exists, skipping")

            # Add tenant_id to agent_logs table
            agent_logs_table = conn.execute(text("""
                SELECT name FROM sqlite_master WHERE type='table' AND name='agent_logs'
            """)).fetchone()

            if agent_logs_table:
                has_tenant_id = conn.execute(text("""
                    PRAGMA table_info(agent_logs)
                """)).fetchall()
                column_names = [row[1] for row in has_tenant_id]

                if 'tenant_id' not in column_names:
                    conn.execute(text("""
                        ALTER TABLE agent_logs ADD COLUMN tenant_id VARCHAR REFERENCES tenants(id) ON DELETE CASCADE
                    """))
                    print("  ✅ Added 'tenant_id' to 'agent_logs' table")
                else:
                    print("  ℹ️  'agent_logs.tenant_id' already exists, skipping")

            conn.commit()

            # ========================================================================
            # Step 3: Create default tenant
            # ========================================================================
            print("\n[Step 3/5] Creating default tenant...")

            # Check if default tenant already exists
            default_tenant = conn.execute(text("""
                SELECT id, name FROM tenants WHERE name = 'default'
            """)).fetchone()

            if default_tenant:
                default_tenant_id = default_tenant[0]
                print(f"  ℹ️  Default tenant already exists: {default_tenant_id}")
            else:
                # Create default tenant
                default_tenant_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO tenants (id, name, display_name, plan, status, created_at, updated_at)
                    VALUES (:id, 'default', 'Default Tenant', 'free', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """), {"id": default_tenant_id})
                print(f"  ✅ Created default tenant: {default_tenant_id}")

            # Create default tenant quota
            default_quota = conn.execute(text("""
                SELECT tenant_id FROM tenant_quotas WHERE tenant_id = :tid
            """), {"tid": default_tenant_id}).fetchone()

            if not default_quota:
                conn.execute(text("""
                    INSERT INTO tenant_quotas (tenant_id, max_users, max_agents, max_sessions_per_day,
                                                     max_tokens_per_month, current_month_tokens, reset_date)
                    VALUES (:tid, 100, 50, 1000, 10000000, 0, DATE('now'))
                """), {"tid": default_tenant_id})
                print("  ✅ Created default tenant quota")

            conn.commit()

            # ========================================================================
            # Step 4: Migrate existing data to default tenant
            # ========================================================================
            print("\n[Step 4/5] Migrating existing data to default tenant...")

            # Migrate sessions
            sessions_updated = conn.execute(text("""
                UPDATE sessions SET tenant_id = :tid WHERE tenant_id IS NULL
            """), {"tid": default_tenant_id}).rowcount
            print(f"  ✅ Migrated {sessions_updated} sessions to default tenant")

            # Migrate messages
            messages_updated = conn.execute(text("""
                UPDATE messages SET tenant_id = :tid WHERE tenant_id IS NULL
            """), {"tid": default_tenant_id}).rowcount
            print(f"  ✅ Migrated {messages_updated} messages to default tenant")

            # Migrate agent_logs
            agent_logs_updated = conn.execute(text("""
                UPDATE agent_logs SET tenant_id = :tid WHERE tenant_id IS NULL
            """), {"tid": default_tenant_id}).rowcount
            print(f"  ✅ Migrated {agent_logs_updated} agent_logs to default tenant")

            conn.commit()

            # ========================================================================
            # Step 5: Verify migration
            # ========================================================================
            print("\n[Step 5/5] Verifying migration...")

            # Check all tables have tenant_id populated
            sessions_null = conn.execute(text("""
                SELECT COUNT(*) FROM sessions WHERE tenant_id IS NULL
            """)).fetchone()[0]
            messages_null = conn.execute(text("""
                SELECT COUNT(*) FROM messages WHERE tenant_id IS NULL
            """)).fetchone()[0]
            agent_logs_null = conn.execute(text("""
                SELECT COUNT(*) FROM agent_logs WHERE tenant_id IS NULL
            """)).fetchone()[0]

            if sessions_null == 0 and messages_null == 0 and agent_logs_null == 0:
                print("  ✅ All data successfully migrated to default tenant")
            else:
                print(f"  ⚠️  Warning: Some records still have NULL tenant_id:")
                print(f"     - Sessions: {sessions_null}")
                print(f"     - Messages: {messages_null}")
                print(f"     - Agent logs: {agent_logs_null}")

            # Show tenant summary
            tenant_count = conn.execute(text("""
                SELECT COUNT(*) FROM tenants
            """)).fetchone()[0]
            user_count = conn.execute(text("""
                SELECT COUNT(*) FROM users
            """)).fetchone()[0]

            print(f"\n📊 Migration Summary:")
            print(f"  - Total tenants: {tenant_count}")
            print(f"  - Total users: {user_count}")
            print(f"  - Default tenant ID: {default_tenant_id}")

            conn.commit()

            print("\n" + "=" * 70)
            print("✅ Multi-tenant support migration completed successfully!")
            print("=" * 70)

            return True

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return False


def rollback_tenant_support():
    """
    回滚多租户支持（警告：这将删除租户数据）。

    这将移除tenant_id列并删除多租户表。
    仅用于测试/开发。
    """

    print("\n⚠️  警告：这将回滚多租户支持!")
    print("  所有租户数据将被删除。")

    response = input("\n继续回滚？(yes/no): ")
    if response.lower() != 'yes':
        print("回滚已取消。")
        return

    print("\n正在回滚多租户支持...")

    with engine.connect() as conn:
        try:
            # 首先删除外键约束
            conn.execute(text("DROP TABLE IF EXISTS api_keys"))
            conn.execute(text("DROP TABLE IF EXISTS tenant_quotas"))
            conn.execute(text("DROP TABLE IF EXISTS users"))
            conn.execute(text("DROP TABLE IF EXISTS tenants"))

            # 注意：SQLite不支持DROP COLUMN，所以我们需要：
            # 1. 创建没有tenant_id的新表
            # 2. 从旧表复制数据
            # 3. 删除旧表
            # 4. 重命名新表
            # 为简单起见，我们只报告需要做什么

            print("  ✅ 已删除多租户表")
            print("\n  ℹ️  注意：tenant_id列仍存在于sessions/messages/agent_logs中")
            print("  ℹ️  要完全删除它们，需要重新创建不包含tenant_id的表")

            conn.commit()

            print("\n✅ 回滚完成（部分）")

        except Exception as e:
            print(f"\n❌ 回滚失败: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="迁移数据库以支持多租户")
    parser.add_argument("--rollback", action="store_true", help="回滚多租户支持")

    args = parser.parse_args()

    if args.rollback:
        rollback_tenant_support()
    else:
        success = migrate_add_tenant_support()
        sys.exit(0 if success else 1)
