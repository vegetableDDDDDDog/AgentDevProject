"""
工具使用 Agent - 支持 Function Calling

集成 LangChain Agent 实现自动工具选择和调用。
"""
import time
from typing import Any, Dict, List
from agents.base_agent import BaseAgent
from services.tool_registry import ToolRegistry
from services.tool_adapter import ToolAdapter
from services.database import Session


class ToolUsingAgent(BaseAgent):
    """
    支持工具调用的 Agent

    能力：
    1. 自动选择合适的工具
    2. 规划多步任务
    3. 整合工具结果
    """

    def __init__(
        self,
        name: str,
        role: str,
        tenant_id: str,
        db: Session
    ):
        """
        初始化工具使用 Agent

        Args:
            name: Agent 名称
            role: Agent 角色描述
            tenant_id: 租户 ID
            db: 数据库会话
        """
        super().__init__(name, role)
        self.tenant_id = tenant_id
        self.db = db
        self.tool_registry = ToolRegistry()

    async def execute(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行任务（可调用工具）

        Args:
            task: 任务描述
            context: 上下文信息

        Returns:
            包含执行结果的字典
        """
        # 1. 获取租户可用工具
        # TODO: 从 tenant_context 获取租户配置
        tenant_settings = {
            'enable_search': True,
            'enable_math': True,
            'tenant_id': self.tenant_id
        }

        tools = self.tool_registry.get_tools_for_tenant(
            tenant_id=self.tenant_id,
            tenant_settings=tenant_settings,
            db=self.db
        )

        # 2. 如果没有工具，返回提示
        if not tools:
            return {
                'context': context,
                'done': True,
                'result': '当前没有可用工具。请先配置工具。'
            }

        # 3. 简化实现：使用第一个工具执行任务
        # TODO: 完整实现需要 LangChain Agent
        tool = tools[0]

        try:
            # 执行工具
            if hasattr(tool, '_arun'):
                result = await tool._arun(task)
            else:
                result = tool._run(task)

            return {
                'context': context,
                'done': True,
                'result': f"使用 {tool.name} 执行完成: {result}"
            }

        except Exception as e:
            return {
                'context': context,
                'done': True,
                'result': f"工具执行失败: {str(e)}"
            }

    def get_capabilities(self) -> List[str]:
        """
        返回能力列表

        Returns:
            能力描述列表
        """
        tenant_settings = {
            'enable_search': True,
            'enable_math': True,
            'tenant_id': self.tenant_id
        }

        tools = self.tool_registry.get_tools_for_tenant(
            tenant_id=self.tenant_id,
            tenant_settings=tenant_settings,
            db=self.db
        )

        tool_names = [t.name for t in tools]

        capabilities = [
            f"可以使用工具: {', '.join(tool_names) if tool_names else '无'}",
            "支持自动规划多步任务（TODO: 完整功能待实现）",
            "支持整合多个工具的结果（TODO: 完整功能待实现）"
        ]

        return capabilities
