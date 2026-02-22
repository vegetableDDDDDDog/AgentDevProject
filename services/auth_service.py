"""
认证服务 - JWT 令牌管理和用户认证

提供用户认证、JWT token 生成和验证、密码加密等功能。
支持跨租户用户查询和多租户歧义处理。
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session as SQLSession

from api.config import settings
from services.database import User, Tenant
from services.exceptions import (
    UserNotFoundException,
    InvalidCredentialsException,
    TokenExpiredException,
    TokenInvalidException,
    TenantSelectionRequiredException,
    UserSuspendedException
)


# ============================================================================
# JWT 配置
# ============================================================================

ALGORITHM = "HS256"  # HMAC-SHA256 算法
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Access token 15分钟
REFRESH_TOKEN_EXPIRE_DAYS = 7  # Refresh token 7天


# ============================================================================
# 密码加密上下文
# ============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# Token 载荷模型
# ============================================================================

class TokenPayload:
    """JWT Token 载荷数据模型"""

    def __init__(
        self,
        sub: str,  # 用户 ID (Subject)
        tenant_id: str,  # 租户 ID
        role: str,  # 用户角色
        iat: datetime,  # 签发时间
        exp: datetime,  # 过期时间
        token_version: int = 1,  # Token 版本号
        token_type: str = "access"  # Token 类型: access | refresh
    ):
        self.sub = sub
        self.tenant_id = tenant_id
        self.role = role
        self.iat = iat
        self.exp = exp
        self.token_version = token_version
        self.token_type = token_type


# ============================================================================
# 认证服务类
# ============================================================================

class AuthService:
    """
    认证服务类

    提供用户认证、JWT token 生成和验证功能。
    支持跨租户用户查询和多租户歧义处理。

    示例:
        service = AuthService()
        # 登录
        tokens = service.authenticate_user(db, "user@example.com", "password")
        # 验证 token
        payload = service.verify_token("eyJhbGciOi...")
    """

    def __init__(self, secret_key: str = None):
        """
        初始化认证服务

        Args:
            secret_key: JWT 签名密钥，默认从 settings 读取
        """
        self.secret_key = secret_key or settings.secret_key
        self.algorithm = ALGORITHM

    # ==================== 用户查询 ====================

    def find_user_by_email(self, db: SQLSession, email: str) -> List[User]:
        """
        跨所有租户查找用户（通过邮箱）

        Args:
            db: 数据库会话
            email: 用户邮箱

        Returns:
            用户列表（可能属于不同租户）

        示例:
            users = service.find_user_by_email(db, "user@example.com")
            # 返回: [User(...), User(...)]  # 可能属于不同租户
        """
        if not email:
            raise ValueError("邮箱不能为空")

        users = db.query(User).filter(User.email == email).all()
        return users

    def find_user_by_id(self, db: SQLSession, user_id: str) -> Optional[User]:
        """
        根据用户 ID 查找用户

        Args:
            db: 数据库会话
            user_id: 用户 UUID

        Returns:
            用户对象，如果不存在返回 None
        """
        return db.query(User).filter(User.id == user_id).first()

    # ==================== 密码验证 ====================

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        验证明文密码是否与哈希密码匹配

        Args:
            plain_password: 明文密码
            hashed_password: bcrypt 哈希密码

        Returns:
            如果密码匹配返回 True，否则返回 False

        示例:
            is_valid = service.verify_password("password123", "$2b$12$...")
        """
        return pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, plain_password: str) -> str:
        """
        对明文密码进行 bcrypt 哈希

        Args:
            plain_password: 明文密码

        Returns:
            bcrypt 哈希后的密码

        示例:
            hashed = service.hash_password("password123")
            # 返回: "$2b$12$..."
        """
        return pwd_context.hash(plain_password)

    # ==================== 用户认证 ====================

    def authenticate_user(
        self,
        db: SQLSession,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """
        用户认证（跨租户）

        通过邮箱和密码认证用户，返回 token 和用户信息。
        如果邮箱属于多个租户，触发 TenantSelectionRequiredException。

        Args:
            db: 数据库会话
            email: 用户邮箱
            password: 明文密码

        Returns:
            包含 access_token, refresh_token, user_info 的字典

        Raises:
            InvalidCredentialsException: 邮箱或密码错误
            TenantSelectionRequiredException: 邮箱属于多个租户
            UserSuspendedException: 用户被暂停

        示例:
            try:
                result = service.authenticate_user(db, "user@example.com", "password")
                # result = {
                #     "access_token": "eyJhbGciOi...",
                #     "refresh_token": "eyJhbGciOi...",
                #     "user": {...}
                # }
            except TenantSelectionRequiredException as e:
                # 处理多租户歧义
                tenants = e.tenants
        """
        # 查找用户（跨租户）
        users = self.find_user_by_email(db, email)

        if not users:
            raise InvalidCredentialsException()

        # 多租户歧义处理
        if len(users) > 1:
            tenants_info = [
                {"id": u.tenant_id, "name": u.tenant.name}
                for u in users
            ]
            raise TenantSelectionRequiredException(tenants=tenants_info)

        # 单个用户 - 验证密码
        user = users[0]

        if not self.verify_password(password, user.password_hash):
            raise InvalidCredentialsException()

        # 检查用户状态
        if user.status != 'active':
            raise UserSuspendedException()

        # 更新最后登录时间
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        # 生成 tokens
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "tenant_id": user.tenant_id
            }
        }

    def authenticate_user_with_tenant(
        self,
        db: SQLSession,
        email: str,
        password: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        用户认证（指定租户）

        用于多租户歧义场景，用户指定租户后重新认证。

        Args:
            db: 数据库会话
            email: 用户邮箱
            password: 明文密码
            tenant_id: 租户 ID

        Returns:
            包含 access_token, refresh_token, user_info 的字典

        Raises:
            InvalidCredentialsException: 邮箱、密码或租户不匹配
            UserSuspendedException: 用户被暂停
        """
        user = db.query(User).filter(
            User.email == email,
            User.tenant_id == tenant_id
        ).first()

        if not user or not self.verify_password(password, user.password_hash):
            raise InvalidCredentialsException()

        if user.status != 'active':
            raise UserSuspendedException()

        # 更新最后登录时间
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        # 生成 tokens
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "tenant_id": user.tenant_id
            }
        }

    # ==================== Token 生成 ====================

    def create_access_token(
        self,
        user: User,
        expires_delta: timedelta = None
    ) -> str:
        """
        创建 Access token

        Args:
            user: 用户对象
            expires_delta: 自定义过期时间，默认 15 分钟

        Returns:
            JWT access token 字符串

        示例:
            token = service.create_access_token(user, timedelta(minutes=30))
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )

        payload = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role,
            "iat": datetime.now(timezone.utc),
            "exp": expire,
            "token_version": getattr(user, 'token_version', 1),
            "token_type": "access"
        }

        encoded_jwt = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        return encoded_jwt

    def create_refresh_token(
        self,
        user: User,
        expires_delta: timedelta = None
    ) -> str:
        """
        创建 Refresh token

        Args:
            user: 用户对象
            expires_delta: 自定义过期时间，默认 7 天

        Returns:
            JWT refresh token 字符串
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=REFRESH_TOKEN_EXPIRE_DAYS
            )

        payload = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role,
            "iat": datetime.now(timezone.utc),
            "exp": expire,
            "token_version": getattr(user, 'token_version', 1),
            "token_type": "refresh"
        }

        encoded_jwt = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        return encoded_jwt

    # ==================== Token 验证 ====================

    def verify_token(self, token: str) -> TokenPayload:
        """
        验证并解析 JWT token

        Args:
            token: JWT token 字符串

        Returns:
            TokenPayload 对象

        Raises:
            TokenInvalidException: Token 无效（签名错误、格式错误）
            TokenExpiredException: Token 已过期

        示例:
            try:
                payload = service.verify_token("eyJhbGciOi...")
                print(f"用户 ID: {payload.sub}")
                print(f"租户 ID: {payload.tenant_id}")
            except TokenExpiredException:
                print("Token 已过期")
        """
        try:
            # 解析 JWT
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # 转换为 TokenPayload 对象
            return TokenPayload(
                sub=payload["sub"],
                tenant_id=payload["tenant_id"],
                role=payload["role"],
                iat=payload["iat"],
                exp=payload["exp"],
                token_version=payload.get("token_version", 1),
                token_type=payload.get("token_type", "access")
            )

        except jwt.ExpiredSignatureError:
            # Token 已过期
            raise TokenExpiredException()
        except JWTError as e:
            # 其他 JWT 错误（签名无效、格式错误等）
            raise TokenInvalidException(detail=str(e))

    def verify_access_token(self, token: str) -> TokenPayload:
        """
        验证 Access token

        Args:
            token: JWT token 字符串

        Returns:
            TokenPayload 对象

        Raises:
            TokenInvalidException: Token 类型不是 access
            TokenExpiredException: Token 已过期
            TokenInvalidException: Token 无效
        """
        payload = self.verify_token(token)

        if payload.token_type != "access":
            raise TokenInvalidException("Token 类型错误")

        return payload

    def verify_refresh_token(self, token: str) -> TokenPayload:
        """
        验证 Refresh token

        Args:
            token: JWT token 字符串

        Returns:
            TokenPayload 对象

        Raises:
            TokenInvalidException: Token 类型不是 refresh
            TokenExpiredException: Token 已过期
            TokenInvalidException: Token 无效
        """
        payload = self.verify_token(token)

        if payload.token_type != "refresh":
            raise TokenInvalidException("Token 类型错误")

        return payload

    # ==================== Token 刷新 ====================

    def refresh_access_token(
        self,
        db: SQLSession,
        refresh_token: str
    ) -> str:
        """
        使用 Refresh token 刷新 Access token

        Args:
            db: 数据库会话
            refresh_token: Refresh token 字符串

        Returns:
            新的 Access token

        Raises:
            TokenExpiredException: Refresh token 已过期
            TokenInvalidException: Refresh token 无效
            UserNotFoundException: 用户不存在（已被删除）

        示例:
            new_access_token = service.refresh_access_token(db, refresh_token)
        """
        # 验证 refresh token
        payload = self.verify_refresh_token(refresh_token)

        # 查询用户
        user = self.find_user_by_id(db, payload.sub)
        if not user:
            raise UserNotFoundException()

        # 检查 token 版本（支持强制下线）
        user_token_version = getattr(user, 'token_version', 1)
        if payload.token_version != user_token_version:
            raise TokenInvalidException("Token 版本不匹配（已失效）")

        # 检查用户状态
        if user.status != 'active':
            raise UserSuspendedException()

        # 生成新的 access token
        new_token = self.create_access_token(user)

        return new_token
