"""
添加工具调用相关表

执行: python migrations/add_tool_calling_tables.py

本脚本为 Phase 3 工具调用功能创建必要的数据库表。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from services.database import Base, ToolCallLog, TenantToolQuota, engine


def migrate():
    """创建工具调用相关表"""
    print("🔄 Creating tool calling tables...")

    # 创建表
    Base.metadata.create_all(engine, tables=[
        ToolCallLog.__table__,
        TenantToolQuota.__table__
    ])

    print("✅ Tool calling tables created successfully!")

    # 验证表创建
    with engine.connect() as conn:
        # SQLite 查询表名
        result = conn.execute(text("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            AND name IN ('tool_call_logs', 'tenant_tool_quotas')
        """)).fetchall()

        print(f"✅ Verified tables: {[r[0] for r in result]}")

        # 验证表结构
        print("\n📋 tool_call_logs 表结构:")
        result = conn.execute(text("PRAGMA table_info(tool_call_logs)"))
        for row in result:
            print(f"  - {row[1]}: {row[2]}")

        print("\n📋 tenant_tool_quotas 表结构:")
        result = conn.execute(text("PRAGMA table_info(tenant_tool_quotas)"))
        for row in result:
            print(f"  - {row[1]}: {row[2]}")


def rollback():
    """回滚迁移（删除表）"""
    print("⚠️  Rolling back tool calling tables...")

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS tenant_tool_quotas"))
        conn.execute(text("DROP TABLE IF EXISTS tool_call_logs"))
        conn.commit()

    print("✅ Tool calling tables dropped!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移工具")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移")
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
