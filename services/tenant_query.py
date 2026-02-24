"""
租户感知查询助手 - 自动 tenant_id 过滤

提供便捷的查询方法，自动添加租户过滤条件，
防止跨租户数据泄露。
"""

from typing import Type, TypeVar, List, Any
from sqlalchemy.orm import Session as SQLSession
from fastapi import HTTPException, status

from services.database import Session, Message, AgentLog


# ============================================================================
# 类型变量
# ============================================================================

T = TypeVar('T', bound=Any)


# ============================================================================
# 租户感知查询助手
# ============================================================================

class TenantQuery:
    """
    租户感知查询助手

    提供自动添加 tenant_id 过滤条件的查询方法，
    确保数据隔离安全。

    示例:
        # ❌ 错误：可能跨租户访问
        sessions = db.query(Session).all()

        # ✅ 正确：自动过滤当前租户
        tenant_id = request.state.tenant_context.tenant_id
        sessions = TenantQuery.filter_by_tenant(
            db, Session, tenant_id
        ).all()
    """

    @staticmethod
    def filter_by_tenant(
        db: SQLSession,
        model: Type[T],
        tenant_id: str
    ):
        """
        自动添加 tenant_id 过滤条件

        创建一个带租户过滤的查询对象，后续可以继续添加条件。

        Args:
            db: 数据库会话
            model: ORM 模型类（必须有 tenant_id 字段）
            tenant_id: 租户 ID

        Returns:
            SQLAlchemy Query 对象

        示例:
            query = TenantQuery.filter_by_tenant(db, Session, tenant_id)
            recent_sessions = query.order_by(
                Session.created_at.desc()
            ).limit(10).all()
        """
        return db.query(model).filter(
            model.tenant_id == tenant_id
        )

    @staticmethod
    def get_by_id(
        db: SQLSession,
        model: Type[T],
        resource_id: str,
        tenant_id: str
    ) -> T:
        """
        根据 ID 获取资源，自动验证租户

        同时验证资源 ID 和租户 ID，确保只返回属于当前租户的资源。
        如果资源不存在或不属于当前租户，返回 None。

        Args:
            db: 数据库会话
            model: ORM 模型类
            resource_id: 资源 ID
            tenant_id: 租户 ID

        Returns:
            资源对象，如果不存在或不属于当前租户返回 None

        示例:
            session = TenantQuery.get_by_id(
                db, Session, session_id, tenant_id
            )
            if session:
                print(session.messages)
        """
        return db.query(model).filter(
            model.id == resource_id,
            model.tenant_id == tenant_id
        ).first()

    @staticmethod
    def get_by_id_or_404(
        db: SQLSession,
        model: Type[T],
        resource_id: str,
        tenant_id: str,
        resource_name: str = "资源"
    ) -> T:
        """
        根据 ID 获取资源，自动验证租户，不存在则抛出 404

        这是 get_by_id 的 HTTP 友好版本，适合在路由中使用。
        如果资源不存在或不属于当前租户，抛出 HTTPException。

        Args:
            db: 数据库会话
            model: ORM 模型类
            resource_id: 资源 ID
            tenant_id: 租户 ID
            resource_name: 资源名称（用于错误消息）

        Returns:
            资源对象

        Raises:
            HTTPException 404: 资源不存在或不属于当前租户

        示例:
            @router.get("/sessions/{session_id}")
            async def get_session(
                session_id: str,
                db: Session = Depends(get_db),
                tenant_id: str = Depends(get_current_tenant_id)
            ):
                session = TenantQuery.get_by_id_or_404(
                    db, Session, session_id, tenant_id, "会话"
                )
                return {"session": session}
        """
        resource = db.query(model).filter(
            model.id == resource_id,
            model.tenant_id == tenant_id
        ).first()

        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "RESOURCE_NOT_FOUND",
                    "message": f"{resource_name}不存在",
                    "code": "tenant_003"
                }
            )

        return resource

    @staticmethod
    def list_all(
        db: SQLSession,
        model: Type[T],
        tenant_id: str,
        limit: int = None,
        order_by = None
    ) -> List[T]:
        """
        列出租户的所有资源

        Args:
            db: 数据库会话
            model: ORM 模型类
            tenant_id: 租户 ID
            limit: 限制返回数量（可选）
            order_by: 排序字段（可选）

        Returns:
            资源列表

        示例:
            # 获取最近 10 个会话
            sessions = TenantQuery.list_all(
                db,
                Session,
                tenant_id,
                limit=10,
                order_by=Session.created_at.desc()
            )
        """
        query = TenantQuery.filter_by_tenant(db, model, tenant_id)

        if order_by is not None:
            query = query.order_by(order_by)

        if limit is not None:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def count(
        db: SQLSession,
        model: Type[T],
        tenant_id: str
    ) -> int:
        """
        统计租户的资源数量

        Args:
            db: 数据库会话
            model: ORM 模型类
            tenant_id: 租户 ID

        Returns:
            资源数量

        示例:
            session_count = TenantQuery.count(db, Session, tenant_id)
            print(f"当前租户有 {session_count} 个会话")
        """
        return TenantQuery.filter_by_tenant(
            db, model, tenant_id
        ).count()


# ============================================================================
# 便捷函数
# ============================================================================

def get_tenant_sessions(
    db: SQLSession,
    tenant_id: str,
    limit: int = None
) -> List[Session]:
    """
    获取租户的所有会话

    Args:
        db: 数据库会话
        tenant_id: 租户 ID
        limit: 限制返回数量（可选）

    Returns:
        会话列表（按创建时间倒序）
    """
    return TenantQuery.list_all(
        db,
        Session,
        tenant_id,
        limit=limit,
        order_by=Session.created_at.desc()
    )


def get_tenant_session_or_404(
    db: SQLSession,
    session_id: str,
    tenant_id: str
) -> Session:
    """
    获取租户的指定会话，不存在则抛出 404

    Args:
        db: 数据库会话
        session_id: 会话 ID
        tenant_id: 租户 ID

    Returns:
        会话对象

    Raises:
        HTTPException 404: 会话不存在
    """
    return TenantQuery.get_by_id_or_404(
        db, Session, session_id, tenant_id, "会话"
    )


def get_tenant_messages(
    db: SQLSession,
    session_id: str,
    tenant_id: str
) -> List[Message]:
    """
    获取租户会话的所有消息

    Args:
        db: 数据库会话
        session_id: 会话 ID
        tenant_id: 租户 ID

    Returns:
        消息列表（按创建时间正序）
    """
    return db.query(Message).filter(
        Message.session_id == session_id,
        Message.tenant_id == tenant_id
    ).order_by(Message.created_at.asc()).all()


def get_tenant_agent_logs(
    db: SQLSession,
    tenant_id: str,
    agent_type: str = None,
    limit: int = 100
) -> List[AgentLog]:
    """
    获取租户的 Agent 日志

    Args:
        db: 数据库会话
        tenant_id: 租户 ID
        agent_type: Agent 类型过滤（可选）
        limit: 限制返回数量

    Returns:
        Agent 日志列表（按创建时间倒序）
    """
    query = TenantQuery.filter_by_tenant(db, AgentLog, tenant_id)

    if agent_type:
        query = query.filter(AgentLog.agent_type == agent_type)

    return query.order_by(
        AgentLog.created_at.desc()
    ).limit(limit).all()
