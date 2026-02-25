"""
会话服务 - 用于管理 Agent 会话、消息和日志。

本模块提供与会话、消息和 Agent 执行日志相关的数据库操作的服务层。
所有方法都是同步的，并自动处理数据库会话管理。
"""

from typing import Optional, List

from sqlalchemy.orm import Session as SQLSession
from sqlalchemy.exc import SQLAlchemyError

from services.database import Session, Message, AgentLog, SessionLocal


class SessionService:
    """
    用于管理 Agent 会话、消息和日志的服务类。

    此服务提供会话、消息和 Agent 日志的 CRUD 操作方法。
    所有方法都创建自己的数据库会话，并自动处理事务管理。

    示例:
        service = SessionService()
        session = service.create_session("langchain", {"model": "gpt-4"})
        message = service.add_message(session.id, "user", "你好！")
    """

    # ==================== 会话管理 ====================

    def create_session(
        self,
        agent_type: str,
        config: Optional[dict] = None,
        metadata: Optional[dict] = None,
        tenant_id: Optional[str] = None
    ) -> Session:
        """
        创建具有指定 Agent 类型和配置的新会话。

        Args:
            agent_type: Agent 类型（例如 'langchain', 'crewai'）
            config: Agent 的可选配置字典
            metadata: 会话的可选元数据字典
            tenant_id: 租户 ID（用于多租户隔离）

        Returns:
            Session: 创建的会话对象，具有自动生成的 UUID

        Raises:
            ValueError: 如果 agent_type 为空或无效
            SQLAlchemyError: 如果数据库操作失败
        """
        if not agent_type or not isinstance(agent_type, str):
            raise ValueError("agent_type 必须是非空字符串")

        db: SQLSession = SessionLocal()
        try:
            session = Session(
                agent_type=agent_type,
                config=config,
                meta=metadata,
                tenant_id=tenant_id  # 租户 ID
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
        except SQLAlchemyError as e:
            db.rollback()
            raise ValueError(f"创建会话失败: {str(e)}")
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        通过 ID 检索会话。

        Args:
            session_id: 要检索的会话的 UUID

        Returns:
            如果找到返回 Session 对象，否则返回 None

        Raises:
            ValueError: 如果 session_id 为空
        """
        if not session_id:
            raise ValueError("必须提供 session_id")

        db: SQLSession = SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            return session
        finally:
            db.close()

    def update_session(self, session_id: str, **kwargs) -> Optional[Session]:
        """
        更新会话字段。

        Args:
            session_id: 要更新的会话的 UUID
            **kwargs: 要更新的字段（config, meta 等）

        Returns:
            如果找到返回更新的 Session 对象，否则返回 None

        Raises:
            ValueError: 如果 session_id 无效或会话未找到

        注意:
            updated_at 时间戳由 ORM 自动更新。
        """
        if not session_id:
            raise ValueError("必须提供 session_id")

        db: SQLSession = SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                return None

            # 更新允许的字段
            allowed_fields = {"config", "meta", "agent_type"}
            for key, value in kwargs.items():
                if key == 'metadata':
                    # 将 'metadata' 映射到 'meta' 列
                    session.meta = value
                elif key in allowed_fields:
                    setattr(session, key, value)
                else:
                    raise ValueError(f"无法更新字段 '{key}'")

            db.commit()
            db.refresh(session)
            return session
        except SQLAlchemyError as e:
            db.rollback()
            raise ValueError(f"更新会话失败: {str(e)}")
        finally:
            db.close()

    def list_sessions(
        self,
        agent_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Session]:
        """
        列出会话，可选择按 Agent 类型过滤。

        Args:
            agent_type: Agent 类型的可选过滤器
            limit: 要返回的会话最大数量（默认: 100）

        Returns:
            按创建时间降序排列的 Session 对象列表

        Raises:
            ValueError: 如果 limit 无效
        """
        if limit <= 0 or limit > 1000:
            raise ValueError("limit 必须在 1 到 1000 之间")

        db: SQLSession = SessionLocal()
        try:
            query = db.query(Session)

            if agent_type:
                query = query.filter(Session.agent_type == agent_type)

            sessions = query.order_by(Session.created_at.desc()).limit(limit).all()
            return sessions
        finally:
            db.close()

    # ==================== 消息管理 ====================

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
        metadata: Optional[dict] = None,
        tenant_id: Optional[str] = None
    ) -> Message:
        """
        向会话添加消息。

        Args:
            session_id: 会话的 UUID
            role: 消息角色（'user', 'assistant' 或 'system'）
            content: 消息内容
            tokens_used: 可选的 Token 使用计数
            metadata: 可选的元数据字典
            tenant_id: 租户 ID（用于多租户隔离）

        Returns:
            Message: 创建的 Message 对象

        Raises:
            ValueError: 如果会话未找到或参数无效
        """
        if not session_id:
            raise ValueError("必须提供 session_id")
        if not role or role not in ['user', 'assistant', 'system']:
            raise ValueError("role 必须是以下之一: 'user', 'assistant', 'system'")
        if not content or not isinstance(content, str):
            raise ValueError("content 必须是非空字符串")

        db: SQLSession = SessionLocal()
        try:
            # 验证会话是否存在（且租户匹配）
            session_query = db.query(Session).filter(Session.id == session_id)
            if tenant_id:
                session_query = session_query.filter(Session.tenant_id == tenant_id)

            session = session_query.first()
            if not session:
                raise ValueError(f"未找到 ID 为 '{session_id}' 的会话")

            # 获取租户 ID（优先使用参数，否则从会话获取）
            message_tenant_id = tenant_id or session.tenant_id

            message = Message(
                session_id=session_id,
                role=role,
                content=content,
                tokens_used=tokens_used,
                meta=metadata,
                tenant_id=message_tenant_id  # 租户 ID
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            return message
        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise ValueError(f"添加消息失败: {str(e)}")
        finally:
            db.close()

    def get_messages(
        self,
        session_id: str,
        role: Optional[str] = None,
        limit: int = 100,
        tenant_id: Optional[str] = None
    ) -> List[Message]:
        """
        获取会话的消息。

        Args:
            session_id: 会话的 UUID
            role: 按角色可选过滤（'user', 'assistant', 'system'）
            limit: 要返回的消息最大数量（默认: 100）
            tenant_id: 租户 ID（用于验证租户权限，可选）

        Returns:
            按创建时间升序排列的 Message 对象列表（最旧的在前）

        Raises:
            ValueError: 如果会话未找到或参数无效
        """
        if not session_id:
            raise ValueError("必须提供 session_id")
        if limit <= 0 or limit > 1000:
            raise ValueError("limit 必须在 1 到 1000 之间")

        db: SQLSession = SessionLocal()
        try:
            # 构建查询 - 验证会话存在且租户匹配
            session_query = db.query(Session).filter(Session.id == session_id)
            if tenant_id:
                session_query = session_query.filter(Session.tenant_id == tenant_id)

            session = session_query.first()
            if not session:
                raise ValueError(f"未找到 ID 为 '{session_id}' 的会话")

            query = db.query(Message).filter(Message.session_id == session_id)

            # 租户隔离
            if tenant_id:
                query = query.filter(Message.tenant_id == tenant_id)

            if role:
                if role not in ['user', 'assistant', 'system']:
                    raise ValueError("role 必须是以下之一: 'user', 'assistant', 'system'")
                query = query.filter(Message.role == role)

            messages = query.order_by(Message.created_at.asc()).limit(limit).all()
            return messages
        finally:
            db.close()

    def get_session_history(self, session_id: str) -> dict:
        """
        获取完整的会话历史，包括会话信息和所有消息。

        Args:
            session_id: 会话的 UUID

        Returns:
            包含以下键的字典:
                - session: Session 对象数据
                - messages: 按创建时间升序排列的 Message 对象列表

        Raises:
            ValueError: 如果会话未找到
        """
        if not session_id:
            raise ValueError("必须提供 session_id")

        db: SQLSession = SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                raise ValueError(f"未找到 ID 为 '{session_id}' 的会话")

            messages = (
                db.query(Message)
                .filter(Message.session_id == session_id)
                .order_by(Message.created_at.asc())
                .all()
            )

            return {
                "session": session,
                "messages": messages
            }
        finally:
            db.close()

    # ==================== Agent 日志记录 ====================

    def log_execution(
        self,
        session_id: Optional[str],
        agent_type: str,
        task: str,
        status: str,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        tenant_id: Optional[str] = None
    ) -> AgentLog:
        """
        记录 Agent 执行事件。

        Args:
            session_id: 会话的可选 UUID（可以为 None）
            agent_type: 执行的 Agent 类型
            task: 任务描述或标识符
            status: 执行状态（'success', 'error', 'pending' 等）
            error_message: 如果状态为 'error' 时的可选错误消息
            execution_time_ms: 可选的执行时间（毫秒）
            tenant_id: 租户 ID（用于多租户隔离）

        Returns:
            AgentLog: 创建的 AgentLog 对象

        Raises:
            ValueError: 如果参数无效或提供了 session_id 但未找到

        注意:
            对于没有会话上下文的 Agent 执行，session_id 可以为 None。
        """
        if not agent_type or not isinstance(agent_type, str):
            raise ValueError("agent_type 必须是非空字符串")
        if not task or not isinstance(task, str):
            raise ValueError("task 必须是非空字符串")
        if not status or not isinstance(status, str):
            raise ValueError("status 必须是非空字符串")

        db: SQLSession = SessionLocal()
        try:
            # 如果提供了 session_id，验证它是否存在（且租户匹配）
            if session_id:
                session_query = db.query(Session).filter(Session.id == session_id)
                if tenant_id:
                    session_query = session_query.filter(Session.tenant_id == tenant_id)

                session = session_query.first()
                if not session:
                    raise ValueError(f"未找到 ID 为 '{session_id}' 的会话")

                # 如果没有显式提供 tenant_id，从会话获取
                if not tenant_id:
                    tenant_id = session.tenant_id

            log = AgentLog(
                session_id=session_id,
                agent_type=agent_type,
                task=task,
                status=status,
                error_message=error_message,
                execution_time_ms=execution_time_ms,
                tenant_id=tenant_id  # 租户 ID
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log
        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise ValueError(f"记录执行失败: {str(e)}")
        finally:
            db.close()

    def get_agent_logs(
        self,
        session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentLog]:
        """
        获取具有可选过滤的 Agent 执行日志。

        Args:
            session_id: 按会话 ID 的可选过滤器
            agent_type: 按 Agent 类型的可选过滤器
            limit: 要返回的日志最大数量（默认: 100）

        Returns:
            按创建时间降序排列的 AgentLog 对象列表（最新的在前）

        Raises:
            ValueError: 如果 limit 无效
        """
        if limit <= 0 or limit > 1000:
            raise ValueError("limit 必须在 1 到 1000 之间")

        db: SQLSession = SessionLocal()
        try:
            query = db.query(AgentLog)

            if session_id:
                query = query.filter(AgentLog.session_id == session_id)

            if agent_type:
                query = query.filter(AgentLog.agent_type == agent_type)

            logs = query.order_by(AgentLog.created_at.desc()).limit(limit).all()
            return logs
        finally:
            db.close()
