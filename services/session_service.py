"""
Session service for managing agent sessions, messages, and logs.

This module provides a service layer for database operations related to sessions,
messages, and agent execution logs. All methods are synchronous and handle
database session management automatically.
"""

from typing import Optional, List

from sqlalchemy.orm import Session as SQLSession
from sqlalchemy.exc import SQLAlchemyError

from services.database import Session, Message, AgentLog, SessionLocal


class SessionService:
    """
    Service class for managing agent sessions, messages, and logs.

    This service provides methods for CRUD operations on sessions, messages,
    and agent logs. All methods create their own database sessions and handle
    transaction management automatically.

    Example:
        service = SessionService()
        session = service.create_session("langchain", {"model": "gpt-4"})
        message = service.add_message(session.id, "user", "Hello!")
    """

    # ==================== Session Management ====================

    def create_session(
        self,
        agent_type: str,
        config: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> Session:
        """
        Create a new session with the specified agent type and configuration.

        Args:
            agent_type: Type of agent (e.g., 'langchain', 'crewai')
            config: Optional configuration dictionary for the agent
            metadata: Optional metadata dictionary for the session

        Returns:
            Session: The created Session object with auto-generated UUID

        Raises:
            ValueError: If agent_type is empty or invalid
            SQLAlchemyError: If database operation fails
        """
        if not agent_type or not isinstance(agent_type, str):
            raise ValueError("agent_type must be a non-empty string")

        db: SQLSession = SessionLocal()
        try:
            session = Session(
                agent_type=agent_type,
                config=config,
                meta=metadata
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
        except SQLAlchemyError as e:
            db.rollback()
            raise ValueError(f"Failed to create session: {str(e)}")
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve a session by its ID.

        Args:
            session_id: UUID of the session to retrieve

        Returns:
            Session object if found, None otherwise

        Raises:
            ValueError: If session_id is empty
        """
        if not session_id:
            raise ValueError("session_id must be provided")

        db: SQLSession = SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            return session
        finally:
            db.close()

    def update_session(self, session_id: str, **kwargs) -> Optional[Session]:
        """
        Update session fields.

        Args:
            session_id: UUID of the session to update
            **kwargs: Fields to update (config, meta, etc.)

        Returns:
            Updated Session object if found, None otherwise

        Raises:
            ValueError: If session_id is invalid or session not found

        Note:
            The updated_at timestamp is automatically updated by the ORM.
        """
        if not session_id:
            raise ValueError("session_id must be provided")

        db: SQLSession = SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                return None

            # Update allowed fields
            allowed_fields = {"config", "meta", "agent_type"}
            for key, value in kwargs.items():
                if key == 'metadata':
                    # Map 'metadata' to 'meta' column
                    session.meta = value
                elif key in allowed_fields:
                    setattr(session, key, value)
                else:
                    raise ValueError(f"Cannot update field '{key}'")

            db.commit()
            db.refresh(session)
            return session
        except SQLAlchemyError as e:
            db.rollback()
            raise ValueError(f"Failed to update session: {str(e)}")
        finally:
            db.close()

    def list_sessions(
        self,
        agent_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Session]:
        """
        List sessions, optionally filtered by agent type.

        Args:
            agent_type: Optional filter for agent type
            limit: Maximum number of sessions to return (default: 100)

        Returns:
            List of Session objects ordered by created_at DESC

        Raises:
            ValueError: If limit is invalid
        """
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

        db: SQLSession = SessionLocal()
        try:
            query = db.query(Session)

            if agent_type:
                query = query.filter(Session.agent_type == agent_type)

            sessions = query.order_by(Session.created_at.desc()).limit(limit).all()
            return sessions
        finally:
            db.close()

    # ==================== Message Management ====================

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> Message:
        """
        Add a message to a session.

        Args:
            session_id: UUID of the session
            role: Message role ('user', 'assistant', or 'system')
            content: Message content
            tokens_used: Optional token usage count
            metadata: Optional metadata dictionary

        Returns:
            Message: The created Message object

        Raises:
            ValueError: If session not found or parameters invalid
        """
        if not session_id:
            raise ValueError("session_id must be provided")
        if not role or role not in ['user', 'assistant', 'system']:
            raise ValueError("role must be one of: 'user', 'assistant', 'system'")
        if not content or not isinstance(content, str):
            raise ValueError("content must be a non-empty string")

        db: SQLSession = SessionLocal()
        try:
            # Verify session exists
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                raise ValueError(f"Session with id '{session_id}' not found")

            message = Message(
                session_id=session_id,
                role=role,
                content=content,
                tokens_used=tokens_used,
                meta=metadata
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            return message
        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise ValueError(f"Failed to add message: {str(e)}")
        finally:
            db.close()

    def get_messages(
        self,
        session_id: str,
        role: Optional[str] = None,
        limit: int = 100
    ) -> List[Message]:
        """
        Get messages for a session.

        Args:
            session_id: UUID of the session
            role: Optional filter by role ('user', 'assistant', 'system')
            limit: Maximum number of messages to return (default: 100)

        Returns:
            List of Message objects ordered by created_at ASC (oldest first)

        Raises:
            ValueError: If session not found or parameters invalid
        """
        if not session_id:
            raise ValueError("session_id must be provided")
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

        db: SQLSession = SessionLocal()
        try:
            # Verify session exists
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                raise ValueError(f"Session with id '{session_id}' not found")

            query = db.query(Message).filter(Message.session_id == session_id)

            if role:
                if role not in ['user', 'assistant', 'system']:
                    raise ValueError("role must be one of: 'user', 'assistant', 'system'")
                query = query.filter(Message.role == role)

            messages = query.order_by(Message.created_at.asc()).limit(limit).all()
            return messages
        finally:
            db.close()

    def get_session_history(self, session_id: str) -> dict:
        """
        Get complete session history including session info and all messages.

        Args:
            session_id: UUID of the session

        Returns:
            Dictionary with keys:
                - session: Session object data
                - messages: List of Message objects ordered by created_at ASC

        Raises:
            ValueError: If session not found
        """
        if not session_id:
            raise ValueError("session_id must be provided")

        db: SQLSession = SessionLocal()
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                raise ValueError(f"Session with id '{session_id}' not found")

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

    # ==================== Agent Logging ====================

    def log_execution(
        self,
        session_id: Optional[str],
        agent_type: str,
        task: str,
        status: str,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> AgentLog:
        """
        Log an agent execution event.

        Args:
            session_id: Optional UUID of the session (can be None)
            agent_type: Type of agent executed
            task: Task description or identifier
            status: Execution status ('success', 'error', 'pending', etc.)
            error_message: Optional error message if status is 'error'
            execution_time_ms: Optional execution time in milliseconds

        Returns:
            AgentLog: The created AgentLog object

        Raises:
            ValueError: If parameters invalid or session_id provided but not found

        Note:
            session_id can be None for agent executions without a session context.
        """
        if not agent_type or not isinstance(agent_type, str):
            raise ValueError("agent_type must be a non-empty string")
        if not task or not isinstance(task, str):
            raise ValueError("task must be a non-empty string")
        if not status or not isinstance(status, str):
            raise ValueError("status must be a non-empty string")

        db: SQLSession = SessionLocal()
        try:
            # If session_id is provided, verify it exists
            if session_id:
                session = db.query(Session).filter(Session.id == session_id).first()
                if not session:
                    raise ValueError(f"Session with id '{session_id}' not found")

            log = AgentLog(
                session_id=session_id,
                agent_type=agent_type,
                task=task,
                status=status,
                error_message=error_message,
                execution_time_ms=execution_time_ms
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log
        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise ValueError(f"Failed to log execution: {str(e)}")
        finally:
            db.close()

    def get_agent_logs(
        self,
        session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentLog]:
        """
        Get agent execution logs with optional filtering.

        Args:
            session_id: Optional filter by session ID
            agent_type: Optional filter by agent type
            limit: Maximum number of logs to return (default: 100)

        Returns:
            List of AgentLog objects ordered by created_at DESC (newest first)

        Raises:
            ValueError: If limit is invalid
        """
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

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
