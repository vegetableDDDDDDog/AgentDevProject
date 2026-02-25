"""
认证路由 - 用户登录、登出和 token 刷新

提供用户认证相关的 API 端点，包括登录、刷新 token 等。
支持多租户歧义处理。
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as SQLSession

from api.schemas.auth import (
    LoginRequest,
    LoginWithTenantRequest,
    LoginResponse,
    TenantSelectionRequiredResponse,
    RefreshRequest,
    RefreshResponse,
    ErrorResponse
)
from services.database import get_db, SessionLocal
from services.auth_service import AuthService
from services.exceptions import (
    InvalidCredentialsException,
    TenantSelectionRequiredException,
    UserSuspendedException,
    TokenExpiredException,
    TokenInvalidException
)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ============================================================================
# 端点
# ============================================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="用户登录",
    description="通过邮箱和密码登录，返回 JWT access token 和 refresh token"
)
async def login(
    request: LoginRequest,
    db: SQLSession = Depends(get_db)
) -> LoginResponse:
    """
    用户登录接口

    通过邮箱和密码进行用户认证。如果邮箱属于多个租户，
    返回 202 Accepted 状态码和租户列表，需要用户选择租户后重新登录。

    Args:
        request: 登录请求（邮箱、密码）
        db: 数据库会话

    Returns:
        LoginResponse: 包含 access_token, refresh_token, user_info

    Raises:
        HTTPException 401: 邮箱或密码错误
        HTTPException 403: 用户被暂停

    示例:
        POST /api/auth/login
        {
            "email": "user@example.com",
            "password": "password123"
        }
    """
    auth_service = AuthService()

    try:
        # 认证用户
        result = auth_service.authenticate_user(
            db,
            request.email,
            request.password
        )

        # 成功认证
        return LoginResponse(**result)

    except TenantSelectionRequiredException as e:
        # 多租户歧义 - 返回 202 Accepted 和租户列表
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=TenantSelectionRequiredResponse(
                status="tenant_selection_required",
                message=f"您的邮箱属于 {len(e.tenants)} 个租户，请选择",
                tenants=[
                    {"id": t["id"], "name": t["name"]}
                    for t in e.tenants
                ]
            ).model_dump()
        )

    except InvalidCredentialsException:
        # 邮箱或密码错误
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error="INVALID_CREDENTIALS",
                message="邮箱或密码错误",
                code="auth_001"
            ).model_dump()
        )

    except UserSuspendedException:
        # 用户被暂停
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse(
                error="USER_SUSPENDED",
                message="用户已被暂停",
                code="auth_002"
            ).model_dump()
        )


@router.post(
    "/login/tenant",
    response_model=LoginResponse,
    summary="用户登录（指定租户）",
    description="通过邮箱、密码和租户 ID 登录，用于多租户歧义场景"
)
async def login_with_tenant(
    request: LoginWithTenantRequest,
    db: SQLSession = Depends(get_db)
) -> LoginResponse:
    """
    用户登录接口（指定租户）

    用于多租户歧义场景，用户在获取租户列表后，指定租户 ID 进行登录。

    Args:
        request: 登录请求（邮箱、密码、租户 ID）
        db: 数据库会话

    Returns:
        LoginResponse: 包含 access_token, refresh_token, user_info

    Raises:
        HTTPException 401: 邮箱、密码或租户不匹配
        HTTPException 403: 用户被暂停

    示例:
        POST /api/auth/login/tenant
        {
            "email": "user@example.com",
            "password": "password123",
            "tenant_id": "tenant-001"
        }
    """
    auth_service = AuthService()

    try:
        # 认证用户（指定租户）
        result = auth_service.authenticate_user_with_tenant(
            db,
            request.email,
            request.password,
            request.tenant_id
        )

        return LoginResponse(**result)

    except InvalidCredentialsException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error="INVALID_CREDENTIALS",
                message="邮箱、密码或租户不匹配",
                code="auth_003"
            ).model_dump()
        )

    except UserSuspendedException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse(
                error="USER_SUSPENDED",
                message="用户已被暂停",
                code="auth_002"
            ).model_dump()
        )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="刷新 Access token",
    description="使用 Refresh token 获取新的 Access token"
)
async def refresh_token(
    request: RefreshRequest,
    db: SQLSession = Depends(get_db)
) -> RefreshResponse:
    """
    刷新 Access token

    使用有效的 Refresh token 获取新的 Access token。
    Refresh token 的有效期为 7 天。

    Args:
        request: 刷新请求（refresh_token）
        db: 数据库会话

    Returns:
        RefreshResponse: 包含新的 access_token

    Raises:
        HTTPException 401: Refresh token 无效或已过期

    示例:
        POST /api/auth/refresh
        {
            "refresh_token": "eyJhbGciOi..."
        }
    """
    auth_service = AuthService()

    try:
        # 刷新 token
        new_access_token = auth_service.refresh_access_token(
            db,
            request.refresh_token
        )

        return RefreshResponse(
            access_token=new_access_token,
            token_type="bearer"
        )

    except TokenExpiredException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error="TOKEN_EXPIRED",
                message="Refresh token 已过期，请重新登录",
                code="auth_004"
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""}
        )

    except TokenInvalidException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error="TOKEN_INVALID",
                message=str(e),
                code="auth_005"
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""}
        )


@router.post(
    "/logout",
    summary="用户登出",
    description="客户端删除 token，服务端不维护状态"
)
async def logout():
    """
    用户登出接口

    这是一个无状态的登出实现。服务端不存储或标记 token，
    客户端需要自行删除本地存储的 token。

    登出后，Access token 会在 15 分钟后自动过期。

    Returns:
        成功消息

    示例:
        POST /api/auth/logout
    """
    return {
        "message": "登出成功",
        "note": "请删除客户端存储的 token"
    }


# ============================================================================
# 健康检查端点（用于测试）
# ============================================================================

@router.get(
    "/health",
    summary="认证服务健康检查",
    description="检查认证服务是否正常运行"
)
async def health_check() -> Dict[str, Any]:
    """认证服务健康检查"""
    return {
        "service": "auth",
        "status": "healthy",
        "timestamp": time.time()
    }
