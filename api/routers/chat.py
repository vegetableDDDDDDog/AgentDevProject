"""
Chat Router - SSE Streaming Chat Completions

提供基于 SSE 的流式聊天接口，支持真实 LLM 和多租户隔离。
"""

import time
import asyncio
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as SQLSession

from api.schemas import ChatRequest, ChatHistoryResponse, ChatMessage
from api.sse_protocol import (
    SSEMessage,
    SSEThought,
    SSEError,
    SSEDone,
    SSEEventType,
    create_sse_event
)
from services.agent_factory import get_agent, is_registered
from services.session_service import SessionService
from services.tenant_query import get_tenant_messages
from api.middleware.db_middleware import get_db
from api.middleware.auth_middleware import get_current_auth_user, get_current_tenant_id
from api.middleware.tenant_middleware import get_tenant_context
from services.database import Session as SessionModel


router = APIRouter(prefix="/chat", tags=["Chat"])


# ============================================================================
# 流式响应生成器
# ============================================================================

async def stream_agent_response(
    agent_type: str,
    message: str,
    session_id: str,
    tenant_id: str,
    tenant_context,
    service: SessionService
) -> AsyncGenerator[str, None]:
    """
    流式输出 Agent 执行结果（SSE）

    支持真实 LLM Agent 的流式输出和模拟 Agent 的分块输出。

    Args:
        agent_type: Agent 类型
        message: 用户消息
        session_id: 会话 ID
        tenant_id: 租户 ID
        tenant_context: 租户上下文
        service: SessionService 实例

    Yields:
        SSE 格式的事件字符串
    """
    start_time = time.time()
    tokens_used = 0

    try:
        # 1. 发送思考事件 - Agent 开始执行
        yield create_sse_event(
            SSEEventType.THOUGHT,
            {"content": f"使用 Agent: {agent_type}", "step": 0}
        )

        # 2. 验证 Agent 已注册
        if not is_registered(agent_type):
            available = ", ".join(list_registered_agents())
            raise ValueError(f"未知的 Agent 类型: {agent_type}，可用: {available}")

        # 3. 获取 Agent 实例
        agent = get_agent(agent_type)

        # 4. 添加用户消息到会话
        service.add_message(
            session_id=session_id,
            role="user",
            content=message,
            tenant_id=tenant_id
        )

        # 5. 获取对话历史
        messages = service.get_messages(
            session_id=session_id,
            tenant_id=tenant_id,
            limit=100
        )

        # 转换为历史格式（排除最后一条用户消息，因为它是刚刚添加的）
        history = []
        for msg in messages[:-1]:  # 排除刚添加的用户消息
            history.append({
                "role": msg.role,
                "content": msg.content
            })

        # 6. 执行 Agent
        context = {
            "history": history,
            "session_id": session_id,
            "tenant_id": tenant_id
        }

        # 如果是真实 LLM Agent，传递租户上下文
        if agent_type in ["llm_chat", "llm_single_turn"]:
            # 更新 Agent 配置，添加租户上下文
            if hasattr(agent, 'config'):
                agent.config["tenant_context"] = tenant_context
            else:
                # 重新创建 Agent 实例（带租户上下文）
                agent = get_agent(agent_type, config={"tenant_context": tenant_context})

            # 检查 Agent 是否支持流式输出
            if hasattr(agent, 'stream_execute'):
                # 使用真实 LLM 流式输出
                response_text = ""
                async for chunk_data in agent.stream_execute(message, context):
                    if chunk_data.get("type") == "content":
                        content = chunk_data.get("content", "")
                        response_text += content
                        # 实时流式输出
                        yield SSEMessage(content=content, type="text").to_sse()
                    elif chunk_data.get("type") == "done":
                        response_text = chunk_data.get("content", response_text)
                        break

                tokens_used = estimate_tokens(response_text)

            else:
                # 使用同步调用
                result = await agent.execute(message, context)
                response_text = result.get("response", "")
                tokens_used = result.get("tokens_used", estimate_tokens(response_text))

                # 模拟流式输出（分块发送）
                chunk_size = 5
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i + chunk_size]
                    yield SSEMessage(content=chunk, type="text").to_sse()
                    await asyncio.sleep(0.02)

        else:
            # 模拟 Agent（非真实 LLM）
            result = await agent.execute(message, context)
            response_text = result.get("response", "")
            tokens_used = result.get("tokens_used", 0)

            # 模拟流式输出
            chunk_size = 5
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield SSEMessage(content=chunk, type="text").to_sse()
                await asyncio.sleep(0.02)

        # 7. 添加助手响应到会话
        service.add_message(
            session_id=session_id,
            role="assistant",
            content=response_text,
            tokens_used=tokens_used,
            tenant_id=tenant_id
        )

        # 8. 记录执行日志
        execution_time = int((time.time() - start_time) * 1000)
        service.log_execution(
            session_id=session_id,
            agent_type=agent_type,
            task=message[:100],
            status="success",
            execution_time_ms=execution_time,
            tenant_id=tenant_id
        )

        # 9. 发送完成事件
        yield SSEDone(
            session_id=session_id,
            tokens_used=tokens_used,
            execution_time_ms=execution_time
        ).to_sse()

    except Exception as e:
        # 记录错误日志
        execution_time = int((time.time() - start_time) * 1000)
        service.log_execution(
            session_id=session_id,
            agent_type=agent_type,
            task=message[:100],
            status="error",
            error_message=str(e),
            execution_time_ms=execution_time,
            tenant_id=tenant_id
        )

        # 发送错误事件
        yield SSEError(
            message=str(e),
            code="AGENT_EXECUTION_ERROR"
        ).to_sse()


# ============================================================================
# 辅助函数
# ============================================================================

def list_registered_agents() -> list:
    """获取已注册的 Agent 列表"""
    from services.agent_factory import agent_registry
    return list(agent_registry.keys())


def estimate_tokens(text: str) -> int:
    """
    估算 Token 数量

    简单估算：中文约 1 token ≈ 1.5 字符，英文约 1 token ≈ 4 字符

    Args:
        text: 文本内容

    Returns:
        估算的 Token 数
    """
    # 简单估算：平均 1 token ≈ 2 字符
    return max(1, int(len(text) / 2))


# ============================================================================
# 端点实现
# ============================================================================

@router.post(
    "/completions",
    summary="流式聊天补全",
    description="向 Agent 发送消息，通过 SSE 接收流式响应"
)
async def chat_completion(
    request: ChatRequest,
    db: SQLSession = Depends(get_db),
    auth_user: dict = Depends(get_current_auth_user),
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_context = Depends(get_tenant_context)
) -> StreamingResponse:
    """
    流式聊天补全

    创建会话（如果未提供 session_id），执行 Agent，
    通过 SSE 流式输出响应。

    支持的 Agent 类型：
    - llm_chat: 真实 LLM 聊天（需要租户配置 API Key）
    - llm_single_turn: 单轮 LLM 聊天
    - mock_chat_agent: 模拟聊天（测试用）
    - echo_agent: 回声 Agent（测试用）

    Args:
        request: 聊天请求
        db: 数据库会话
        auth_user: 认证用户
        tenant_id: 租户 ID
        tenant_context: 租户上下文

    Returns:
        SSE 流式响应

    Example:
        POST /api/v1/chat/completions
        {
            "agent_type": "llm_chat",
            "message": "你好"
        }
    """
    # 验证 Agent 类型
    if not is_registered(request.agent_type):
        available = ", ".join(list_registered_agents())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"未知的 Agent 类型 '{request.agent_type}'，可用: {available}"
        )

    # 验证真实 LLM Agent 的配置
    if request.agent_type in ["llm_chat", "llm_single_turn"]:
        # 检查租户是否配置了 LLM API Key
        api_key = tenant_context.get_setting("llm_api_key")
        base_url = tenant_context.get_setting("llm_base_url")

        if not api_key or not base_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "LLM_NOT_CONFIGURED",
                    "message": "租户未配置 LLM，请在租户设置中配置 llm_api_key 和 llm_base_url",
                    "code": "llm_001"
                }
            )

    # 创建或获取会话
    service = SessionService()

    if request.session_id:
        # 验证会话存在且属于当前租户
        session = service.get_session(request.session_id)
        if not session or session.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        session_id = request.session_id
    else:
        # 创建新会话
        session = service.create_session(
            agent_type=request.agent_type,
            config=request.config,
            tenant_id=tenant_id
        )
        session_id = session.id

    # 返回 SSE 流
    return StreamingResponse(
        stream_agent_response(
            agent_type=request.agent_type,
            message=request.message,
            session_id=session_id,
            tenant_id=tenant_id,
            tenant_context=tenant_context,
            service=service
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get(
    "/history",
    response_model=ChatHistoryResponse,
    summary="获取会话历史",
    description="获取指定会话的所有消息"
)
async def get_chat_history(
    session_id: str,
    db: SQLSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
) -> ChatHistoryResponse:
    """
    获取会话聊天历史

    自动验证租户权限，只返回属于当前租户的消息。

    Args:
        session_id: 会话 UUID
        db: 数据库会话
        tenant_id: 租户 ID

    Returns:
        ChatHistoryResponse: 会话信息和消息列表

    Raises:
        HTTPException 404: 会话不存在
    """
    from services.tenant_query import TenantQuery

    # 使用 TenantQuery 验证会话权限
    session = TenantQuery.get_by_id_or_404(
        db, SessionModel, session_id, tenant_id, "会话"
    )

    # 获取消息（自动过滤租户）
    messages = get_tenant_messages(
        db=db,
        session_id=session_id,
        tenant_id=tenant_id
    )

    return ChatHistoryResponse(
        session_id=session.id,
        agent_type=session.agent_type,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            ChatMessage(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                tokens_used=msg.tokens_used,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    )
