"""
Simple Agents for Testing and Quick Start

These agents demonstrate the agent factory registration pattern and can
be used for testing without consuming LLM tokens.
"""

import asyncio
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from services.agent_factory import register_agent


@register_agent("echo_agent")
class EchoAgent(BaseAgent):
    """
    A simple echo agent that returns the task text as-is.

    Useful for testing the agent factory without consuming API tokens.
    """

    def __init__(self, config: dict = None):
        super().__init__(name="echo_agent", role="Echo Agent")
        self.config = config or {}

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Return the task text unchanged."""
        # Simulate some processing time
        await asyncio.sleep(0.1)

        return {
            "response": f"Echo: {task}",
            "context": context,
            "done": True
        }

    def get_capabilities(self) -> List[str]:
        return ["echo", "test", "debug"]


@register_agent("mock_chat_agent")
class MockChatAgent(BaseAgent):
    """
    A mock chat agent that returns predefined responses.

    Useful for testing chat interfaces without calling real LLM APIs.
    """

    def __init__(self, config: dict = None):
        super().__init__(name="mock_chat_agent", role="Mock Chat Agent")
        self.config = config or {}
        self.response_count = 0

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Return a mock response based on the task."""
        await asyncio.sleep(0.2)

        self.response_count += 1

        # Generate a mock response
        responses = [
            f"I understand you said: {task}",
            f"Interesting! Tell me more about: {task}",
            f"Here's my thought on '{task}': This is a mock response.",
            f"Processing complete for: {task}"
        ]

        response = responses[self.response_count % len(responses)]

        return {
            "response": response,
            "context": {**context, "last_task": task},
            "done": True,
            "tokens_used": 10  # Mock token count
        }

    def get_capabilities(self) -> List[str]:
        return ["chat", "conversation", "mock"]


@register_agent("counter_agent")
class CounterAgent(BaseAgent):
    """
    A simple agent that counts how many times it has been executed.

    Useful for testing state management and session persistence.
    """

    def __init__(self, config: dict = None):
        super().__init__(name="counter_agent", role="Counter Agent")
        self.config = config or {}
        self.execution_count = 0

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Increment counter and return current count."""
        await asyncio.sleep(0.1)

        self.execution_count += 1

        return {
            "response": f"This agent has been executed {self.execution_count} times",
            "context": {
                **context,
                "execution_count": self.execution_count
            },
            "done": True
        }

    def get_capabilities(self) -> List[str]:
        return ["count", "state", "test"]

    def reset_count(self) -> None:
        """Reset the execution counter."""
        self.execution_count = 0


@register_agent("error_agent")
class ErrorAgent(BaseAgent):
    """
    An agent that simulates errors for testing error handling.

    Can be configured to raise different types of errors.
    """

    def __init__(self, config: dict = None):
        super().__init__(name="error_agent", role="Error Simulation Agent")
        self.config = config or {}
        self.error_type = self.config.get("error_type", "none")

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate an error based on configuration."""
        await asyncio.sleep(0.1)

        error_map = {
            "value": ValueError("Simulated ValueError"),
            "runtime": RuntimeError("Simulated RuntimeError"),
            "timeout": asyncio.TimeoutError("Simulated timeout"),
        }

        if self.error_type in error_map:
            raise error_map[self.error_type]

        return {
            "response": f"No error (error_type={self.error_type})",
            "context": context,
            "done": True
        }

    def get_capabilities(self) -> List[str]:
        return ["error_simulation", "test", "debug"]
