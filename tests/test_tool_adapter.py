"""
工具适配器测试

测试 ToolAdapter 多租户适配器的功能。
"""
import pytest
import uuid
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from services.tool_adapter import ToolAdapter
from services.database import Session, SessionLocal


class MockTool:
    """模拟 LangChain 工具"""
    name = "mock_search_tool"
    description = "A mock search tool for testing"

    def _run(self, query: str) -> str:
        """同步执行"""
        return f"Result for: {query}"

    async def _arun(self, query: str) -> str:
        """异步执行"""
        return f"Async result for: {query}"


@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    return db


@pytest.fixture
def mock_tool():
    """模拟工具实例"""
    return MockTool()


@pytest.fixture
def tool_adapter(mock_tool, mock_db):
    """工具适配器实例"""
    return ToolAdapter(
        tool=mock_tool,
        tenant_id="test-tenant-id",
        db=mock_db
    )


class TestToolAdapter:
    """ToolAdapter 测试套件"""

    def test_tool_adapter_creation(self, tool_adapter):
        """测试工具适配器创建"""
        assert tool_adapter.name == "mock_search_tool"
        assert tool_adapter.tenant_id == "test-tenant-id"
        assert tool_adapter.description == "A mock search tool for testing"

    def test_tool_adapter_repr(self, tool_adapter):
        """测试 __repr__ 方法"""
        repr_str = repr(tool_adapter)
        assert "ToolAdapter" in repr_str
        assert "mock_search_tool" in repr_str
        assert "test-tenant-id" in repr_str

    @pytest.mark.asyncio
    async def test_tool_adapter_async_run(self, tool_adapter):
        """测试工具适配器异步执行"""
        # 模拟成功执行
        result = await tool_adapter._arun("test query")

        assert "Async result for: test query" in result

    def test_tool_adapter_sync_run(self, tool_adapter):
        """测试工具适配器同步执行"""
        result = tool_adapter._run("test query")

        assert "Result for: test query" in result

    def test_record_metrics_success(self, tool_adapter):
        """测试记录成功指标"""
        # 应该不抛出异常
        tool_adapter._record_metrics(
            success=True,
            execution_time=0.5
        )

    def test_record_metrics_failure(self, tool_adapter):
        """测试记录失败指标"""
        # 应该不抛出异常
        tool_adapter._record_metrics(
            success=False,
            error="Test error",
            execution_time=0.3
        )

    def test_write_audit_log_success(self, tool_adapter, mock_db):
        """测试写入成功日志"""
        # 应该不抛出异常
        tool_adapter._write_audit_log(
            input_data={"query": "test"},
            output_data="test result",
            status="success",
            execution_time_ms=100
        )

        # 验证数据库操作被调用
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_write_audit_log_error(self, tool_adapter, mock_db):
        """测试写入错误日志"""
        tool_adapter._write_audit_log(
            input_data={"query": "test"},
            output_data=None,
            status="error",
            execution_time_ms=50,
            error_message="Test error"
        )

        # 验证数据库操作被调用
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_adapter_with_sync_tool(self, mock_db):
        """测试适配器包装只有同步方法的工具"""
        class SyncOnlyTool:
            name = "sync_tool"
            description = "Sync only tool"

            def _run(self, query: str) -> str:
                return f"Sync result: {query}"

        tool = SyncOnlyTool()
        adapter = ToolAdapter(tool, "tenant-123", mock_db)

        # 应该能够执行
        result = await adapter._arun("test")
        assert "Sync result: test" in result


class TestToolAdapterIntegration:
    """ToolAdapter 集成测试"""

    def test_adapter_with_database_session(self):
        """测试适配器使用真实数据库会话"""
        db = SessionLocal()
        tool = MockTool()
        adapter = ToolAdapter(tool, "tenant-456", db)

        # 验证适配器创建成功
        assert adapter.name == "mock_search_tool"
        assert adapter.tenant_id == "tenant-456"

        db.close()

    def test_metrics_recording_doesnt_crash(self):
        """测试指标记录不会崩溃"""
        from api.metrics import get_metrics_store

        db = SessionLocal()
        tool = MockTool()
        adapter = ToolAdapter(tool, "tenant-789", db)

        # 记录指标
        adapter._record_metrics(success=True, execution_time=1.0)

        # 验证指标存储存在
        metrics = get_metrics_store()
        assert metrics is not None

        db.close()
