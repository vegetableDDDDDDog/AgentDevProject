"""
SSE (Server-Sent Events) Protocol Definition

Defines the event types and data structures for streaming responses
from agents to clients using Server-Sent Events.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import json


class SSEEventType(str, Enum):
    """
    SSE event types for agent streaming responses.

    Events are sent in the following sequence:
    1. thought - Agent thinking/reasoning steps (optional)
    2. message - Text content chunks (streamed)
    3. error - Error information (if error occurs)
    4. done - Stream completion marker (always sent last)
    """

    MESSAGE = "message"   # Normal text output (streamed in chunks)
    THOUGHT = "thought"   # Intermediate thinking steps
    ERROR = "error"       # Error information
    DONE = "done"         # Stream end marker


class SSEMessage(BaseModel):
    """
    Message event data for streaming text content.

    Sent as SSE events with type "message".
    Clients should display these chunks as they arrive.
    """

    content: str = Field(description="Text content chunk")
    type: str = Field(default="text", description="Content type (text, code, etc.)")

    def to_sse(self) -> str:
        """Convert to SSE format string."""
        return f"event: {SSEEventType.MESSAGE.value}\ndata: {self.model_dump_json()}\n\n"


class SSEThought(BaseModel):
    """
    Thought event data for intermediate reasoning steps.

    Sent as SSE events with type "thought".
    Clients can display these differently (e.g., in a collapsible section).
    """

    content: str = Field(description="Thought/reasoning content")
    step: Optional[int] = Field(default=None, description="Step number (optional)")

    def to_sse(self) -> str:
        """Convert to SSE format string."""
        return f"event: {SSEEventType.THOUGHT.value}\ndata: {self.model_dump_json()}\n\n"


class SSEError(BaseModel):
    """
    Error event data for error reporting.

    Sent as SSE events with type "error".
    Indicates that an error occurred during agent execution.
    """

    message: str = Field(description="Error message")
    code: Optional[str] = Field(default=None, description="Error code (optional)")
    details: Optional[dict] = Field(default=None, description="Additional error details")

    def to_sse(self) -> str:
        """Convert to SSE format string."""
        return f"event: {SSEEventType.ERROR.value}\ndata: {self.model_dump_json()}\n\n"


class SSEDone(BaseModel):
    """
    Done event data for stream completion.

    Sent as the final SSE event with type "done".
    Indicates that the agent has completed execution.
    """

    session_id: str = Field(description="Session ID for the conversation")
    tokens_used: Optional[int] = Field(default=None, description="Total tokens used")
    execution_time_ms: Optional[int] = Field(default=None, description="Execution time in milliseconds")

    def to_sse(self) -> str:
        """Convert to SSE format string."""
        return f"event: {SSEEventType.DONE.value}\ndata: {self.model_dump_json()}\n\n"


def create_sse_event(event_type: SSEEventType, data: dict) -> str:
    """
    Create an SSE event string from an event type and data dict.

    This is a convenience function for creating SSE events without
    instantiating the specific event model classes.

    Args:
        event_type: The type of SSE event
        data: The data payload for the event

    Returns:
        A formatted SSE event string

    Example:
        event = create_sse_event(SSEEventType.MESSAGE, {"content": "Hello"})
        # Returns: "event: message\ndata: {\"content\":\"Hello\"}\n\n"
    """
    data_json = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type.value}\ndata: {data_json}\n\n"


async def sse_generator(event_iterator):
    """
    Convert an iterator of SSE events to an async generator for FastAPI.

    This function takes an iterator of SSE event objects (SSEMessage,
    SSEThought, SSEError, SSEDone) and converts them to the string format
    expected by FastAPI's StreamingResponse.

    Args:
        event_iterator: Iterator of SSE event objects

    Yields:
        SSE formatted strings

    Example:
        async def stream_response():
            yield SSEMessage(content="Hello")
            yield SSEMessage(content=" World")
            yield SSEDone(session_id="abc123")

        return StreamingResponse(
            sse_generator(stream_response()),
            media_type="text/event-stream"
        )
    """
    for event in event_iterator:
        if hasattr(event, 'to_sse'):
            yield event.to_sse()
        else:
            # Fallback for raw dicts
            yield create_sse_event(event.get("type", SSEEventType.MESSAGE), event.get("data", {}))
