"""
为 users 表添加 token_version 字段

此迁移脚本为 users 表添加 token_version 字段，用于支持强制下线功能。
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from services.database import engine


def migrate_add_token_version():
    """
    为 users 表添加 token_version 字段

    Returns:
        bool: 迁移成功返回 True，失败返回 False
    """

    print("=" * 70)
    print("添加 token_version 字段到 users 表")
    print("=" * 70)

    with engine.connect() as conn:
        try:
            # 检查字段是否已存在
            columns = conn.execute(text("""
                PRAGMA table_info(users)
            """)).fetchall()

            column_names = [row[1] for row in columns]

            if 'token_version' in column_names:
                print("\nℹ️  'token_version' 字段已存在，跳过迁移")
                return True

            # 添加 token_version 字段
            print("\n[1/1] 添加 token_version 字段...")
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1
            """))
            print("  ✅ 已添加 'token_version' 字段（默认值: 1）")

            conn.commit()

            # 验证字段添加成功
            columns = conn.execute(text("""
                PRAGMA table_info(users)
            """)).fetchall()

            column_names = [row[1] for row in columns]

            if 'token_version' in column_names:
                print("\n✅ 迁移成功！")
                print(f"   当前 users 表字段: {', '.join(column_names)}")
                return True
            else:
                print("\n❌ 迁移失败：字段未成功添加")
                return False

        except Exception as e:
            print(f"\n❌ 迁移失败: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return False


def rollback_token_version():
    """
    回滚 token_version 字段（警告：SQLite 不支持 DROP COLUMN）

    注意：SQLite 不支持 ALTER TABLE DROP COLUMN
    此函数仅为记录用途，实际回滚需要重新创建表
    """

    print("\n⚠️  警告：SQLite 不支持 DROP COLUMN")
    print("   要回滚此迁移，需要：")
    print("   1. 创建新的 users 表（不包含 token_version）")
    print("   2. 复制数据到新表")
    print("   3. 删除旧表")
    print("   4. 重命名新表")
    print("\n   或者，保持 token_version 字段（不影响功能）")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="添加 token_version 字段到 users 表")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移（SQLite 不支持）")

    args = parser.parse_args()

    if args.rollback:
        rollback_token_version()
    else:
        success = migrate_add_token_version()
        sys.exit(0 if success else 1)
