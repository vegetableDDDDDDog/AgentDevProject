#!/usr/bin/env python3
"""
测试 IDE 跳转功能

使用方法:
1. 在 IDE 中打开此文件
2. 尝试点击以下函数名，看是否能正确跳转:
   - db_init_db (应该跳转到 services/database.py:269)
   - db_drop_all (应该跳转到 services/database.py:282)
   - initialize_database (应该跳转到本文件:113)
   - drop_all_tables (应该跳转到本文件:98)
"""

# ✅ 测试1: 别名导入 - 点击 db_init_db 应该跳转到 database.py:269
from services.init_db import db_init_db, db_drop_all, initialize_database, drop_all_tables

def test_alias_import():
    """测试别名导入的跳转"""
    print("=" * 70)
    print("测试 IDE 跳转功能")
    print("=" * 70)

    # 点击下面的 db_init_db，应该跳转到 database.py:269
    print("\n[测试1] 点击 db_init_db 应该跳转到:")
    print("  文件: services/database.py")
    print("  行号: 269")
    print(f"  实际位置: {db_init_db.__module__}")

    # 点击下面的 db_drop_all，应该跳转到 database.py:282
    print("\n[测试2] 点击 db_drop_all 应该跳转到:")
    print("  文件: services/database.py")
    print("  行号: 282")
    print(f"  实际位置: {db_drop_all.__module__}")

    # 点击下面的 initialize_database，应该跳转到本文件
    print("\n[测试3] 点击 initialize_database 应该跳转到:")
    print("  文件: services/init_db.py")
    print("  行号: 119")
    print(f"  实际位置: {initialize_database.__module__}")

    # 点击下面的 drop_all_tables，应该跳转到本文件
    print("\n[测试4] 点击 drop_all_tables 应该跳转到:")
    print("  文件: services/init_db.py")
    print("  行号: 102")
    print(f"  实际位置: {drop_all_tables.__module__}")

    print("\n" + "=" * 70)
    print("如果所有跳转都正确，说明 IDE 配置成功！")
    print("=" * 70)

if __name__ == "__main__":
    test_alias_import()
