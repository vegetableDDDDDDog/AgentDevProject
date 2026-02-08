#!/usr/bin/env python3
"""查看 SQLite 聊天历史数据库的便捷工具"""

import os
import sqlite3
import argparse

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "chat_history.db")


def view_all():
    """查看所有消息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, session_id, type, content, timestamp FROM chat_messages ORDER BY id')

    print("\n📋 所有对话记录：")
    print("=" * 80)

    rows = cursor.fetchall()
    if not rows:
        print("（空）")
    else:
        for row in rows:
            print(f"[{row[0]}] [{row[1]}] {row[2]}: {row[3]}")

    print(f"\n总计：{len(rows)} 条消息\n")
    conn.close()


def view_sessions():
    """查看所有会话"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT session_id, COUNT(*) as count,
               MIN(timestamp) as start_time,
               MAX(timestamp) as end_time
        FROM chat_messages
        GROUP BY session_id
    ''')

    print("\n📁 会话列表：")
    print("=" * 80)

    rows = cursor.fetchall()
    if not rows:
        print("（空）")
    else:
        for row in rows:
            print(f"会话: {row[0]:20} | 消息数: {row[1]:3} | 开始: {row[2]} | 结束: {row[3]}")

    print(f"\n总计：{len(rows)} 个会话\n")
    conn.close()


def view_session(session_id: str):
    """查看特定会话的消息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT type, content, timestamp
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY id
    ''', (session_id,))

    print(f"\n💬 会话 [{session_id}] 的记录：")
    print("=" * 80)

    rows = cursor.fetchall()
    if not rows:
        print("（该会话无记录）")
    else:
        for row in rows:
            print(f"[{row[2]}] {row[0]}: {row[1]}")

    print(f"\n总计：{len(rows)} 条消息\n")
    conn.close()


def stats():
    """显示统计信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 总消息数
    cursor.execute('SELECT COUNT(*) FROM chat_messages')
    total = cursor.fetchone()[0]

    # 会话数
    cursor.execute('SELECT COUNT(DISTINCT session_id) FROM chat_messages')
    sessions = cursor.fetchone()[0]

    # 按类型统计
    cursor.execute('SELECT type, COUNT(*) FROM chat_messages GROUP BY type')
    type_stats = cursor.fetchall()

    print("\n📊 数据库统计：")
    print("=" * 80)
    print(f"总消息数：{total}")
    print(f"会话数：{sessions}")
    print("\n消息类型分布：")
    for msg_type, count in type_stats:
        print(f"  - {msg_type}: {count}")
    print()

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="查看 SQLite 聊天历史")
    parser.add_argument('-a', '--all', action='store_true', help='查看所有消息')
    parser.add_argument('-s', '--sessions', action='store_true', help='查看所有会话')
    parser.add_argument('-i', '--id', type=str, help='查看指定会话 ID 的消息')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')

    args = parser.parse_args()

    if args.stats:
        stats()
    elif args.sessions:
        view_sessions()
    elif args.id:
        view_session(args.id)
    elif args.all:
        view_all()
    else:
        # 默认显示统计信息
        stats()
        print("提示：使用 -h 查看更多选项")
