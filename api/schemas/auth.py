"""
认证相关的 Pydantic 数据模型

定义登录、刷新 token 等请求和响应的数据结构。
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


# ============================================================================
# 请求模型
# ============================================================================

class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=8, description="用户密码（至少8个字符）")


class LoginWithTenantRequest(BaseModel):
    """带租户选择的登录请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=8, description="用户密码")
    tenant_id: str = Field(..., description="租户 ID")


class RefreshRequest(BaseModel):
    """刷新 token 请求"""
    refresh_token: str = Field(..., description="Refresh token")


# ============================================================================
# 响应模型
# ============================================================================

class UserInfo(BaseModel):
    """用户信息"""
    id: str
    email: str
    role: str
    tenant_id: str

    class Config:
        from_attributes = True


class TenantInfo(BaseModel):
    """租户信息（用于多租户歧义）"""
    id: str
    name: str


class LoginResponse(BaseModel):
    """登录成功响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserInfo


class TenantSelectionRequiredResponse(BaseModel):
    """需要选择租户响应"""
    status: str = "tenant_selection_required"
    message: str
    tenants: List[TenantInfo]


class RefreshResponse(BaseModel):
    """刷新 token 成功响应"""
    access_token: str
    token_type: str = "bearer"


# ============================================================================
# 错误响应模型
# ============================================================================

class ErrorResponse(BaseModel):
    """通用错误响应"""
    error: str
    message: str
    code: Optional[str] = None
    path: Optional[str] = None
