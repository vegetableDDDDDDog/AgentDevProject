"""
工具配置 API

提供工具列表、使用统计、配置管理等端点。
"""
import time
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func

from api.schemas.tool import (
    ToolResponse,
    ToolUsageResponse,
    ToolConfigRequest,
    ToolConfigResponse
)
from api.middleware.auth_middleware import (
    get_current_auth_user,
    get_current_tenant_id
)
from api.middleware.tenant_middleware import get_tenant_context
from services.database import get_db, SessionLocal, ToolCallLog
from services.tool_registry import ToolRegistry
from services.quota_service import QuotaService

router = APIRouter(prefix="/tools", tags=["Tools"])


# ============================================================================
# 端点
# ============================================================================

@router.get(
    "",
    response_model=List[ToolResponse],
    summary="获取租户可用工具列表",
    description="返回当前租户可用的工具列表，包含配额信息"
)
async def list_tools(
    auth_user: dict = Depends(get_current_auth_user),
    tenant_id: str = Depends(get_current_tenant_id),
    context: Any = Depends(get_tenant_context)
) -> List[ToolResponse]:
    """
    获取租户可用工具列表

    根据租户配置返回可用的工具列表，包括配额使用情况。

    Args:
        auth_user: 认证用户信息
        tenant_id: 租户 ID
        context: 租户上下文

    Returns:
        工具列表，包含配额信息

    示例:
        GET /api/v1/tools
    """
    # 获取数据库会话
    db = SessionLocal()

    try:
        tool_registry = ToolRegistry()
        quota_service = QuotaService(db)

        # 获取工具列表
        tools = tool_registry.get_tools_for_tenant(
            tenant_id=tenant_id,
            tenant_settings=context.settings,
            db=db
        )

        # 构建响应
        response = []
        for tool in tools:
            quota_info = quota_service.get_quota_info(tenant_id, tool.name)

            quota_limit = quota_info.get('max_calls_per_day') if quota_info else None
            quota_used = quota_info.get('current_day_calls') if quota_info else None
            quota_remaining = (
                quota_limit - quota_used
                if quota_limit is not None and quota_used is not None
                else None
            )

            response.append(ToolResponse(
                name=tool.name,
                display_name=tool.name.replace('_', ' ').title(),
                description=tool.description,
                enabled=True,
                quota_limit=quota_limit,
                quota_used=quota_used,
                quota_remaining=quota_remaining
            ))

        return response

    finally:
        db.close()


@router.get(
    "/usage",
    response_model=ToolUsageResponse,
    summary="获取工具使用统计",
    description="返回工具调用的统计数据，包括总次数、按工具分组、成功率"
)
async def get_tool_usage(
    auth_user: dict = Depends(get_current_auth_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: SessionLocal = Depends(get_db)
) -> ToolUsageResponse:
    """
    获取工具使用统计

    返回工具调用的统计数据，包括总次数、按工具分组统计、成功率。

    Args:
        auth_user: 认证用户信息
        tenant_id: 租户 ID
        db: 数据库会话

    Returns:
        使用统计数据

    示例:
        GET /api/v1/tools/usage
    """
    # 总调用次数
    total = db.query(func.count(ToolCallLog.id)).filter(
        ToolCallLog.tenant_id == tenant_id
    ).scalar()

    # 按工具分组统计
    by_tool_result = db.query(
        ToolCallLog.tool_name,
        func.count(ToolCallLog.id).label('count')
    ).filter(
        ToolCallLog.tenant_id == tenant_id
    ).group_by(ToolCallLog.tool_name).all()

    by_tool = {tool: count for tool, count in by_tool_result}

    # 成功率
    success_count = db.query(func.count(ToolCallLog.id)).filter(
        ToolCallLog.tenant_id == tenant_id,
        ToolCallLog.status == 'success'
    ).scalar()

    success_rate = success_count / total if total > 0 else 0.0

    return ToolUsageResponse(
        total_calls=total or 0,
        by_tool=by_tool,
        success_rate=round(success_rate, 4)
    )


@router.get(
    "/config",
    response_model=ToolConfigResponse,
    summary="获取工具配置",
    description="返回当前租户的工具配置（API Key 会脱敏）"
)
async def get_tool_config(
    auth_user: dict = Depends(get_current_auth_user),
    context: Any = Depends(get_tenant_context)
) -> ToolConfigResponse:
    """
    获取工具配置

    返回当前租户的工具配置。敏感信息（如 API Key）会脱敏。

    Args:
        auth_user: 认证用户信息
        context: 租户上下文

    Returns:
        工具配置

    示例:
        GET /api/v1/tools/config
    """
    settings = context.settings or {}

    # 脱敏 API Key
    api_key = settings.get('tavily_api_key')
    masked_key = None
    if api_key and len(api_key) > 8:
        masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]

    return ToolConfigResponse(
        enable_search=settings.get('enable_search', True),
        enable_math=settings.get('enable_math', True),
        tavily_api_key=masked_key
    )


@router.put(
    "/config",
    response_model=ToolConfigResponse,
    summary="更新工具配置",
    description="更新租户的工具配置（注意：此端点为占位实现）"
)
async def update_tool_config(
    request: ToolConfigRequest,
    auth_user: dict = Depends(get_current_auth_user),
    tenant_id: str = Depends(get_current_tenant_id),
    context: Any = Depends(get_tenant_context),
    db: SessionLocal = Depends(get_db)
) -> ToolConfigResponse:
    """
    更新工具配置

    更新租户的工具配置。

    注意：这是一个简化实现，实际应该更新 tenants.settings 字段。

    Args:
        request: 工具配置请求
        auth_user: 认证用户信息
        tenant_id: 租户 ID
        context: 租户上下文
        db: 数据库会话

    Returns:
        更新后的工具配置

    示例:
        PUT /api/v1/tools/config
        {
            "enable_search": true,
            "enable_math": true
        }
    """
    # TODO: 完整实现需要更新 tenants.settings 字段
    # 这里返回占位响应

    return ToolConfigResponse(
        enable_search=request.enable_search,
        enable_math=request.enable_math,
        tavily_api_key="***"  # 实际应返回更新后的值
    )


# ============================================================================
# 健康检查
# ============================================================================

@router.get(
    "/health",
    summary="工具服务健康检查",
    description="检查工具服务是否正常运行"
)
async def health_check() -> Dict[str, Any]:
    """工具服务健康检查"""
    return {
        "service": "tools",
        "status": "healthy",
        "timestamp": time.time()
    }
