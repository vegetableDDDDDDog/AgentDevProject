"""
多 Agent 协作 - 状态管理器

负责 Agent 之间的状态共享和通信。
"""

from typing import Any, Dict, List
from datetime import datetime


class SharedStateManager:
    """
    Agent 间共享状态管理

    提供状态存储、更新、查询和历史记录功能。
    """

    def __init__(self, session_id: str):
        """
        初始化状态管理器

        Args:
            session_id: 会话唯一标识
        """
        self.session_id = session_id
        self.state: Dict[str, Dict[str, Any]] = {}
        self.history: List[Dict[str, Any]] = []

    def update(self, agent_name: str, key: str, value: Any) -> None:
        """
        更新状态

        Args:
            agent_name: Agent 名称
            key: 状态键
            value: 状态值
        """
        if agent_name not in self.state:
            self.state[agent_name] = {}

        self.state[agent_name][key] = value

        # 记录历史
        self.history.append({
            "agent": agent_name,
            "action": "update",
            "key": key,
            "timestamp": datetime.now().isoformat()
        })

    def get(self, agent_name: str, key: str, default: Any = None) -> Any:
        """
        获取状态

        Args:
            agent_name: Agent 名称
            key: 状态键
            default: 默认值

        Returns:
            状态值，如果不存在则返回默认值
        """
        return self.state.get(agent_name, {}).get(key, default)

    def get_agent_state(self, agent_name: str) -> Dict[str, Any]:
        """
        获取指定 Agent 的所有状态

        Args:
            agent_name: Agent 名称

        Returns:
            该 Agent 的所有状态
        """
        return self.state.get(agent_name, {}).copy()

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有状态

        Returns:
            所有 Agent 的状态
        """
        return self.state.copy()

    def get_history(self) -> List[Dict[str, Any]]:
        """
        获取历史记录

        Returns:
            状态变更历史列表
        """
        return self.history.copy()

    def clear(self) -> None:
        """清空所有状态"""
        self.state.clear()
        self.history.clear()

    def __repr__(self) -> str:
        return f"SharedStateManager(session_id={self.session_id}, agents={len(self.state)})"
