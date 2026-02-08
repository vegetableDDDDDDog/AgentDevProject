"""
多 Agent 协作 - 单元测试

测试编排器的三种协作模式：顺序、并行、迭代。
"""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import AgentOrchestrator
from agents.base_agent import BaseAgent
from typing import Dict, Any, List


class MockAgent(BaseAgent):
    """测试用的 Mock Agent"""

    def __init__(self, name: str, delay: float = 0.1):
        super().__init__(name, f"测试Agent-{name}")
        self.delay = delay
        self.call_count = 0

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """模拟执行任务"""
        self.call_count += 1
        await asyncio.sleep(self.delay)  # 模拟异步操作

        return {
            "result": f"[{self.name}] 完成: {task}",
            "task": task,
            "call_count": self.call_count,
            "context": {
                **context,
                f"{self.name}_result": f"result_{self.call_count}"
            },
            "done": False
        }

    def get_capabilities(self) -> List[str]:
        return ["mock_capability"]


class SuccessAgent(BaseAgent):
    """模拟成功完成任务的 Agent"""

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result": "Success",
            "context": context,
            "done": True  # 标记为完成
        }

    def get_capabilities(self) -> List[str]:
        return ["success"]


class FailingAgent(BaseAgent):
    """模拟执行失败的 Agent"""

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        raise Exception("模拟的执行失败")

    def get_capabilities(self) -> List[str]:
        return ["failing"]


# ============ 测试用例 ============

@pytest.mark.asyncio
async def test_sequential_execution():
    """测试顺序执行"""
    orchestrator = AgentOrchestrator()

    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")
    agent3 = MockAgent("agent3")

    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)
    orchestrator.register_agent(agent3)

    result = await orchestrator.execute_sequential(
        agents=["agent1", "agent2", "agent3"],
        task="测试任务",
        context={"initial": "data"}
    )

    # 验证结果
    assert result["status"] == "completed"
    assert "agent1" in result["results"]
    assert "agent2" in result["results"]
    assert "agent3" in result["results"]
    assert "final_context" in result

    # 验证上下文传递
    assert "agent1_result" in result["final_context"]
    assert "agent2_result" in result["final_context"]
    assert "agent3_result" in result["final_context"]


@pytest.mark.asyncio
async def test_parallel_execution():
    """测试并行执行"""
    orchestrator = AgentOrchestrator()

    agents = [MockAgent(f"agent{i}", delay=0.1) for i in range(3)]
    for agent in agents:
        orchestrator.register_agent(agent)

    import time
    start_time = time.time()

    result = await orchestrator.execute_parallel(
        agents=["agent0", "agent1", "agent2"],
        tasks=["任务1", "任务2", "任务3"]
    )

    elapsed = time.time() - start_time

    # 验证结果
    assert result["status"] == "completed"
    assert len(result["results"]) == 3

    # 并行执行应该比顺序快
    # 3个任务各0.1秒，顺序需要0.3秒，并行应该接近0.1秒
    assert elapsed < 0.25  # 留一些余量


@pytest.mark.asyncio
async def test_iterative_execution():
    """测试迭代执行"""
    orchestrator = AgentOrchestrator()

    # 前两次失败，第三次成功
    agent1 = MockAgent("agent1")
    agent2 = SuccessAgent("agent2")  # 会立即返回 done=True

    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)

    result = await orchestrator.execute_iterative(
        agents=["agent1", "agent2"],
        task="测试任务",
        max_iterations=5
    )

    # 验证结果
    assert result["status"] == "completed"
    assert result["iterations"] == 1  # 第一次迭代就完成
    assert "results" in result


@pytest.mark.asyncio
async def test_iterative_max_reached():
    """测试达到最大迭代次数"""
    orchestrator = AgentOrchestrator()

    # 这些 Agent 永远不会完成（done=False）
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)

    result = await orchestrator.execute_iterative(
        agents=["agent1", "agent2"],
        task="测试任务",
        max_iterations=2
    )

    # 验证结果
    assert result["status"] == "max_iterations_reached"
    assert result["iterations"] == 2


@pytest.mark.asyncio
async def test_agent_registry():
    """测试 Agent 注册表"""
    orchestrator = AgentOrchestrator()

    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")

    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)

    # 验证注册
    assert orchestrator.registry.count() == 2
    assert orchestrator.registry.get("agent1") is agent1
    assert orchestrator.registry.get("agent2") is agent2

    # 验证列表
    agents_list = orchestrator.registry.list_all()
    assert "agent1" in agents_list
    assert "agent2" in agents_list


@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    orchestrator = AgentOrchestrator()

    failing_agent = FailingAgent("failing")
    success_agent = MockAgent("success")

    orchestrator.register_agent(failing_agent)
    orchestrator.register_agent(success_agent)

    # 顺序执行中某个 Agent 失败
    result = await orchestrator.execute_sequential(
        agents=["failing", "success"],
        task="测试任务"
    )

    # 验证错误被正确处理
    assert "failing" in result["results"]
    assert "error" in result["results"]["failing"]
    assert "success" in result["results"]


@pytest.mark.asyncio
async def test_state_manager():
    """测试状态管理器"""
    from agents.state_manager import SharedStateManager

    state_manager = SharedStateManager("test_session")

    # 测试更新和获取
    state_manager.update("agent1", "key1", "value1")
    state_manager.update("agent1", "key2", "value2")
    state_manager.update("agent2", "key1", "value3")

    # 验证状态
    assert state_manager.get("agent1", "key1") == "value1"
    assert state_manager.get("agent1", "key2") == "value2"
    assert state_manager.get("agent2", "key1") == "value3"

    # 验证历史记录
    history = state_manager.get_history()
    assert len(history) == 3


@pytest.mark.asyncio
async def test_orchestrator_status():
    """测试编排器状态查询"""
    orchestrator = AgentOrchestrator(session_id="test_session")

    agent1 = MockAgent("agent1")
    orchestrator.register_agent(agent1)

    status = orchestrator.get_status()

    assert status["session_id"] == "test_session"
    assert status["agent_count"] == 1
    assert "agent1" in status["registered_agents"]


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
