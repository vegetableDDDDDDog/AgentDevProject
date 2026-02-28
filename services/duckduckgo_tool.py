"""
DuckDuckGo 搜索工具集成

使用 DuckDuckGo API 进行实时网络搜索，无需 API Key。
"""
import os
from typing import Optional
from langchain.tools import BaseTool
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper


class DuckDuckGoSearchTool(BaseTool):
    """
    DuckDuckGo 搜索工具

    提供免费的实时网络搜索能力，无需 API Key。

    参考:
    - https://python.langchain.com/docs/integrations/tools/ddg/
    """

    name: str = "duckduckgo_search"
    description: str = "搜索实时网络信息，获取最新数据和答案"

    def __init__(
        self,
        max_results: int = 5,
        time_range: str = "w",
        backend: str = "news"
    ):
        """
        初始化 DuckDuckGo 搜索工具

        Args:
            max_results: 最大结果数（默认5）
            time_range: 时间范围（d/day, w/week, m/month, y/year）
            backend: 搜索类型（news, text）
        """
        super().__init__()
        # 使用私有属性避免 Pydantic 验证问题
        object.__setattr__(self, '_max_results', max_results)
        object.__setattr__(self, '_time_range', time_range)
        object.__setattr__(self, '_backend', backend)

        # ✅ 正确的初始化方式（来自Phase 0文档发现）
        object.__setattr__(self, '_searcher', DuckDuckGoSearchResults(
            max_results=max_results,
            backend=backend,
            api_wrapper=DuckDuckGoSearchAPIWrapper(
                time=time_range,  # ✅ time参数在api_wrapper中
                max_results=max_results,
                source=backend
            )
        ))

    @property
    def max_results(self):
        return self._max_results

    @property
    def time_range(self):
        return self._time_range

    @property
    def backend(self):
        return self._backend

    @property
    def searcher(self):
        return self._searcher

    def _run(self, query: str) -> str:
        """
        执行搜索

        Args:
            query: 搜索查询

        Returns:
            str: 搜索结果（格式化字符串）
        """
        try:
            # ✅ 使用invoke()，不是run()
            results = self.searcher.invoke(query)

            # invoke()返回tuple: (formatted_results, raw_results)
            if isinstance(results, tuple):
                formatted_results, _ = results
                return formatted_results
            else:
                return results

        except Exception as e:
            return self._handle_error(e)

    def _handle_error(self, error: Exception) -> str:
        """
        优雅的错误处理

        Args:
            error: 异常对象

        Returns:
            str: 友好的错误信息
        """
        error_msg = str(error).lower()

        if "timeout" in error_msg or "timed out" in error_msg:
            return "搜索超时，请稍后重试"
        elif "rate limit" in error_msg:
            return "搜索频率过高，请稍后再试"
        elif "no results" in error_msg or "0 results" in error_msg:
            return "未找到相关结果"
        else:
            return f"搜索出错: {str(error)}"

    async def _arun(self, query: str) -> str:
        """
        异步执行搜索

        Args:
            query: 搜索查询

        Returns:
            str: 搜索结果
        """
        return self._run(query)
