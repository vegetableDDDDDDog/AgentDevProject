"""
Sessions Router - Session Management

提供会话管理端点，支持租户隔离。
所有会话操作都自动应用租户过滤，确保数据安全。
"""

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as SQLSession

from api.schemas import (
    SessionCreateRequest,
    SessionResponse,
    SessionListResponse
)
from services.session_service import SessionService
from services.tenant_query import TenantQuery
from api.middleware.db_middleware import get_db
from api.middleware.auth_middleware import get_current_auth_user, get_current_tenant_id
from api.middleware.tenant_middleware import get_tenant_context, require_active_tenant


router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ============================================================================
# 端点实现
# ============================================================================

@router.post(
    "",
    response_model=SessionResponse,
    summary="创建新会话",
    description="为指定 Agent 类型创建新的对话会话"
)
async def create_session(
    request: SessionCreateRequest,
    db: SQLSession = Depends(get_db),
    auth_user: dict = Depends(get_current_auth_user),
    tenant_id: str = Depends(get_current_tenant_id),
    is_active: bool = Depends(require_active_tenant)
) -> SessionResponse:
    """
    创建新的对话会话

    自动关联当前租户，确保租户隔离。

    Args:
        request: 会话创建请求（包含 agent_type 和可选配置）
        db: 数据库会话
        auth_user: 认证用户信息
        tenant_id: 租户 ID
        is_active: 租户激活状态

    Returns:
        SessionResponse: 创建的会话详情
    """
    service = SessionService()

    # 创建会话（SessionService 会自动添加 tenant_id）
    session = service.create_session(
        agent_type=request.agent_type,
        config=request.config,
        metadata=request.metadata,
        tenant_id=tenant_id  # 传递租户 ID
    )

    return SessionResponse(
        id=session.id,
        agent_type=session.agent_type,
        config=session.config,
        metadata=session.meta,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0
    )


@router.get(
    "",
    response_model=SessionListResponse,
    summary="列出会话",
    description="获取当前租户的所有会话列表，支持按 Agent 类型过滤"
)
async def list_sessions(
    agent_type: Optional[str] = None,
    limit: int = 100,
    db: SQLSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
) -> SessionListResponse:
    """
    列出会话

    自动过滤当前租户的会话，防止跨租户数据泄露。

    Args:
        agent_type: 可选的 Agent 类型过滤
        limit: 最大返回数量（默认 100，最大 1000）
        db: 数据库会话
        tenant_id: 租户 ID

    Returns:
        SessionListResponse: 会话列表
    """
    # 使用 TenantQuery 自动过滤租户
    query = TenantQuery.filter_by_tenant(db, Session, tenant_id)

    if agent_type:
        query = query.filter(Session.agent_type == agent_type)

    # 按创建时间倒序
    query = query.order_by(Session.created_at.desc())

    # 限制数量
    if limit > 1000:
        limit = 1000
    sessions = query.limit(limit).all()

    # 获取消息计数
    service = SessionService()
    result_sessions = []
    for s in sessions:
        # 验证会话属于当前租户（TenantQuery 已保证）
        messages = service.get_messages(s.id, tenant_id=tenant_id, limit=1000)
        message_count = len(messages)

        result_sessions.append(
            SessionResponse(
                id=s.id,
                agent_type=s.agent_type,
                config=s.config,
                metadata=s.meta,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=message_count
            )
        )

    return SessionListResponse(
        sessions=result_sessions,
        count=len(sessions)
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="获取会话详情",
    description="获取指定会话的详细信息，自动验证租户权限"
)
async def get_session(
    session_id: str,
    db: SQLSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
) -> SessionResponse:
    """
    获取会话详情

    使用 TenantQuery.get_by_id_or_404 自动验证租户权限，
    如果会话不属于当前租户，返回 404。

    Args:
        session_id: 会话 UUID
        db: 数据库会话
        tenant_id: 租户 ID

    Returns:
        SessionResponse: 会话详情

    Raises:
        HTTPException 404: 会话不存在或不属于当前租户
    """
    # 使用 TenantQuery 自动验证租户权限
    session = TenantQuery.get_by_id_or_404(
        db, Session, session_id, tenant_id, "会话"
    )

    # 获取消息
    service = SessionService()
    messages = service.get_messages(session_id, tenant_id=tenant_id, limit=1000)

    return SessionResponse(
        id=session.id,
        agent_type=session.agent_type,
        config=session.config,
        metadata=session.meta,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(messages)
    )


@router.delete(
    "/{session_id}",
    summary="删除会话",
    description="删除指定会话及其所有消息，自动验证租户权限"
)
async def delete_session(
    session_id: str,
    db: SQLSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
) -> dict:
    """
    删除会话

    使用 TenantQuery 自动验证租户权限。

    Args:
        session_id: 会话 UUID
        db: 数据库会话
        tenant_id: 租户 ID

    Returns:
        删除成功消息

    Raises:
        HTTPException 404: 会话不存在或不属于当前租户
    """
    # 使用 TenantQuery 自动验证租户权限
    session = TenantQuery.get_by_id_or_404(
        db, Session, session_id, tenant_id, "会话"
    )

    # TODO: 实现删除逻辑（需要在 SessionService 中添加）
    # service.delete_session(session_id, tenant_id)

    return {
        "message": "会话删除功能待实现",
        "session_id": session_id
    }


# 导入 Session 模型（用于类型提示）
from services.database import Session
