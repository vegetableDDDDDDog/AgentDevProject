"""
工具调用性能测试

测试工具调用的延迟、并发性能等。
"""
import pytest
import time
import asyncio
from unittest.mock import Mock, patch
from agents.tool_using_agent import ToolUsingAgent


@pytest.mark.performance
class TestToolPerformance:
    """工具调用性能测试套件"""

    @pytest.mark.asyncio
    async def test_tool_calling_latency(self):
        """测试工具调用延迟"""
        db = Mock()

        agent = ToolUsingAgent(
            name="tool_using",
            role="工具使用专家",
            tenant_id="test-tenant-id",
            db=db
        )

        # Mock 工具（快速响应）
        mock_tool = Mock()
        mock_tool.name = "fast_tool"
        mock_tool._arun = Mock(return_value="快速响应")

        with patch.object(agent.tool_registry, 'get_tools_for_tenant', return_value=[mock_tool]):
            start = time.time()
            await agent.execute("简单任务", {})
            latency = time.time() - start

            # 延迟应该 < 1 秒（模拟工具）
            assert latency < 1.0, f"工具调用延迟 {latency:.2f}s 超过预期"

    @pytest.mark.asyncio
    async def test_slow_tool_calling(self):
        """测试慢速工具调用"""
        db = Mock()

        agent = ToolUsingAgent(
            name="tool_using",
            role="工具使用专家",
            tenant_id="test-tenant-id",
            db=db
        )

        # Mock 慢速工具（模拟真实场景）
        async def slow_tool(*args, **kwargs):
            await asyncio.sleep(0.1)  # 模拟 100ms 延迟
            return "慢速响应"

        mock_tool = Mock()
        mock_tool.name = "slow_tool"
        mock_tool._arun = slow_tool

        with patch.object(agent.tool_registry, 'get_tools_for_tenant', return_value=[mock_tool]):
            start = time.time()
            await agent.execute("测试任务", {})
            latency = time.time() - start

            # 延迟应该 > 100ms 且 < 500ms
            assert latency >= 0.1, f"工具调用延迟 {latency:.2f}s 低于预期"
            assert latency < 0.5, f"工具调用延迟 {latency:.2f}s 超过预期"

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """测试并发工具调用"""
        db = Mock()

        agent = ToolUsingAgent(
            name="tool_using",
            role="工具使用专家",
            tenant_id="test-tenant-id",
            db=db
        )

        # Mock 工具
        async def mock_tool_async(*args, **kwargs):
            await asyncio.sleep(0.05)  # 模拟 50ms 延迟
            return f"结果: {args[0] if args else 'default'}"

        mock_tool = Mock()
        mock_tool.name = "concurrent_tool"
        mock_tool._arun = mock_tool_async

        with patch.object(agent.tool_registry, 'get_tools_for_tenant', return_value=[mock_tool]):
            # 并发执行 10 个任务
            tasks = [
                agent.execute(f"任务 {i}", {})
                for i in range(10)
            ]

            start = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start

            # 所有任务都应该完成
            assert len(results) == 10
            assert all(r['done'] for r in results)

            # 并发执行应该比顺序执行快
            # 顺序执行: 10 * 50ms = 500ms
            # 并发执行: ~50ms（取决于事件循环）
            print(f"\n并发执行 10 个任务耗时: {total_time:.3f}秒")
            print(f"平均每个任务: {total_time / 10:.3f}秒")

            # 允许一定的容错（并发不会完全线性）
            assert total_time < 1.0, f"并发执行时间 {total_time:.3f}s 过长"

    @pytest.mark.asyncio
    async def test_agent_creation_performance(self):
        """测试 Agent 创建性能"""
        db = Mock()

        start = time.time()
        for i in range(100):
            agent = ToolUsingAgent(
                name=f"agent_{i}",
                role="测试 Agent",
                tenant_id="test-tenant-id",
                db=db
            )
        creation_time = time.time() - start

        # 创建 100 个 Agent 应该很快
        print(f"\n创建 100 个 Agent 耗时: {creation_time:.3f}秒")
        print(f"平均每个 Agent: {creation_time / 100:.6f}秒")

        assert creation_time < 1.0, f"Agent 创建时间 {creation_time:.3f}s 过长"

    @pytest.mark.asyncio
    async def test_tool_registry_performance(self):
        """测试工具注册表性能"""
        from services.tool_registry import ToolRegistry

        db = Mock()
        registry = ToolRegistry()

        tenant_settings = {
            'enable_search': True,
            'enable_math': True,
            'tenant_id': 'test-tenant-id'
        }

        # 测试 100 次查询性能
        start = time.time()
        for i in range(100):
            tools = registry.get_tools_for_tenant(
                tenant_id=f'tenant-{i % 10}',  # 10 个不同租户
                tenant_settings=tenant_settings,
                db=db
            )
        query_time = time.time() - start

        print(f"\n查询工具列表 100 次耗时: {query_time:.3f}秒")
        print(f"平均每次查询: {query_time / 100:.6f}秒")

        # 每次查询应该很快
        assert query_time < 1.0, f"工具查询时间 {query_time:.3f}s 过长"


@pytest.mark.performance
class TestQuotaServicePerformance:
    """配额服务性能测试"""

    @pytest.mark.asyncio
    async def test_quota_check_performance(self):
        """测试配额检查性能"""
        from services.quota_service import QuotaService
        from unittest.mock import Mock

        db = Mock()
        quota_service = QuotaService(db)

        # Mock 查询返回 None（无配额限制）
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        db.query.return_value = mock_query

        start = time.time()
        for i in range(100):
            await quota_service.check_tool_quota(
                tenant_id=f'tenant-{i % 10}',
                tool_name='test_tool'
            )
        check_time = time.time() - start

        print(f"\n配额检查 100 次耗时: {check_time:.3f}秒")
        print(f"平均每次检查: {check_time / 100:.6f}秒")

        # 配额检查应该很快
        assert check_time < 0.5, f"配额检查时间 {check_time:.3f}s 过长"


@pytest.mark.performance
class TestMemoryUsage:
    """内存使用测试"""

    @pytest.mark.asyncio
    async def test_many_agents_memory(self):
        """测试创建多个 Agent 的内存使用"""
        import gc
        import sys

        db = Mock()

        # 获取初始内存
        gc.collect()
        initial_objects = len(gc.get_objects())

        # 创建大量 Agent
        agents = []
        for i in range(1000):
            agent = ToolUsingAgent(
                name=f"agent_{i}",
                role="测试 Agent",
                tenant_id="test-tenant-id",
                db=db
            )
            agents.append(agent)

        # 检查对象增长
        gc.collect()
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        print(f"\n创建 1000 个 Agent，对象增长: {object_growth}")

        # 清理
        del agents
        gc.collect()

        # 对象增长不应该过大（每个 Agent 大约增加几个对象）
        assert object_growth < 10000, f"对象增长 {object_growth} 过大，可能存在内存泄漏"
