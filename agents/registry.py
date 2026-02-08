"""
多 Agent 协作 - Agent 注册表

统一管理所有 Agent 实例的注册和查询。
"""

from typing import Dict, Optional, List
from agents.base_agent import BaseAgent


class AgentRegistry:
    """
    Agent 注册表

    提供统一的 Agent 注册、查询和管理功能。
    """

    def __init__(self):
        """初始化注册表"""
        self.agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """
        注册 Agent

        Args:
            agent: Agent 实例

        Raises:
            ValueError: 如果名称已存在
        """
        if agent.name in self.agents:
            raise ValueError(f"Agent '{agent.name}' 已存在")

        self.agents[agent.name] = agent
        print(f"✅ Agent 已注册: {agent.name} ({agent.role})")

    def get(self, name: str) -> Optional[BaseAgent]:
        """
        获取 Agent

        Args:
            name: Agent 名称

        Returns:
            Agent 实例，如果不存在则返回 None
        """
        return self.agents.get(name)

    def unregister(self, name: str) -> bool:
        """
        注销 Agent

        Args:
            name: Agent 名称

        Returns:
            是否成功注销
        """
        if name in self.agents:
            del self.agents[name]
            print(f"🗑️ Agent 已注销: {name}")
            return True
        return False

    def list_all(self) -> Dict[str, str]:
        """
        列出所有 Agent

        Returns:
            Agent 名称和角色的字典
        """
        return {
            name: agent.role
            for name, agent in self.agents.items()
        }

    def get_capabilities(self, name: str) -> List[str]:
        """
        获取指定 Agent 的能力列表

        Args:
            name: Agent 名称

        Returns:
            能力列表，如果 Agent 不存在则返回空列表
        """
        agent = self.get(name)
        return agent.get_capabilities() if agent else []

    def count(self) -> int:
        """
        获取注册的 Agent 数量

        Returns:
            Agent 数量
        """
        return len(self.agents)

    def clear(self) -> None:
        """清空所有注册的 Agent"""
        self.agents.clear()
        print("🗑️ 已清空所有 Agent 注册")

    def __repr__(self) -> str:
        return f"AgentRegistry(count={self.count()})"
