import pytest
from services.duckduckgo_tool import DuckDuckGoSearchTool


class TestDuckDuckGoSearchTool:
    """DuckDuckGo 搜索工具测试"""

    def test_tool_initialization(self):
        """测试工具初始化"""
        tool = DuckDuckGoSearchTool()
        assert tool.name == "duckduckgo_search"
        assert tool.max_results == 5
        assert tool.backend == "news"

    def test_basic_search(self):
        """测试基本搜索功能"""
        tool = DuckDuckGoSearchTool(max_results=3)
        result = tool._run("Python programming")

        # 验证返回结果
        assert isinstance(result, str)
        assert len(result) > 0
        print(f"搜索结果: {result[:200]}...")  # 打印前200个字符

    def test_search_with_time_range(self):
        """测试带时间范围的搜索"""
        tool = DuckDuckGoSearchTool(time_range="d")  # 最近一天
        result = tool._run("AI news")
        assert isinstance(result, str)

    def test_error_handling_empty_query(self):
        """测试空查询的错误处理"""
        tool = DuckDuckGoSearchTool()
        result = tool._run("")
        # 应该返回某种错误信息或空结果
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_async_search(self):
        """测试异步搜索"""
        tool = DuckDuckGoSearchTool()
        result = await tool._arun("Python")
        assert isinstance(result, str)
