"""
Tavily 搜索工具集成

使用 Tavily API 进行实时网络搜索。
"""
import os
from typing import List, Dict, Any
from langchain.tools import BaseTool
from langchain.utilities.tavily import TavilySearchResults


class TavilySearchTool(BaseTool):
    """
    Tavily 搜索工具

    提供 AI 驱动的实时网络搜索能力。
    """

    name = "tavily_search"
    description = "搜索实时网络信息，获取最新数据和答案"

    def __init__(self, api_key: str = None, max_results: int = 5):
        """
        初始化 Tavily 搜索工具

        Args:
            api_key: Tavily API Key（可选，默认从环境变量读取）
            max_results: 最大结果数量
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.max_results = max_results

        if not self.api_key:
            print("⚠️  警告: 未配置 TAVILY_API_KEY，搜索功能将不可用")

    def _run(self, query: str) -> str:
        """
        执行搜索（同步）

        Args:
            query: 搜索查询

        Returns:
            str: 搜索结果
        """
        if not self.api_key:
            return "错误: 未配置 Tavily API Key"

        try:
            # 创建 Tavily 搜索工具
            search = TavilySearchResults(
                api_key=self.api_key,
                max_results=self.max_results,
                search_depth="basic",
                include_domains=[],
                exclude_domains=[]
            )

            # 执行搜索
            results = search._run(query)

            # 格式化结果
            return self._format_results(results)

        except Exception as e:
            return f"搜索失败: {str(e)}"

    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        格式化搜索结果

        Args:
            results: Tavily 返回的结果

        Returns:
            str: 格式化的结果字符串
        """
        if not results:
            return "未找到相关结果"

        formatted = []
        for i, result in enumerate(results[:5], 1):
            title = result.get('title', '无标题')
            url = result.get('url', '')
            content = result.get('content', '')[:200]

            formatted.append(f"{i}. {title}\n   {url}\n   {content}...\n")

        return "\n".join(formatted)

    async def _arun(self, query: str) -> str:
        """
        异步执行搜索

        Args:
            query: 搜索查询

        Returns:
            str: 搜索结果
        """
        # 对于网络请求，同步和异步差异不大
        return self._run(query)
