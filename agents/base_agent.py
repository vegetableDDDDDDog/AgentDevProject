"""
多 Agent 协作 - 基类定义

定义所有 Agent 的统一接口，确保所有协作 Agent 遵循相同的规范。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseAgent(ABC):
    """
    所有 Agent 的基类

    所有参与协作的 Agent 都必须继承此类并实现抽象方法。
    """

    def __init__(self, name: str, role: str):
        """
        初始化 Agent

        Args:
            name: Agent 唯一名称
            role: Agent 角色描述
        """
        self.name = name
        self.role = role
        self.state = {}

    @abstractmethod
    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务的抽象方法

        Args:
            task: 任务描述
            context: 上下文信息（包含前序 Agent 的输出）

        Returns:
            包含执行结果的字典，必须包含：
            - context: 更新后的上下文（传递给下一个 Agent）
            - done: 是否完成任务（用于迭代协作模式）
            - 其他自定义字段
        """
        pass

    def get_info(self) -> Dict[str, str]:
        """
        返回 Agent 信息

        Returns:
            包含 name, role, capabilities 的字典
        """
        return {
            "name": self.name,
            "role": self.role,
            "capabilities": self.get_capabilities()
        }

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        返回 Agent 能力列表

        Returns:
            能力描述列表
        """
        pass

    def __repr__(self) -> str:
        return f"BaseAgent(name={self.name}, role={self.role})"
