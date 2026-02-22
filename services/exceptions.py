"""
自定义异常类

定义项目中使用的所有自定义异常，包括认证、授权和业务逻辑异常。
"""


class AgentException(Exception):
    """Agent 平台异常基类"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


# ============================================================================
# 认证相关异常
# ============================================================================

class AuthException(AgentException):
    """认证异常基类"""
    pass


class UserNotFoundException(AuthException):
    """用户不存在异常"""

    def __init__(self, email: str = None):
        message = f"用户不存在" + (f": {email}" if email else "")
        super().__init__(message, "USER_NOT_FOUND")


class InvalidCredentialsException(AuthException):
    """无效的凭据异常（密码错误）"""

    def __init__(self):
        super().__init__("邮箱或密码错误", "INVALID_CREDENTIALS")


class TokenExpiredException(AuthException):
    """Token 已过期异常"""

    def __init__(self):
        super().__init__("Token 已过期", "TOKEN_EXPIRED")


class TokenInvalidException(AuthException):
    """Token 无效异常（签名错误、格式错误等）"""

    def __init__(self, detail: str = None):
        message = "Token 无效"
        if detail:
            message += f": {detail}"
        super().__init__(message, "TOKEN_INVALID")


class TenantSelectionRequiredException(AuthException):
    """需要选择租户异常"""

    def __init__(self, tenants: list = None):
        self.tenants = tenants or []
        super().__init__(
            f"您的邮箱属于 {len(self.tenants)} 个租户，请选择",
            "TENANT_SELECTION_REQUIRED"
        )


class UserSuspendedException(AuthException):
    """用户被暂停异常"""

    def __init__(self):
        super().__init__("用户已被暂停", "USER_SUSPENDED")


# ============================================================================
# 租户相关异常
# ============================================================================

class TenantException(AgentException):
    """租户异常基类"""
    pass


class TenantNotFoundException(TenantException):
    """租户不存在异常"""

    def __init__(self, tenant_id: str = None):
        message = f"租户不存在" + (f": {tenant_id}" if tenant_id else "")
        super().__init__(message, "TENANT_NOT_FOUND")


class TenantSuspendedException(TenantException):
    """租户被暂停异常"""

    def __init__(self):
        super().__init__("租户已被暂停", "TENANT_SUSPENDED")


# ============================================================================
# 配额相关异常
# ============================================================================

class QuotaException(AgentException):
    """配额异常基类"""
    pass


class QuotaExceededException(QuotaException):
    """配额超限异常"""

    def __init__(self, resource: str, limit: int = None):
        message = f"配额超限: {resource}"
        if limit is not None:
            message += f" (限制: {limit})"
        super().__init__(message, "QUOTA_EXCEEDED")


# ============================================================================
# Agent 相关异常
# ============================================================================

class AgentRegistryException(AgentException):
    """Agent 注册表异常"""

    def __init__(self, message: str):
        super().__init__(message, "AGENT_REGISTRY_ERROR")


class AgentExecutionException(AgentException):
    """Agent 执行异常"""

    def __init__(self, message: str):
        super().__init__(message, "AGENT_EXECUTION_ERROR")
