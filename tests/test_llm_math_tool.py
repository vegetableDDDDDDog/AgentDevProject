import pytest
from services.llm_math_tool import LLMMathTool


class TestLLMMathTool:
    """LLM 数学计算工具测试"""

    def test_tool_initialization(self):
        """测试工具初始化（无 LLM）"""
        tool = LLMMathTool()
        assert tool.name == "llm_math"
        assert tool.llm_service is None

    def test_basic_calculation(self):
        """测试基本计算"""
        tool = LLMMathTool()
        result = tool._run("2 + 2")
        assert "4" in result
        print(f"2 + 2 = {result}")

    def test_complex_calculation(self):
        """测试复杂计算"""
        tool = LLMMathTool()
        result = tool._run("123 * 456 + 789")
        assert "56877" in result
        print(f"123 * 456 + 789 = {result}")

    def test_error_handling_invalid_expression(self):
        """测试无效表达式的错误处理"""
        tool = LLMMathTool()
        result = tool._run("invalid expression")
        # 应该返回错误信息
        assert isinstance(result, str)
        print(f"无效表达式结果: {result}")

    def test_power_operator(self):
        """测试幂运算"""
        tool = LLMMathTool()
        result = tool._run("2 ^ 3")  # 会转换为 2 ** 3
        assert "8" in result
        print(f"2 ^ 3 = {result}")

    @pytest.mark.asyncio
    async def test_async_calculation(self):
        """测试异步计算"""
        tool = LLMMathTool()
        result = await tool._arun("5 + 5")
        assert "10" in result
