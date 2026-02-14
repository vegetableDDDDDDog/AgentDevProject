"""
Agent Factory - Dynamic Agent Registration and Instantiation

This module provides a decorator-based registry pattern for Agent classes.
Agents are registered at module import time using the @register_agent decorator,
and can be dynamically instantiated using the get_agent() factory function.

Example:
    @register_agent("chat_basic")
    class ChatAgent(BaseAgent):
        def __init__(self, config: dict = None):
            super().__init__(name="chat_basic", role="Conversational Agent")
            self.config = config or {}

    # Later, create an instance
    agent = get_agent("chat_basic", {"temperature": 0.7})
"""

from typing import Dict, Type, Optional, Any, List
from agents.base_agent import BaseAgent


# Global registry for Agent classes
# Maps agent_type string to Agent class
agent_registry: Dict[str, Type[BaseAgent]] = {}


def register_agent(name: str) -> callable:
    """
    Decorator to register an Agent class in the global registry.

    The decorated class must be a subclass of BaseAgent and will be
    stored in agent_registry with the provided name as the key.

    Args:
        name: Unique identifier for this agent type (e.g., "chat_basic", "rag_agent")

    Returns:
        Decorator function that registers the class and returns it unchanged

    Raises:
        ValueError: If an agent with the same name is already registered
        TypeError: If the decorated class is not a subclass of BaseAgent

    Example:
        @register_agent("chat_basic")
        class ChatAgent(BaseAgent):
            def __init__(self, config: dict = None):
                super().__init__(name="chat_basic", role="Chat")
    """
    def decorator(cls: Type[BaseAgent]) -> Type[BaseAgent]:
        # Validate that the class is a BaseAgent subclass
        if not issubclass(cls, BaseAgent):
            raise TypeError(
                f"Agent '{name}' must inherit from BaseAgent, "
                f"got {cls.__name__} ({cls.__bases__})"
            )

        # Check for duplicate registration
        if name in agent_registry:
            existing_class = agent_registry[name]
            raise ValueError(
                f"Agent type '{name}' is already registered by {existing_class.__name__}. "
                f"Cannot re-register with {cls.__name__}."
            )

        # Register the class
        agent_registry[name] = cls
        return cls

    return decorator


def get_agent(agent_type: str, config: Optional[dict] = None) -> BaseAgent:
    """
    Factory function to create an Agent instance by type.

    Looks up the Agent class in the registry and instantiates it with
    the provided configuration.

    Args:
        agent_type: The type identifier of the agent to create
        config: Optional configuration dictionary passed to Agent's __init__

    Returns:
        An instance of the requested Agent class

    Raises:
        ValueError: If agent_type is not registered
        Exception: Propagates any exception from Agent's __init__

    Example:
        agent = get_agent("chat_basic", {"temperature": 0.7, "max_tokens": 2000})
        result = await agent.execute("Hello!", {})
    """
    agent_class = agent_registry.get(agent_type)

    if agent_class is None:
        available = ", ".join(agent_registry.keys())
        raise ValueError(
            f"Unknown agent type: '{agent_type}'. "
            f"Available agents: {available or 'None'}"
        )

    # Instantiate with config (or empty dict if None)
    try:
        return agent_class(config or {})
    except Exception as e:
        raise RuntimeError(
            f"Failed to instantiate agent '{agent_type}': {str(e)}"
        ) from e


def list_agents() -> Dict[str, Dict[str, Any]]:
    """
    List all registered agent types with their metadata.

    Returns a dictionary mapping agent type to metadata including
    the class name and whether it's currently available.

    Returns:
        Dictionary with agent_type as key and dict with 'class_name' as value

    Example:
        {
            "chat_basic": {"class_name": "ChatAgent"},
            "rag_agent": {"class_name": "RAGAgent"},
            "tool_agent": {"class_name": "ToolAgent"}
        }
    """
    return {
        agent_type: {
            "class_name": cls.__name__,
            "module": cls.__module__
        }
        for agent_type, cls in agent_registry.items()
    }


def get_agent_info(agent_type: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific registered agent.

    Args:
        agent_type: The type identifier of the agent

    Returns:
        Dictionary with agent metadata (class_name, module) or None if not found
    """
    cls = agent_registry.get(agent_type)
    if cls is None:
        return None

    return {
        "type": agent_type,
        "class_name": cls.__name__,
        "module": cls.__module__,
        "doc": cls.__doc__
    }


def is_registered(agent_type: str) -> bool:
    """
    Check if an agent type is registered.

    Args:
        agent_type: The type identifier to check

    Returns:
        True if the agent type is registered, False otherwise
    """
    return agent_type in agent_registry


def clear_registry() -> None:
    """
    Clear all registered agents.

    WARNING: This is primarily intended for testing. Using this in
    production code will make all agents unavailable.
    """
    agent_registry.clear()


def get_registry_count() -> int:
    """
    Get the number of registered agent types.

    Returns:
        Count of registered agent types
    """
    return len(agent_registry)
