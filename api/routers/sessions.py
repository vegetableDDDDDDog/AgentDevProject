"""
Sessions Router - Session Management

Provides endpoints for managing conversation sessions.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query

from api.schemas import (
    SessionCreateRequest,
    SessionResponse,
    SessionListResponse
)
from services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    summary="Create a new session",
    description="Create a new conversation session for an agent type"
)
async def create_session(request: SessionCreateRequest) -> SessionResponse:
    """
    Create a new conversation session.

    Args:
        request: SessionCreateRequest with agent_type and optional config/metadata

    Returns:
        SessionResponse with created session details
    """
    service = SessionService()

    session = service.create_session(
        agent_type=request.agent_type,
        config=request.config,
        metadata=request.metadata
    )

    return SessionResponse(
        id=session.id,
        agent_type=session.agent_type,
        config=session.config,
        metadata=session.meta,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0
    )


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List sessions",
    description="Get a list of sessions, optionally filtered by agent type"
)
async def list_sessions(
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    limit: int = Query(100, description="Maximum number of sessions to return", ge=1, le=1000)
) -> SessionListResponse:
    """
    List sessions with optional filtering.

    Args:
        agent_type: Optional filter for agent type
        limit: Maximum number of sessions to return (default: 100)

    Returns:
        SessionListResponse with list of sessions
    """
    service = SessionService()

    sessions = service.list_sessions(agent_type=agent_type, limit=limit)

    # Get message counts without lazy loading issues
    result_sessions = []
    for s in sessions:
        # Get message count for this session
        messages = service.get_messages(s.id, limit=1000)
        message_count = len(messages)

        result_sessions.append(
            SessionResponse(
                id=s.id,
                agent_type=s.agent_type,
                config=s.config,
                metadata=s.meta,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=message_count
            )
        )

    return SessionListResponse(
        sessions=result_sessions,
        count=len(sessions)
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session details",
    description="Get detailed information about a specific session"
)
async def get_session(session_id: str) -> SessionResponse:
    """
    Get session details.

    Args:
        session_id: Session UUID

    Returns:
        SessionResponse with session details

    Raises:
        HTTPException: If session not found
    """
    service = SessionService()

    session = service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )

    # Get message count
    messages = service.get_messages(session_id, limit=1000)

    return SessionResponse(
        id=session.id,
        agent_type=session.agent_type,
        config=session.config,
        metadata=session.meta,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(messages)
    )


@router.delete(
    "/{session_id}",
    summary="Delete a session",
    description="Delete a session and all its messages"
)
async def delete_session(session_id: str) -> dict:
    """
    Delete a session.

    Note: This endpoint is not fully implemented in the SessionService yet.
    It's included for API completeness.

    Args:
        session_id: Session UUID

    Returns:
        Success message

    Raises:
        HTTPException: If session not found
    """
    service = SessionService()

    session = service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )

    # TODO: Implement delete in SessionService
    # For now, return a message
    return {
        "message": "Session deletion not yet implemented",
        "session_id": session_id
    }
