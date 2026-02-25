"""
监控中间件 - 自动收集请求指标

为每个请求自动记录指标。
"""

from typing import Callable
from fastapi import Request, Response
from time import time

from api.metrics import (
    requests_total,
    chat_requests_total,
    errors_total,
    active_sessions,
    chat_duration_seconds,
    token_usage_total
)


async def metrics_middleware(request: Request, call_next: Callable):
    """
    监控中间件

    自动记录：
    - 请求总数
    - 请求延迟
    - 错误数
    - 聊天请求数

    Args:
        request: FastAPI 请求对象
        call_next: 下一个中间件或路由

    Returns:
        Response 对象
    """
    start_time = time.time()

    # 记录请求开始
    requests_total.inc()

    # 如果是聊天请求，增加聊天计数
    if "/chat/completions" in request.url.path:
        chat_requests_total.inc()

    # 处理请求
    try:
        response = await call_next(request)

        # 记录延迟
        duration = time.time() - start_time
        chat_duration_seconds.observe(duration)

        return response

    except Exception as e:
        # 记录错误
        errors_total.inc()

        # 重新抛出异常
        raise


# ============================================================================
# 指标更新辅助函数
# ============================================================================

def increment_active_sessions():
    """增加活跃会话数"""
    active_sessions.inc()


def decrement_active_sessions():
    """减少活跃会话数"""
    active_sessions.dec()


def record_token_usage(tenant_id: str, tokens: int):
    """
    记录 Token 使用量

    Args:
        tenant_id: 租户 ID
        tokens: Token 数量
    """
    token_usage_total.inc(tokens)
    metrics_store.add_tokens_used(tenant_id, tokens)
