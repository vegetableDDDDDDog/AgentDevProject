"""
认证中间件 - JWT Token 验证

提供 JWT token 验证中间件，用于保护需要认证的 API 端点。
从 Authorization Header 中提取并验证 token，将用户信息注入到 request.state。
"""

from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth_service import AuthService
from services.exceptions import TokenExpiredException, TokenInvalidException


# ============================================================================
# FastAPI HTTPBearer 安全方案
# ============================================================================

# 定义 HTTPBearer 安全方案，用于从 Authorization Header 提取 token
security = HTTPBearer(auto_error=False)


# ============================================================================
# 可选认证依赖
# ============================================================================

async def get_optional_auth_user(
    request: Request
) -> Optional[dict]:
    """
    可选认证依赖（不强制要求 token）

    从 Authorization Header 中提取并验证 token。
    如果没有 token 或 token 无效，返回 None。

    Args:
        request: FastAPI 请求对象

    Returns:
        用户信息字典，如果认证失败返回 None

    示例:
        @app.get("/api/public")
        async def public_endpoint(user = Depends(get_optional_auth_user)):
            if user:
                return f"Hello, {user['email']}"
            else:
                return "Hello, anonymous"
    """
    # 尝试从 Authorization Header 获取凭证
    credentials: HTTPAuthorizationCredentials = await security(request)

    if not credentials:
        # 没有 token
        return None

    try:
        # 验证 token
        auth_service = AuthService()
        payload = auth_service.verify_access_token(credentials.credentials)

        # 返回用户信息
        return {
            "id": payload.sub,
            "tenant_id": payload.tenant_id,
            "role": payload.role
        }

    except (TokenExpiredException, TokenInvalidException):
        # Token 无效
        return None


# ============================================================================
# 必需认证依赖
# ============================================================================

async def get_current_auth_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    必需认证依赖（强制要求 token）

    从 Authorization Header 中提取并验证 token。
    如果没有 token 或 token 无效，抛出 HTTPException。

    Args:
        request: FastAPI 请求对象
        credentials: HTTP Bearer 凭证（自动提取）

    Returns:
        用户信息字典

    Raises:
        HTTPException 401: 没有 token 或 token 无效

    示例:
        @app.get("/api/protected")
        async def protected_endpoint(user = Depends(get_current_auth_user)):
            return f"Hello, {user['email']}"
    """
    if not credentials:
        # 没有 token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "MISSING_TOKEN",
                "message": "需要认证",
                "code": "auth_006"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # 验证 token
        auth_service = AuthService()
        payload = auth_service.verify_access_token(credentials.credentials)

        # 将用户信息注入到 request.state（方便后续使用）
        request.state.auth_user = {
            "id": payload.sub,
            "tenant_id": payload.tenant_id,
            "role": payload.role
        }

        return request.state.auth_user

    except TokenExpiredException:
        # Token 已过期
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TOKEN_EXPIRED",
                "message": "Token 已过期，请刷新或重新登录",
                "code": "auth_007"
            },
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""}
        )

    except TokenInvalidException as e:
        # Token 无效
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TOKEN_INVALID",
                "message": str(e),
                "code": "auth_008"
            },
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""}
        )


# ============================================================================
# 租户 ID 快速访问
# ============================================================================

async def get_current_tenant_id(
    auth_user: dict = Depends(get_current_auth_user)
) -> str:
    """
    从认证用户中获取租户 ID

    这是一个便捷函数，用于快速获取当前用户的租户 ID。
    通常与 get_current_auth_user 配合使用。

    Args:
        auth_user: 认证用户信息

    Returns:
        租户 ID 字符串

    示例:
        @app.get("/api/sessions")
        async def list_sessions(
            tenant_id: str = Depends(get_current_tenant_id),
            db: Session = Depends(get_db)
        ):
            # 使用 tenant_id 查询数据
            sessions = db.query(Session).filter(
                Session.tenant_id == tenant_id
            ).all()
            return sessions
    """
    return auth_user["tenant_id"]


async def get_current_user_id(
    auth_user: dict = Depends(get_current_auth_user)
) -> str:
    """
    从认证用户中获取用户 ID

    Args:
        auth_user: 认证用户信息

    Returns:
        用户 ID 字符串

    示例:
        @app.get("/api/me")
        async def get_me(
            user_id: str = Depends(get_current_user_id),
            db: Session = Depends(get_db)
        ):
            user = db.query(User).filter(User.id == user_id).first()
            return user
    """
    return auth_user["id"]
