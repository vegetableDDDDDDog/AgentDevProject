"""
配额服务 - 管理工具调用配额
"""
from datetime import date, datetime
from sqlalchemy.orm import Session
from services.database import TenantToolQuota


class QuotaExceededException(Exception):
    """配额超限异常"""
    pass


class QuotaService:
    """配额管理服务"""

    def __init__(self, db: Session):
        """
        初始化配额服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def check_tool_quota(
        self,
        tenant_id: str,
        tool_name: str
    ):
        """
        检查工具调用配额

        Args:
            tenant_id: 租户ID
            tool_name: 工具名称

        Raises:
            QuotaExceededException: 配额超限
        """
        # 获取配额配置
        quota = self.db.query(TenantToolQuota).filter(
            TenantToolQuota.tenant_id == tenant_id,
            TenantToolQuota.tool_name == tool_name
        ).first()

        # 如果没有配置配额，则不限制
        if not quota:
            return

        # 检查是否需要重置
        self._reset_if_needed(quota)

        # 检查日配额
        if quota.max_calls_per_day:
            if quota.current_day_calls >= quota.max_calls_per_day:
                raise QuotaExceededException(
                    f"工具 {tool_name} 日配额已用完 "
                    f"({quota.current_day_calls}/{quota.max_calls_per_day})"
                )

        # 检查月配额
        if quota.max_calls_per_month:
            if quota.current_month_calls >= quota.max_calls_per_month:
                raise QuotaExceededException(
                    f"工具 {tool_name} 月配额已用完 "
                    f"({quota.current_month_calls}/{quota.max_calls_per_month})"
                )

    def record_tool_usage(
        self,
        tenant_id: str,
        tool_name: str
    ):
        """
        记录工具使用（增加计数）

        Args:
            tenant_id: 租户ID
            tool_name: 工具名称
        """
        quota = self.db.query(TenantToolQuota).filter(
            TenantToolQuota.tenant_id == tenant_id,
            TenantToolQuota.tool_name == tool_name
        ).first()

        if not quota:
            return

        # 检查是否需要重置
        self._reset_if_needed(quota)

        # 增加计数
        quota.current_day_calls += 1
        quota.current_month_calls += 1
        self.db.commit()

    def _reset_if_needed(self, quota: TenantToolQuota):
        """
        如果需要，重置配额计数

        Args:
            quota: 配额对象
        """
        today = date.today()

        # 检查日重置
        if quota.last_reset_date < today:
            quota.current_day_calls = 0
            quota.last_reset_date = today

        # 检查月重置
        if quota.last_reset_date.month != today.month:
            quota.current_month_calls = 0

    def get_quota_info(
        self,
        tenant_id: str,
        tool_name: str
    ) -> dict:
        """
        获取配额信息

        Args:
            tenant_id: 租户ID
            tool_name: 工具名称

        Returns:
            配额信息字典，如果不存在则返回 None
        """
        quota = self.db.query(TenantToolQuota).filter(
            TenantToolQuota.tenant_id == tenant_id,
            TenantToolQuota.tool_name == tool_name
        ).first()

        if not quota:
            return None

        return {
            "max_calls_per_day": quota.max_calls_per_day,
            "current_day_calls": quota.current_day_calls,
            "max_calls_per_month": quota.max_calls_per_month,
            "current_month_calls": quota.current_month_calls,
            "last_reset_date": quota.last_reset_date.isoformat()
        }
