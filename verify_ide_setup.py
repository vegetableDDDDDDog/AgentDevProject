#!/usr/bin/env python3
"""
IDE 跳转验证工具

这个工具会显示所有函数的详细信息，帮助您验证 IDE 配置。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("IDE 跳转验证工具")
print("=" * 70)

# 测试1: 检查导入关系
print("\n[测试 1] 检查导入和定义")
print("-" * 70)

from services.database import init_db, drop_all
from services.init_db import db_init_db, db_drop_all, initialize_database

print(f"✅ init_db 定义位置: {init_db.__code__.co_firstlineno}")
print(f"   文件: {init_db.__code__.co_filename}")

print(f"\n✅ db_init_db 定义位置: {db_init_db.__code__.co_firstlineno}")
print(f"   文件: {db_init_db.__code__.co_filename}")

print(f"\n✅ 它们是同一个函数吗? {db_init_db is init_db}")

# 测试2: 显示函数签名
print("\n[测试 2] 函数签名")
print("-" * 70)

import inspect

sig_init_db = inspect.signature(init_db)
sig_db_init_db = inspect.signature(db_init_db)

print(f"init_db 签名: {sig_init_db}")
print(f"db_init_db 签名: {sig_db_init_db}")

# 测试3: 检查调用链
print("\n[测试 3] 调用链分析")
print("-" * 70)

print("\n在 services/init_db.py 中:")
print("  db_init_db() 调用了 database.py 的 init_db()")
print(f"  定义在 database.py 第 {init_db.__code__.co_firstlineno} 行")

print("\n在 api/main.py 中:")
print("  init_db() 直接调用 database.py 的 init_db()")
print(f"  定义在 database.py 第 {init_db.__code__.co_firstlineno} 行")

# 测试4: 提供跳转建议
print("\n[测试 4] IDE 跳转建议")
print("-" * 70)

print("""
如果您在 IDE 中点击 db_init_db() 无法跳转，请尝试:

PyCharm 用户:
  方法1: 光标放在 db_init_db 上 → 按 Ctrl + B (Go to Declaration)
  方法2: 光标放在 db_init_db 上 → 按 Ctrl + Alt + B (Go to Implementation)
  方法3: 右键点击 db_init_db → Go To → Declaration
  方法4: 如果以上都不行，按 Ctrl + N 搜索 "def init_db"

VS Code 用户:
  方法1: 光标放在 db_init_db 上 → 按 F12 (Go to Definition)
  方法2: 右键点击 db_init_db → Peek Definition (Alt + F12)
  方法3: 右键点击 db_init_db → Go to Definition
  方法4: 如果以上都不行，按 Ctrl + Shift + F 搜索 "def init_db"

通用方法:
  1. 打开 services/database.py
  2. 使用 Ctrl + F 搜索 "def init_db"
  3. 跳转到第 269 行
""")

# 测试5: 创建跳转映射表
print("\n[测试 5] 完整的函数映射表")
print("-" * 70)

mapping = {
    "db_init_db": {
        "file": "services/database.py",
        "line": 269,
        "definition": "def init_db():",
        "import_from": "services.database"
    },
    "db_drop_all": {
        "file": "services/database.py",
        "line": 282,
        "definition": "def drop_all():",
        "import_from": "services.database"
    },
    "initialize_database": {
        "file": "services/init_db.py",
        "line": 119,
        "definition": "def initialize_database():",
        "import_from": "services.init_db"
    },
    "drop_all_tables": {
        "file": "services/init_db.py",
        "line": 102,
        "definition": "def drop_all_tables():",
        "import_from": "services.init_db"
    }
}

for alias, info in mapping.items():
    print(f"\n{alias}:")
    print(f"  定义在: {info['file']}:{info['line']}")
    print(f"  函数名: {info['definition']}")
    print(f"  从: {info['import_from']} 导入")

print("\n" + "=" * 70)
print("验证完成！")
print("=" * 70)
