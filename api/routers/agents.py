"""
Agents Router - Agent Management

Provides endpoints for listing available agents and executing one-shot tasks.
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status

from api.schemas import (
    AgentInfo,
    AgentListResponse,
    AgentExecuteRequest,
    AgentExecuteResponse
)
from services.agent_factory import (
    list_agents,
    get_agent_info,
    is_registered,
    get_agent
)

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List all available agents",
    description="Get a list of all registered agent types with their metadata"
)
async def list_available_agents() -> AgentListResponse:
    """
    List all available agent types.

    Returns information about each registered agent including
    the class name and module path.

    Returns:
        AgentListResponse with list of agent info
    """
    agents_dict = list_agents()

    agents = [
        AgentInfo(
            type=agent_type,
            class_name=info["class_name"],
            module=info["module"],
            description=info.get("doc")
        )
        for agent_type, info in agents_dict.items()
    ]

    return AgentListResponse(
        agents=agents,
        count=len(agents)
    )


@router.get(
    "/{agent_type}",
    summary="Get agent information",
    description="Get detailed information about a specific agent type"
)
async def get_agent_details(agent_type: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific agent.

    Args:
        agent_type: The agent type identifier

    Returns:
        Dictionary with agent details

    Raises:
        HTTPException: If agent not found
    """
    info = get_agent_info(agent_type)

    if info is None:
        # List available agents in error message
        available = ", ".join(list_agents().keys())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_type}' not found. Available: {available}"
        )

    return info


@router.post(
    "/{agent_type}/execute",
    response_model=AgentExecuteResponse,
    summary="Execute a one-shot agent task",
    description="Execute an agent task without creating a session (non-streaming)"
)
async def execute_agent_task(
    agent_type: str,
    task: str,
    config: Dict[str, Any] = None
) -> AgentExecuteResponse:
    """
    Execute a one-shot agent task.

    This endpoint executes an agent task without creating a conversational session.
    The response is returned all at once (non-streaming).

    Args:
        agent_type: The type of agent to execute
        task: The task description
        config: Optional agent configuration

    Returns:
        AgentExecuteResponse with execution result

    Raises:
        HTTPException: If agent not found or execution fails
    """
    # Validate agent exists
    if not is_registered(agent_type):
        available = ", ".join(list_agents().keys())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_type}' not found. Available: {available}"
        )

    start_time = time.time()

    try:
        # Get agent instance with config
        config = config or {}
        agent = get_agent(agent_type, config)

        # Execute agent
        result = await agent.execute(task, {})

        execution_time = int((time.time() - start_time) * 1000)

        return AgentExecuteResponse(
            success=True,
            result=result,
            execution_time_ms=execution_time
        )

    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)

        return AgentExecuteResponse(
            success=False,
            error=str(e),
            execution_time_ms=execution_time
        )
