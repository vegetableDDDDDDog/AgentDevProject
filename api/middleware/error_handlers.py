"""
错误处理器 - 统一异常处理

将自定义异常转换为 HTTP 响应，提供一致的错误消息格式。
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from services.exceptions import (
    AuthException,
    UserNotFoundException,
    InvalidCredentialsException,
    TokenExpiredException,
    TokenInvalidException,
    TenantSelectionRequiredException,
    UserSuspendedException,
    TenantNotFoundException,
    TenantSuspendedException,
    QuotaException,
    QuotaExceededException,
    AgentException
)


# ============================================================================
# 异常到 HTTP 状态码映射
# ============================================================================

exception_to_status_code = {
    # 认证异常
    InvalidCredentialsException: status.HTTP_401_UNAUTHORIZED,
    TokenExpiredException: status.HTTP_401_UNAUTHORIZED,
    TokenInvalidException: status.HTTP_401_UNAUTHORIZED,
    UserSuspendedException: status.HTTP_403_FORBIDDEN,
    UserNotFoundException: status.HTTP_404_NOT_FOUND,
    TenantSelectionRequiredException: status.HTTP_202_ACCEPTED,

    # 租户异常
    TenantNotFoundException: status.HTTP_404_NOT_FOUND,
    TenantSuspendedException: status.HTTP_403_FORBIDDEN,

    # 配额异常
    QuotaExceededException: status.HTTP_429_TOO_MANY_REQUESTS,
}


# ============================================================================
# FastAPI 异常处理器
# ============================================================================

async def auth_exception_handler(request: Request, exc: AuthException) -> JSONResponse:
    """
    处理所有认证相关异常

    Args:
        request: FastAPI 请求对象
        exc: 认证异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    # 获取 HTTP 状态码
    status_code = exception_to_status_code.get(
        type(exc),
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    # 构建错误响应
    error_response = {
        "error": exc.code or "AUTH_ERROR",
        "message": exc.message,
        "code": exc.code
    }

    # Token 过期特殊处理：添加 WWW-Authenticate Header
    if isinstance(exc, (TokenExpiredException, TokenInvalidException)):
        return JSONResponse(
            status_code=status_code,
            content=error_response,
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""}
        )

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def tenant_exception_handler(request: Request, exc: TenantException) -> JSONResponse:
    """
    处理所有租户相关异常

    Args:
        request: FastAPI 请求对象
        exc: 租户异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    status_code = exception_to_status_code.get(
        type(exc),
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.code or "TENANT_ERROR",
            "message": exc.message,
            "code": exc.code
        }
    )


async def quota_exception_handler(request: Request, exc: QuotaException) -> JSONResponse:
    """
    处理所有配额相关异常

    Args:
        request: FastAPI 请求对象
        exc: 配额异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    status_code = exception_to_status_code.get(
        type(exc),
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.code or "QUOTA_ERROR",
            "message": exc.message,
            "code": exc.code
        }
    )


async def agent_exception_handler(request: Request, exc: AgentException) -> JSONResponse:
    """
    处理所有 Agent 平台异常（兜底处理器）

    Args:
        request: FastAPI 请求对象
        exc: Agent 平台异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": exc.code or "INTERNAL_ERROR",
            "message": exc.message,
            "code": exc.code,
            "path": str(request.url.path)
        }
    )


# ============================================================================
# 注册异常处理器的函数
# ============================================================================

def register_exception_handlers(app):
    """
    为 FastAPI 应用注册所有异常处理器

    Args:
        app: FastAPI 应用实例

    示例:
        from api.middleware import error_handlers
        from fastapi import FastAPI

        app = FastAPI()
        error_handlers.register_exception_handlers(app)
    """
    # 认证异常
    app.add_exception_handler(AuthException, auth_exception_handler)

    # 租户异常
    app.add_exception_handler(TenantException, tenant_exception_handler)

    # 配额异常
    app.add_exception_handler(QuotaException, quota_exception_handler)

    # Agent 平台异常（兜底）
    app.add_exception_handler(AgentException, agent_exception_handler)


# ============================================================================
# HTTPException 处理器（FastAPI 内置异常）
# ============================================================================

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    处理 FastAPI 内置的 HTTPException

    Args:
        request: FastAPI 请求对象
        exc: HTTPException

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
        headers=getattr(exc, "headers", None)
    )
