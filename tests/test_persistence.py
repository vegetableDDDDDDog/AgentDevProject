#!/usr/bin/env python3
"""测试 SQLite 持久化存储功能"""

import os
import sys
import sqlite3
import json
from langchain_core.messages import HumanMessage, AIMessage

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 获取数据库路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "chat_history.db")

# 删除旧数据库
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("🗑️  已清除旧数据库")

# 导入 chat_agent 中的类
from agents.chat_agent import SQLiteChatMessageHistory, get_session_history

# 测试 1: 创建会话并添加消息
print("\n--- 测试 1: 添加消息 ---")
session_id = "test_user_1"
history = SQLiteChatMessageHistory(session_id)

history.add_message(HumanMessage(content="你好，我是测试用户"))
history.add_message(AIMessage(content="你好，我是贾维斯"))
history.add_message(HumanMessage(content="记得我吗？"))

print(f"✅ 已添加 3 条消息到会话 {session_id}")

# 测试 2: 直接查询数据库
print("\n--- 测试 2: 查询数据库 ---")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('SELECT session_id, type, content FROM chat_messages ORDER BY id')
rows = cursor.fetchall()
print(f"✅ 数据库中共有 {len(rows)} 条消息:")
for row in rows:
    print(f"  [{row[0]}] {row[1]}: {row[2]}")
conn.close()

# 测试 3: 模拟程序重启 - 创建新对象读取历史
print("\n--- 测试 3: 模拟程序重启 ---")
print("🔄 清除内存缓存，重新创建对象...")
from chat_agent import store
store.clear()  # 清除内存缓存

# 重新获取会话历史（模拟程序重启）
new_history = get_session_history(session_id)
messages = new_history.messages
print(f"✅ 从数据库读取到 {len(messages)} 条消息:")
for msg in messages:
    print(f"  [{msg.type}]: {msg.content}")

# 测试 4: 测试清空功能
print("\n--- 测试 4: 测试清空功能 ---")
new_history.clear()
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM chat_messages')
count = cursor.fetchone()[0]
conn.close()
print(f"✅ 清空后，数据库中剩余 {count} 条消息")

print("\n🎉 所有测试完成！")
