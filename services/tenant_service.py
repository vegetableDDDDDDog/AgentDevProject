"""
租户服务 - 租户管理和上下文

提供租户查询、租户上下文管理和配额检查功能。
确保多租户系统的数据隔离和资源控制。
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session as SQLSession

from services.database import Tenant, User, TenantQuota
from services.exceptions import (
    TenantNotFoundException,
    TenantSuspendedException,
    QuotaExceededException
)


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class TenantQuotaInfo:
    """租户配额信息"""

    max_users: int
    max_agents: int
    max_sessions_per_day: int
    max_tokens_per_month: int
    current_month_tokens: int
    reset_date: date

    @classmethod
    def from_model(cls, quota: TenantQuota) -> 'TenantQuotaInfo':
        """从 ORM 模型创建配额信息"""
        return cls(
            max_users=quota.max_users,
            max_agents=quota.max_agents,
            max_sessions_per_day=quota.max_sessions_per_day,
            max_tokens_per_month=quota.max_tokens_per_month,
            current_month_tokens=quota.current_month_tokens,
            reset_date=quota.reset_date
        )


@dataclass
class TenantContext:
    """
    租户上下文 - 在请求生命周期中传递租户信息

    包含租户的基础信息、配置、配额等所有相关数据。
    """

    # 基础信息
    tenant_id: str
    tenant_name: str
    display_name: str
    plan: str  # 'free', 'pro', 'enterprise'
    status: str  # 'active', 'suspended', 'deleted'

    # 配置（从 settings JSON 字段解析）
    settings: Dict[str, Any]

    # 配额信息
    quotas: TenantQuotaInfo

    # 元数据
    created_at: datetime
    updated_at: datetime

    def is_active(self) -> bool:
        """租户是否激活"""
        return self.status == 'active'

    def has_feature(self, feature: str) -> bool:
        """
        检查租户是否有某个特性（基于 plan）

        Args:
            feature: 特性名称（如 'basic_chat', 'advanced_agents'）

        Returns:
            True if 租户套餐包含该特性
        """
        feature_map = {
            'free': ['basic_chat'],
            'pro': ['basic_chat', 'advanced_agents', 'api_access'],
            'enterprise': ['basic_chat', 'advanced_agents', 'api_access', 'ss']
        }
        return feature in feature_map.get(self.plan, [])

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取租户配置项

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值，如果不存在返回默认值
        """
        return self.settings.get(key, default)


# ============================================================================
# 租户服务
# ============================================================================

class TenantService:
    """
    租户服务类

    提供租户查询、上下文管理和配额检查功能。

    示例:
        service = TenantService()

        # 获取租户上下文
        context = service.get_tenant_context(db, tenant_id)

        # 检查用户数配额
        service.check_user_quota(db, context)
    """

    def get_tenant_context(
        self,
        db: SQLSession,
        tenant_id: str
    ) -> TenantContext:
        """
        获取租户上下文

        从数据库查询租户信息、配额信息，构建 TenantContext。
        自动检查租户状态，非激活状态抛出异常。

        Args:
            db: 数据库会话
            tenant_id: 租户 ID

        Returns:
            TenantContext 对象

        Raises:
            TenantNotFoundException: 租户不存在
            TenantSuspendedException: 租户被暂停或已删除

        示例:
            try:
                context = service.get_tenant_context(db, "tenant-uuid")
                print(f"租户名称: {context.display_name}")
                print(f"套餐: {context.plan}")
            except TenantNotFoundException:
                print("租户不存在")
        """
        # 查询租户
        tenant = db.query(Tenant).filter(
            Tenant.id == tenant_id
        ).first()

        if not tenant:
            raise TenantNotFoundException(tenant_id)

        # 检查状态
        if tenant.status != 'active':
            raise TenantSuspendedException()

        # 查询配额信息
        quota = db.query(TenantQuota).filter(
            TenantQuota.tenant_id == tenant_id
        ).first()

        # 如果配额不存在，创建默认配额
        if not quota:
            quota = TenantQuota(
                tenant_id=tenant_id,
                max_users=5,
                max_agents=10,
                max_sessions_per_day=100,
                max_tokens_per_month=1000000,
                current_month_tokens=0,
                reset_date=date.today()
            )
            db.add(quota)
            db.commit()
            db.refresh(quota)

        # 构建上下文
        return TenantContext(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            display_name=tenant.display_name,
            plan=tenant.plan,
            status=tenant.status,
            settings=tenant.settings or {},
            quotas=TenantQuotaInfo.from_model(quota),
            created_at=tenant.created_at,
            updated_at=tenant.updated_at
        )

    # ========================================================================
    # 配额检查（MVP - 仅实现用户数配额）
    # ========================================================================

    def check_user_quota(
        self,
        db: SQLSession,
        tenant_context: TenantContext
    ) -> bool:
        """
        检查用户数配额（MVP 实现）

        统计当前租户的激活用户数，与配额对比。
        如果已达上限，抛出 QuotaExceededException。

        Args:
            db: 数据库会话
            tenant_context: 租户上下文

        Returns:
            True if 未超限

        Raises:
            QuotaExceededException: 用户数已达上限

        示例:
            try:
                service.check_user_quota(db, context)
                # 可以创建新用户
            except QuotaExceededException as e:
                print(f"用户数已达上限: {e.limit}")
        """
        # 统计当前激活用户数
        current_users = db.query(User).filter(
            User.tenant_id == tenant_context.tenant_id,
            User.status == 'active'
        ).count()

        max_users = tenant_context.quotas.max_users

        # 检查是否超限
        if current_users >= max_users:
            raise QuotaExceededException(
                resource="users",
                limit=max_users
            )

        return True

    def get_current_user_count(
        self,
        db: SQLSession,
        tenant_id: str
    ) -> int:
        """
        获取当前租户的用户数

        Args:
            db: 数据库会话
            tenant_id: 租户 ID

        Returns:
            当前激活用户数
        """
        return db.query(User).filter(
            User.tenant_id == tenant_id,
            User.status == 'active'
        ).count()

    # ========================================================================
    # 租户查询辅助方法
    # ========================================================================

    def find_tenant_by_name(self, db: SQLSession, name: str) -> Optional[Tenant]:
        """
        根据名称查找租户

        Args:
            db: 数据库会话
            name: 租户名称

        Returns:
            租户对象，如果不存在返回 None
        """
        return db.query(Tenant).filter(
            Tenant.name == name
        ).first()

    def find_tenant_by_id(self, db: SQLSession, tenant_id: str) -> Optional[Tenant]:
        """
        根据 ID 查找租户

        Args:
            db: 数据库会话
            tenant_id: 租户 ID

        Returns:
            租户对象，如果不存在返回 None
        """
        return db.query(Tenant).filter(
            Tenant.id == tenant_id
        ).first()
