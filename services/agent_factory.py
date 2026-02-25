"""
Agent 工厂 - 动态注册和实例化

本模块提供基于装饰器的 Agent 类注册模式。
Agent 在模块导入时通过 @register_agent 装饰器注册，
并可通过 get_agent() 工厂函数动态实例化。

示例:
    @register_agent("chat_basic")
    class ChatAgent(BaseAgent):
        def __init__(self, config: dict = None):
            super().__init__(name="chat_basic", role="对话助手")
            self.config = config or {}

    # 稍后，创建实例
    agent = get_agent("chat_basic", {"temperature": 0.7})
"""

from typing import Dict, Type, Optional, Any, List
from agents.base_agent import BaseAgent


# Agent 类的全局注册表
# 将 agent_type 字符串映射到 Agent 类
agent_registry: Dict[str, Type[BaseAgent]] = {}


def register_agent(name: str) -> callable:
    """
    用于在全局注册表中注册 Agent 类的装饰器。

    被装饰的类必须是 BaseAgent 的子类，并会以提供的名称
    作为键存储在 agent_registry 中。

    Args:
        name: 此 Agent 类型的唯一标识符（例如 "chat_basic", "rag_agent"）

    Returns:
        装饰器函数，注册类并原样返回

    Raises:
        ValueError: 如果同名的 Agent 已经被注册
        TypeError: 如果被装饰的类不是 BaseAgent 的子类

    示例:
        @register_agent("chat_basic")
        class ChatAgent(BaseAgent):
            def __init__(self, config: dict = None):
                super().__init__(name="chat_basic", role="对话助手")
    """
    def decorator(cls: Type[BaseAgent]) -> Type[BaseAgent]:
        # 验证该类是 BaseAgent 的子类
        if not issubclass(cls, BaseAgent):
            raise TypeError(
                f"Agent '{name}' 必须继承自 BaseAgent，"
                f"但得到 {cls.__name__} ({cls.__bases__})"
            )

        # 检查重复注册
        if name in agent_registry:
            existing_class = agent_registry[name]
            raise ValueError(
                f"Agent 类型 '{name}' 已被 {existing_class.__name__} 注册。"
                f"无法用 {cls.__name__} 重新注册。"
            )

        # 注册该类
        agent_registry[name] = cls
        return cls

    return decorator


def get_agent(agent_type: str, config: Optional[dict] = None) -> BaseAgent:
    """
    通过类型创建 Agent 实例的工厂函数。

    在注册表中查找 Agent 类，并使用提供的配置实例化它。

    Args:
        agent_type: 要创建的 Agent 的类型标识符
        config: 可选的配置字典，传递给 Agent 的 __init__

    Returns:
        请求的 Agent 类的实例

    Raises:
        ValueError: 如果 agent_type 未注册
        Exception: 传播来自 Agent __init__ 的任何异常

    示例:
        agent = get_agent("chat_basic", {"temperature": 0.7, "max_tokens": 2000})
        result = await agent.execute("你好！", {})
    """
    agent_class = agent_registry.get(agent_type)

    if agent_class is None:
        available = ", ".join(agent_registry.keys())
        raise ValueError(
            f"未知的 agent 类型: '{agent_type}'。"
            f"可用的 agents: {available or '无'}"
        )

    # 使用配置实例化（如果为 None 则使用空字典）
    try:
        return agent_class(config or {})
    except Exception as e:
        raise RuntimeError(
            f"实例化 agent '{agent_type}' 失败: {str(e)}"
        ) from e


def list_agents() -> Dict[str, Dict[str, Any]]:
    """
    列出所有已注册的 Agent 类型及其元数据。

    返回将 agent 类型映射到元数据的字典，包括类名
    以及当前是否可用。

    Returns:
        以 agent_type 为键，包含 'class_name' 的字典为值的字典

    示例:
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
    获取特定已注册 Agent 的详细信息。

    Args:
        agent_type: Agent 的类型标识符

    Returns:
        包含 Agent 元数据（class_name, module）的字典，如果未找到则为 None
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
    检查 Agent 类型是否已注册。

    Args:
        agent_type: 要检查的类型标识符

    Returns:
        如果 Agent 类型已注册返回 True，否则返回 False
    """
    return agent_type in agent_registry


def clear_registry() -> None:
    """
    清除所有已注册的 Agents。

    警告: 这主要用于测试。在生产代码中使用此函数
    将导致所有 Agents 不可用。
    """
    agent_registry.clear()


def get_registry_count() -> int:
    """
    获取已注册 Agent 类型的数量。

    Returns:
        已注册 Agent 类型的计数
    """
    return len(agent_registry)
