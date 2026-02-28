#!/usr/bin/env python
"""
测试 API 并显示原始响应
"""
import requests
import json
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 读取配置
env_model = os.getenv('OPENAI_MODEL', '未配置')

print("=" * 60)
print("API 测试 - 显示原始响应")
print("=" * 60)
print(f"\n📋 配置信息:")
print(f"  .env 文件中的模型: {env_model}")

# 读取数据库配置
from services.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('SELECT settings FROM tenants LIMIT 1'))
    settings = json.loads(result.fetchone()[0])
    db_model = settings.get('llm_model', '未配置')
    print(f"  数据库中的模型: {db_model}")
    print(f"  ✅ 实际使用的模型: {db_model}")
print()

# 获取 token
response = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json={'email': 'test@example.com', 'password': 'test12345'}
)
token = response.json()['access_token']

# 发送聊天请求
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

data = {
    'agent_type': 'llm_chat',
    'message': '你好，请简单介绍一下你自己'
}

print(f"\n📤 发送请求:")
print(f"  URL: http://localhost:8000/api/v1/chat/completions")
print(f"  Agent: llm_chat")
print(f"  Message: 你好")
print(f"\n📥 接收 SSE 流式响应:")
print("-" * 60)

response = requests.post(
    'http://localhost:8000/api/v1/chat/completions',
    headers=headers,
    json=data,
    stream=True
)

print(f"\n状态码: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
print("\n原始 SSE 数据:")
print("-" * 60)

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        print(line)

print("\n" + "=" * 60)
