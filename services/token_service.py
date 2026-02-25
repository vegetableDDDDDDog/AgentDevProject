"""
Token 统计服务 - 记录和统计 LLM Token 使用量

提供 Token 使用记录和统计功能，用于计费和配额管理。
"""

from typing import Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session as SQLSession

from services.database import SessionLocal
from services.database import Message


# ============================================================================
# Token 统计服务
# ============================================================================

class TokenService:
    """
    Token 统计服务类

    提供 Token 使用记录和统计功能。
    MVP 阶段只记录，不扣费。

    示例:
        service = TokenService()

        # 记录 Token 使用
        service.record_token_usage(
            session_id="session-uuid",
            tenant_id="tenant-uuid",
            prompt_tokens=100,
            completion_tokens=200
        )

        # 获取租户本月 Token 使用量
        usage = service.get_monthly_usage(tenant_id)
        print(f"本月使用: {usage} tokens")
    """

    def record_token_usage(
        self,
        session_id: str,
        tenant_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: Optional[int] = None
    ) -> None:
        """
        记录 Token 使用量到消息

        将 Token 使用量记录到消息数据库。
        注意：此方法不会更新配额，仅记录使用情况。

        Args:
            session_id: 会话 ID
            tenant_id: 租户 ID
            prompt_tokens: 提示 Token 数
            completion_tokens: 完成 Token 数
            total_tokens: 总 Token 数（可选，默认为 prompt+completion）

        示例:
            service.record_token_usage(
                session_id="session-123",
                tenant_id="tenant-456",
                prompt_tokens=100,
                completion_tokens=200
            )
        """
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens

        db: SQLSession = SessionLocal()
        try:
            # 查询最后一条消息（通常是当前 AI 响应）
            message = db.query(Message).filter(
                Message.session_id == session_id,
                Message.tenant_id == tenant_id
            ).order_by(Message.created_at.desc()).first()

            if message:
                # 更新消息的 Token 使用量
                message.tokens_used = total_tokens
                db.commit()
            else:
                # 如果没有找到消息，记录日志（不抛出异常）
                print(f"警告: 未找到会话 {session_id} 的消息")

        except Exception as e:
            db.rollback()
            print(f"记录 Token 使用失败: {e}")
        finally:
            db.close()

    def get_monthly_usage(
        self,
        tenant_id: str,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> int:
        """
        获取租户指定月份的 Token 使用量

        Args:
            tenant_id: 租户 ID
            year: 年份（可选，默认当前年）
            month: 月份（可选，默认当前月）

        Returns:
            Token 使用总数
        """
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month

        db: SQLSession = SessionLocal()
        try:
            # 查询指定月份的所有消息
            from sqlalchemy import func

            result = db.query(func.sum(Message.tokens_used)).filter(
                Message.tenant_id == tenant_id,
                func.strftime('%Y', Message.created_at) == str(year),
                func.strftime('%m', Message.created_at) == f"{month:02d}"
            ).scalar()

            # 如果没有记录，返回 0
            return result or 0

        finally:
            db.close()

    def get_session_usage(
        self,
        session_id: str,
        tenant_id: str
    ) -> int:
        """
        获取会话的 Token 使用量

        Args:
            session_id: 会话 ID
            tenant_id: 租户 ID

        Returns:
            Token 使用总数
        """
        db: SQLSession = SessionLocal()
        try:
            from sqlalchemy import func

            result = db.query(func.sum(Message.tokens_used)).filter(
                Message.session_id == session_id,
                Message.tenant_id == tenant_id
            ).scalar()

            return result or 0

        finally:
            db.close()

    def get_daily_usage(
        self,
        tenant_id: str,
        target_date: Optional[date] = None
    ) -> int:
        """
        获取租户指定日期的 Token 使用量

        Args:
            tenant_id: 租户 ID
            target_date: 目标日期（可选，默认今天）

        Returns:
            Token 使用总数
        """
        if target_date is None:
            target_date = date.today()

        db: SQLSession = SessionLocal()
        try:
            from sqlalchemy import func

            result = db.query(func.sum(Message.tokens_used)).filter(
                Message.tenant_id == tenant_id,
                func.date(Message.created_at) == target_date
            ).scalar()

            return result or 0

        finally:
            db.close()

    def get_usage_stats(
        self,
        tenant_id: str,
        days: int = 30
    ) -> dict:
        """
        获取 Token 使用统计

        Args:
            tenant_id: 租户 ID
            days: 统计天数（默认 30 天）

        Returns:
            包含统计信息的字典：
            {
                "total_tokens": 总 Token 数,
                "daily_average": 日均 Token 数,
                "total_messages": 总消息数,
                "avg_tokens_per_message": 平均每条消息 Token 数
            }
        """
        db: SQLSession = SessionLocal()
        try:
            from sqlalchemy import func
            from datetime import timedelta

            start_date = datetime.now() - timedelta(days=days)

            # 总 Token 数
            total_tokens = db.query(func.sum(Message.tokens_used)).filter(
                Message.tenant_id == tenant_id,
                Message.created_at >= start_date
            ).scalar() or 0

            # 总消息数
            total_messages = db.query(func.count(Message.id)).filter(
                Message.tenant_id == tenant_id,
                Message.created_at >= start_date
            ).scalar() or 0

            # 计算平均值
            daily_average = total_tokens / days if days > 0 else 0
            avg_tokens_per_message = total_tokens / total_messages if total_messages > 0 else 0

            return {
                "total_tokens": total_tokens,
                "daily_average": round(daily_average, 2),
                "total_messages": total_messages,
                "avg_tokens_per_message": round(avg_tokens_per_message, 2),
                "period_days": days
            }

        finally:
            db.close()


# ============================================================================
# 便捷函数
# ============================================================================

def record_llm_usage(
    session_id: str,
    tenant_id: str,
    response_message,
    prompt_tokens: int = 0
) -> None:
    """
    记录 LLM 响应的 Token 使用量

    便捷函数，用于在 Agent 执行后记录 Token 使用。

    Args:
        session_id: 会话 ID
        tenant_id: 租户 ID
        response_message: LLM 响应消息（LangChain AIMessage）
        prompt_tokens: 提示 Token 数（如果可用）

    示例:
        from langchain_core.messages import AIMessage

        response = AIMessage(
            content="Hello!",
            response_metadata={"token_usage": {"total_tokens": 100}}
        )

        record_llm_usage(
            session_id="session-123",
            tenant_id="tenant-456",
            response_message=response
        )
    """
    # 尝试从响应元数据中提取 Token 使用量
    completion_tokens = 0
    total_tokens = 0

    if hasattr(response_message, 'response_metadata'):
        token_usage = response_message.response_metadata.get('token_usage', {})
        total_tokens = token_usage.get('total_tokens', 0)
        completion_tokens = token_usage.get('completion_tokens', 0)

    # 记录到数据库
    service = TokenService()
    service.record_token_usage(
        session_id=session_id,
        tenant_id=tenant_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens
    )
