"""
Chat Router - SSE Streaming Chat Completions

Provides endpoints for conversational interactions with agents using
Server-Sent Events (SSE) for streaming responses.
"""

import time
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from api.schemas import ChatRequest, ChatHistoryResponse, ChatMessage
from api.sse_protocol import (
    SSEMessage,
    SSEThought,
    SSEError,
    SSEDone,
    SSEEventType,
    create_sse_event,
    sse_generator
)
from services.agent_factory import get_agent, is_registered
from services.session_service import SessionService
from services.database import SessionLocal

router = APIRouter(prefix="/chat", tags=["Chat"])


async def stream_agent_response(
    agent_type: str,
    message: str,
    session_id: str,
    service: SessionService
) -> AsyncGenerator[str, None]:
    """
    Stream agent execution results as SSE events.

    Args:
        agent_type: Type of agent to execute
        message: User message/task
        session_id: Session ID for persistence
        service: SessionService instance

    Yields:
        SSE formatted strings
    """
    start_time = time.time()
    tokens_used = 0

    try:
        # 1. Send thought event - agent is starting
        yield create_sse_event(
            SSEEventType.THOUGHT,
            {"content": f"Using agent: {agent_type}", "step": 0}
        )

        # 2. Get and execute agent
        if not is_registered(agent_type):
            raise ValueError(f"Unknown agent type: {agent_type}")

        agent = get_agent(agent_type)

        # Add user message to session
        service.add_message(session_id, "user", message)

        # Execute agent (async)
        result = await agent.execute(message, {})

        # 3. Stream the response as chunks
        response_text = result.get("response", "")

        # Simulate streaming by sending chunks
        chunk_size = 5  # Small chunks for demo
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            yield SSEMessage(content=chunk, type="text").to_sse()
            await asyncio.sleep(0.02)  # Small delay for realistic streaming

        # 4. Add assistant response to session
        tokens = result.get("tokens_used", 0)
        service.add_message(
            session_id,
            "assistant",
            response_text,
            tokens_used=tokens
        )

        # 5. Log execution
        execution_time = int((time.time() - start_time) * 1000)
        service.log_execution(
            session_id=session_id,
            agent_type=agent_type,
            task=message[:100],  # Truncate long tasks
            status="success",
            execution_time_ms=execution_time
        )

        # 6. Send done event
        yield SSEDone(
            session_id=session_id,
            tokens_used=tokens,
            execution_time_ms=execution_time
        ).to_sse()

    except Exception as e:
        # Log error
        execution_time = int((time.time() - start_time) * 1000)
        service.log_execution(
            session_id=session_id,
            agent_type=agent_type,
            task=message[:100],
            status="error",
            error_message=str(e),
            execution_time_ms=execution_time
        )

        # Send error event
        yield SSEError(
            message=str(e),
            code="AGENT_EXECUTION_ERROR"
        ).to_sse()


@router.post(
    "/completions",
    summary="Stream chat completion with SSE",
    description="Send a message to an agent and receive a streamed response via Server-Sent Events"
)
async def chat_completion(request: ChatRequest) -> StreamingResponse:
    """
    Stream chat completion using SSE.

    This endpoint creates a session (if session_id not provided), executes
    the agent, and streams the response chunk by chunk.

    Args:
        request: ChatRequest with agent_type, message, and optional session_id

    Returns:
        StreamingResponse with SSE events

    Example:
        POST /chat/completions
        {
            "agent_type": "mock_chat_agent",
            "message": "Hello, how are you?"
        }
    """
    # Validate agent type
    if not is_registered(request.agent_type):
        available = ", ".join([
            k for k in ["echo_agent", "mock_chat_agent", "counter_agent", "error_agent"]
            if is_registered(k)
        ])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown agent type '{request.agent_type}'. Available: {available}"
        )

    # Create or get session
    service = SessionService()

    if request.session_id:
        # Verify session exists
        session = service.get_session(request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{request.session_id}' not found"
            )
        session_id = request.session_id
    else:
        # Create new session
        session = service.create_session(
            agent_type=request.agent_type,
            config=request.config
        )
        session_id = session.id

    # Return SSE stream
    return StreamingResponse(
        stream_agent_response(
            agent_type=request.agent_type,
            message=request.message,
            session_id=session_id,
            service=service
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get(
    "/history",
    response_model=ChatHistoryResponse,
    summary="Get chat history for a session",
    description="Retrieve all messages in a conversation session"
)
async def get_chat_history(session_id: str) -> ChatHistoryResponse:
    """
    Get chat history for a session.

    Args:
        session_id: Session UUID

    Returns:
        ChatHistoryResponse with session info and messages

    Raises:
        HTTPException: If session not found
    """
    service = SessionService()

    try:
        history = service.get_session_history(session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    session = history["session"]
    messages = history["messages"]

    return ChatHistoryResponse(
        session_id=session.id,
        agent_type=session.agent_type,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            ChatMessage(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                tokens_used=msg.tokens_used,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    )
