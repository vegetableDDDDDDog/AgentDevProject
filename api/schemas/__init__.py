"""
Pydantic Schemas for API Request/Response Models

Defines the data models for API requests and responses. These models
provide validation and serialization/deserialization for API endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============================================================================
# Chat Schemas
# ============================================================================

class ChatRequest(BaseModel):
    """
    Request model for chat completion endpoint.

    Clients send this to initiate a conversation with an agent.
    The response is streamed via SSE events.
    """

    agent_type: str = Field(
        ...,
        description="Type of agent to use (e.g., 'mock_chat_agent', 'echo_agent')",
        examples=["mock_chat_agent", "echo_agent"]
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User message to send to the agent"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Existing session ID to continue conversation (optional)"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Agent-specific configuration (e.g., temperature, max_tokens)"
    )

    @field_validator('agent_type')
    @classmethod
    def validate_agent_type(cls, v: str) -> str:
        """Validate that agent_type is not empty."""
        if not v or not v.strip():
            raise ValueError("agent_type cannot be empty")
        return v.strip()


class ChatMessage(BaseModel):
    """
    A single message in the conversation history.
    """

    id: str = Field(description="Unique message ID")
    role: str = Field(description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(description="Message content")
    tokens_used: Optional[int] = Field(default=None, description="Tokens used for this message")
    created_at: datetime = Field(description="Message creation timestamp")


class ChatHistoryResponse(BaseModel):
    """
    Response model for chat history endpoint.

    Returns the session information and all messages in the conversation.
    """

    session_id: str = Field(description="Session ID")
    agent_type: str = Field(description="Agent type for this session")
    created_at: datetime = Field(description="Session creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    messages: List[ChatMessage] = Field(description="List of messages in chronological order")


# ============================================================================
# Agent Schemas
# ============================================================================

class AgentInfo(BaseModel):
    """
    Information about a registered agent type.
    """

    type: str = Field(description="Agent type identifier")
    class_name: str = Field(description="Python class name")
    module: str = Field(description="Python module path")
    description: Optional[str] = Field(default=None, description="Agent description (from docstring)")


class AgentListResponse(BaseModel):
    """
    Response model for listing all available agents.
    """

    agents: List[AgentInfo] = Field(description="List of available agents")
    count: int = Field(description="Total number of agents")


class AgentExecuteRequest(BaseModel):
    """
    Request model for executing a one-shot agent task.

    This is for agents that don't require a conversational session.
    """

    agent_type: str = Field(..., description="Type of agent to execute")
    task: str = Field(..., min_length=1, max_length=10000, description="Task description")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Agent configuration")


class AgentExecuteResponse(BaseModel):
    """
    Response model for agent execution (non-streaming).
    """

    success: bool = Field(description="Whether execution was successful")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Execution result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time_ms: Optional[int] = Field(default=None, description="Execution time in milliseconds")


# ============================================================================
# Session Schemas
# ============================================================================

class SessionCreateRequest(BaseModel):
    """
    Request model for creating a new session.
    """

    agent_type: str = Field(..., description="Agent type for this session")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Session configuration")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Session metadata")


class SessionResponse(BaseModel):
    """
    Response model for session information.
    """

    id: str = Field(description="Session ID")
    agent_type: str = Field(description="Agent type")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Session configuration")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Session metadata")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    message_count: int = Field(default=0, description="Number of messages in session")


class SessionListResponse(BaseModel):
    """
    Response model for listing sessions.
    """

    sessions: List[SessionResponse] = Field(description="List of sessions")
    count: int = Field(description="Total number of sessions")


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    """

    status: str = Field(description="Health status: 'healthy' or 'unhealthy'")
    version: str = Field(description="API version")
    uptime_seconds: float = Field(description="Server uptime in seconds")
    database_connected: bool = Field(description="Whether database is connected")
    agents_registered: int = Field(description="Number of registered agents")


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """
    Standard error response format.
    """

    error: str = Field(description="Error type/code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    path: Optional[str] = Field(default=None, description="Request path that caused the error")
