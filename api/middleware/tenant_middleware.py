"""
租户隔离中间件 - 租户上下文注入和验证

从 JWT token 中提取租户 ID，获取租户上下文，
检查租户状态，注入到 request.state。
"""

from typing import Callable
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session as SQLSession

from services.tenant_service import TenantService
from services.exceptions import TenantNotFoundException, TenantSuspendedException
from api.middleware.db_middleware import get_db


async def tenant_middleware(
    request: Request,
    call_next: Callable
):
    """
    租户隔离中间件

    处理流程:
    1. 从 request.state.auth_user 获取 tenant_id（由认证中间件注入）
    2. 从 request.state.db 获取数据库会话（由数据库中间件注入）
    3. 调用 TenantService 获取租户上下文
    4. 检查租户状态（active/suspended/deleted）
    5. 将 tenant_context 注入到 request.state
    6. 继续处理请求

    使用:
        app.middleware("http")(tenant_middleware)

    中间件顺序:
        app.middleware("http")(db_middleware)
        app.middleware("http")(tenant_middleware)

    在路由中访问:
        @router.get("/api/sessions")
        async def list_sessions(request: Request):
            context = request.state.tenant_context
            return {
                "tenant": context.display_name,
                "plan": context.plan
            }
    """
    # 获取认证用户（由认证中间件注入）
    auth_user = getattr(request.state, 'auth_user', None)

    if not auth_user:
        # 未认证请求，直接放行（由路由的 Depends 处理）
        response = await call_next(request)
        return response

    tenant_id = auth_user.get('tenant_id')

    if not tenant_id:
        # Token 中没有 tenant_id，直接放行（由路由处理）
        response = await call_next(request)
        return response

    # 获取数据库会话（由数据库中间件注入）
    db = getattr(request.state, 'db', None)

    if not db:
        # 数据库会话未注入，直接放行
        response = await call_next(request)
        return response

    try:
        # 获取租户上下文
        tenant_service = TenantService()
        tenant_context = tenant_service.get_tenant_context(db, tenant_id)

        # 注入到 request.state
        request.state.tenant_context = tenant_context

        # 继续处理请求
        response = await call_next(request)
        return response

    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "TENANT_NOT_FOUND",
                "message": "租户不存在",
                "code": "tenant_001"
            }
        )

    except TenantSuspendedException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "TENANT_SUSPENDED",
                "message": "租户已被暂停",
                "code": "tenant_002"
            }
        )


# ============================================================================
# 依赖注入函数（供路由使用）
# ============================================================================

async def get_tenant_context(
    request: Request,
    db: SQLSession = Depends(get_db)
):
    """
    获取租户上下文（依赖注入）

    这是一个 FastAPI 依赖注入函数，用于在路由中获取租户上下文。
    要求请求必须已认证（通过 get_current_auth_user）。

    Args:
        request: FastAPI 请求对象
        db: 数据库会话

    Returns:
        TenantContext 对象

    Raises:
        HTTPException 401: 未认证
        HTTPException 404: 租户不存在
        HTTPException 403: 租户被暂停

    示例:
        @router.get("/api/me")
        async def get_me(
            auth_user: dict = Depends(get_current_auth_user),
            context: TenantContext = Depends(get_tenant_context)
        ):
            return {
                "user": auth_user,
                "tenant": {
                    "name": context.display_name,
                    "plan": context.plan
                }
            }
    """
    # 先检查是否已被中间件设置
    context = getattr(request.state, 'tenant_context', None)

    if context:
        return context

    # 如果中间件没有设置，手动获取
    # 获取认证用户
    auth_user = getattr(request.state, 'auth_user', None)

    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "需要认证",
                "code": "auth_001"
            }
        )

    tenant_id = auth_user.get('tenant_id')

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TENANT_ID_MISSING",
                "message": "Token 中缺少租户 ID",
                "code": "auth_009"
            }
        )

    try:
        # 手动获取租户上下文
        tenant_service = TenantService()
        tenant_context = tenant_service.get_tenant_context(db, tenant_id)

        # 缓存到 request.state
        request.state.tenant_context = tenant_context

        return tenant_context

    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "TENANT_NOT_FOUND",
                "message": "租户不存在",
                "code": "tenant_001"
            }
        )

    except TenantSuspendedException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "TENANT_SUSPENDED",
                "message": "租户已被暂停",
                "code": "tenant_002"
            }
        )


async def require_active_tenant(
    request: Request,
    db: SQLSession = Depends(get_db)
) -> bool:
    """
    要求租户处于激活状态（依赖注入）

    检查当前租户是否激活，如果非激活则抛出异常。

    Args:
        request: FastAPI 请求对象
        db: 数据库会话

    Returns:
        True （租户激活）

    Raises:
        HTTPException 403: 租户非激活状态

    示例:
        @router.post("/api/sessions")
        async def create_session(
            is_active: bool = Depends(require_active_tenant)
        ):
            # 只有激活租户才能创建会话
            pass
    """
    # 获取认证用户
    auth_user = getattr(request.state, 'auth_user', None)

    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "需要认证",
                "code": "auth_001"
            }
        )

    tenant_id = auth_user.get('tenant_id')

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TENANT_ID_MISSING",
                "message": "Token 中缺少租户 ID",
                "code": "auth_009"
            }
        )

    # 直接使用 TenantService 检查租户状态
    try:
        tenant_service = TenantService()
        tenant_context = tenant_service.get_tenant_context(db, tenant_id)

        if not tenant_context.is_active():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "TENANT_NOT_ACTIVE",
                    "message": "租户未激活",
                    "code": "tenant_005"
                }
            )

        return True

    except TenantNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "TENANT_NOT_FOUND",
                "message": "租户不存在",
                "code": "tenant_001"
            }
        )

    except TenantSuspendedException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "TENANT_SUSPENDED",
                "message": "租户已被暂停",
                "code": "tenant_002"
            }
        )


# ============================================================================
# 从认证用户获取租户 ID
# ============================================================================

async def get_current_tenant_id(request: Request) -> str:
    """
    从认证用户中获取租户 ID（便捷函数）

    这是一个便捷函数，用于快速获取当前用户的租户 ID。
    通常与 get_current_auth_user 配合使用。

    Args:
        request: FastAPI 请求对象

    Returns:
        租户 ID 字符串

    示例:
        @router.get("/api/sessions")
        async def list_sessions(
            tenant_id: str = Depends(get_current_tenant_id),
            db: SQLSession = Depends(get_db)
        ):
            # 使用 tenant_id 查询数据
            sessions = db.query(Session).filter(
                Session.tenant_id == tenant_id
            ).all()
            return {"sessions": sessions}
    """
    auth_user = getattr(request.state, 'auth_user', None)

    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "需要认证",
                "code": "auth_001"
            }
        )

    return auth_user.get('tenant_id')
