"""
工具注册表 - 管理标准工具和自定义工具
"""
import os
from typing import List
from services.tool_adapter import ToolAdapter
from services.database import Session
from services.duckduckgo_tool import DuckDuckGoSearchTool
from services.llm_math_tool import LLMMathTool


class ToolRegistry:
    """
    租户级别的工具注册表

    核心职责：
    1. 管理内置标准工具
    2. 根据租户配置返回可用工具列表
    3. 为每个工具创建多租户适配器
    """

    def __init__(self):
        """初始化工具注册表"""
        self._builtin_tools = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """注册内置标准工具（工具类，占位符）"""
        self._builtin_tools = {
            'duckduckgo_search': 'DuckDuckGoSearchTool',
            'llm_math': 'LLMMathTool',
        }

    def get_tools_for_tenant(
        self,
        tenant_id: str,
        tenant_settings: dict,
        db: Session
    ) -> List[ToolAdapter]:
        """
        根据租户配置返回可用工具列表

        Args:
            tenant_id: 租户 ID
            tenant_settings: 租户配置 (from tenants.settings)
            db: 数据库会话

        Returns:
            ToolAdapter 列表
        """
        tools = []

        # 网络搜索（默认开启）
        if tenant_settings.get('enable_search', True):
            search_tool = DuckDuckGoSearchTool(
                max_results=tenant_settings.get('search_max_results', 5),
                time_range=tenant_settings.get('search_time_range', 'w'),
                backend='news'
            )
            tools.append(ToolAdapter(search_tool, tenant_id, db))

        # 数学计算（默认开启）
        if tenant_settings.get('enable_math', True):
            math_tool = LLMMathTool()  # 不需要 LLMService，使用安全 eval
            tools.append(ToolAdapter(math_tool, tenant_id, db))

        return tools

    def get_tool_info(self, tool_name: str) -> dict:
        """
        获取工具信息

        Args:
            tool_name: 工具名称

        Returns:
            工具信息字典，如果不存在则返回 None
        """
        if tool_name in self._builtin_tools:
            return {
                'name': tool_name,
                'class': self._builtin_tools[tool_name],
                'description': f'Tool class: {self._builtin_tools[tool_name]}'
            }
        return None

    def list_all_tools(self) -> List[str]:
        """
        列出所有注册的工具

        Returns:
            工具名称列表
        """
        return list(self._builtin_tools.keys())
