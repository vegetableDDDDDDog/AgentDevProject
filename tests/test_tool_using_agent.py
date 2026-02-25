"""
工具使用 Agent 测试
"""
import pytest
from unittest.mock import Mock, patch
from agents.tool_using_agent import ToolUsingAgent


@pytest.fixture
def mock_db():
    return Mock()


@pytest.fixture
def tool_agent(mock_db):
    return ToolUsingAgent(
        name="tool_using",
        role="工具使用专家",
        tenant_id="test-tenant-id",
        db=mock_db
    )


class TestToolUsingAgent:
    """ToolUsingAgent 测试套件"""

    def test_agent_creation(self, tool_agent):
        """测试 Agent 创建"""
        assert tool_agent.name == "tool_using"
        assert tool_agent.role == "工具使用专家"
        assert tool_agent.tenant_id == "test-tenant-id"

    def test_get_capabilities_with_tools(self, tool_agent):
        """测试获取能力（有工具）"""
        with patch.object(tool_agent.tool_registry, 'get_tools_for_tenant') as mock_get:
            # 模拟返回工具
            mock_tool = Mock()
            mock_tool.name = "test_tool"
            mock_get.return_value = [mock_tool]

            capabilities = tool_agent.get_capabilities()

            assert "test_tool" in capabilities[0]

    def test_get_capabilities_no_tools(self, tool_agent):
        """测试获取能力（无工具）"""
        with patch.object(tool_agent.tool_registry, 'get_tools_for_tenant') as mock_get:
            mock_get.return_value = []

            capabilities = tool_agent.get_capabilities()

            assert "无" in capabilities[0]

    @pytest.mark.asyncio
    async def test_execute_with_tools(self, tool_agent):
        """测试执行任务（有工具）"""
        with patch.object(tool_agent.tool_registry, 'get_tools_for_tenant') as mock_get:
            # 模拟工具
            mock_tool = Mock()
            mock_tool.name = "test_tool"
            mock_tool._arun = Mock(return_value="工具执行成功")
            mock_get.return_value = [mock_tool]

            result = await tool_agent.execute("测试任务", {})

            assert result['done'] is True
            assert "工具执行成功" in result['result']

    @pytest.mark.asyncio
    async def test_execute_without_tools(self, tool_agent):
        """测试执行任务（无工具）"""
        with patch.object(tool_agent.tool_registry, 'get_tools_for_tenant') as mock_get:
            mock_get.return_value = []

            result = await tool_agent.execute("测试任务", {})

            assert result['done'] is True
            assert "没有可用工具" in result['result']
