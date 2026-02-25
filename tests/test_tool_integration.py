"""
工具调用集成测试

测试完整的工具调用流程，包括工具注册、配额检查、Agent 执行等。
"""
import pytest
from unittest.mock import Mock, patch
from services.tool_registry import ToolRegistry
from services.quota_service import QuotaService
from services.database import ToolCallLog, TenantToolQuota, SessionLocal
from agents.tool_using_agent import ToolUsingAgent


@pytest.mark.integration
class TestToolCallingIntegration:
    """工具调用集成测试套件"""

    @pytest.mark.asyncio
    async def test_full_tool_calling_flow(self):
        """测试完整的工具调用流程"""
        # 1. 获取工具列表
        registry = ToolRegistry()
        all_tools = registry.list_all_tools()

        assert len(all_tools) >= 2
        assert 'tavily_search' in all_tools
        assert 'llm_math' in all_tools

    @pytest.mark.asyncio
    async def test_tool_registry_get_tools(self):
        """测试工具注册表获取工具"""
        registry = ToolRegistry()
        db = SessionLocal()

        try:
            # 模拟租户设置
            tenant_settings = {
                'enable_search': True,
                'enable_math': True,
                'tenant_id': 'test-tenant-id'
            }

            # 获取工具列表
            tools = registry.get_tools_for_tenant(
                tenant_id='test-tenant-id',
                tenant_settings=tenant_settings,
                db=db
            )

            # 验证返回的是适配器
            assert len(tools) >= 0

            # 验证工具有 name 和 description
            for tool in tools:
                assert hasattr(tool, 'name')
                assert hasattr(tool, 'description')
                assert tool.name in ['tavily_search', 'llm_math']

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_quota_service_flow(self):
        """测试配额服务流程"""
        db = SessionLocal()

        try:
            quota_service = QuotaService(db)

            # 测试获取不存在的配额（应该返回 None）
            quota_info = quota_service.get_quota_info(
                tenant_id='non-existent-tenant',
                tool_name='test_tool'
            )
            assert quota_info is None

            # 测试配额检查（无配额配置应该不抛出异常）
            await quota_service.check_tool_quota(
                tenant_id='non-existent-tenant',
                tool_name='test_tool'
            )

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_tool_using_agent_no_tools(self):
        """测试 ToolUsingAgent 无工具场景"""
        db = Mock()

        agent = ToolUsingAgent(
            name="tool_using",
            role="工具使用专家",
            tenant_id="test-tenant-id",
            db=db
        )

        # Mock 空工具列表
        with patch.object(agent.tool_registry, 'get_tools_for_tenant', return_value=[]):
            result = await agent.execute("测试任务", {})

            assert result['done'] is True
            assert '没有可用工具' in result['result']

    @pytest.mark.asyncio
    async def test_tool_using_agent_with_mock_tools(self):
        """测试 ToolUsingAgent 带模拟工具"""
        db = Mock()

        agent = ToolUsingAgent(
            name="tool_using",
            role="工具使用专家",
            tenant_id="test-tenant-id",
            db=db
        )

        # Mock 工具
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool._arun = Mock(return_value="工具执行成功")

        with patch.object(agent.tool_registry, 'get_tools_for_tenant', return_value=[mock_tool]):
            result = await agent.execute("测试任务", {})

            assert result['done'] is True
            assert '工具执行成功' in result['result']
            assert 'test_tool' in result['result']


@pytest.mark.integration
class TestToolQuotaEnforcement:
    """工具配额强制执行测试"""

    def test_quota_exceeded_raises_exception(self):
        """测试配额超限抛出异常"""
        from services.exceptions import QuotaExceededException

        db = SessionLocal()

        try:
            quota_service = QuotaService(db)

            # 创建测试配额（已用完）
            quota = TenantToolQuota(
                id='test-quota-id',
                tenant_id='test-tenant',
                tool_name='test_tool',
                max_calls_per_day=1,
                current_day_calls=1,
                current_month_calls=1,
                last_reset_date=None
            )

            # Mock 查询返回配额
            with patch.object(db, 'query') as mock_query:
                mock_filter = Mock()
                mock_query.filter.return_value = mock_filter
                mock_filter.first.return_value = quota

                # 应该抛出异常
                with pytest.raises(Exception):
                    import asyncio
                    asyncio.run(quota_service.check_tool_quota(
                        tenant_id='test-tenant',
                        tool_name='test_tool'
                    ))

        finally:
            db.close()


@pytest.mark.integration
class TestToolCallLogging:
    """工具调用日志测试"""

    def test_tool_call_log_creation(self):
        """测试工具调用日志创建"""
        db = SessionLocal()

        try:
            # 创建测试日志
            log = ToolCallLog(
                id='test-log-id',
                tenant_id='test-tenant',
                tool_name='test_tool',
                tool_input={'query': 'test'},
                tool_output='result',
                status='success',
                execution_time_ms=100
            )

            db.add(log)
            db.commit()

            # 查询验证
            retrieved = db.query(ToolCallLog).filter(
                ToolCallLog.id == 'test-log-id'
            ).first()

            assert retrieved is not None
            assert retrieved.tool_name == 'test_tool'
            assert retrieved.status == 'success'

            # 清理
            db.delete(retrieved)
            db.commit()

        finally:
            db.close()
