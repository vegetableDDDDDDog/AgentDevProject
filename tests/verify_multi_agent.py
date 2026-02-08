"""
多 Agent 协作功能验证脚本

快速验证三种协作模式是否正常工作。
"""

import asyncio
import sys
sys.path.insert(0, '.')

from agents.orchestrator import AgentOrchestrator
from agents.base_agent import BaseAgent
from typing import Dict, Any, List


class SimpleAgent(BaseAgent):
    """简单的测试 Agent"""

    def __init__(self, name: str):
        super().__init__(name, f"测试Agent-{name}")

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.1)  # 模拟处理
        return {
            "result": f"[{self.name}] 完成了 '{task}'",
            "context": {**context, f"{self.name}_done": True},
            "done": False
        }

    def get_capabilities(self) -> List[str]:
        return ["测试"]


async def main():
    print("=" * 70)
    print("🔍 多 Agent 协作功能验证")
    print("=" * 70)

    orchestrator = AgentOrchestrator()

    # 创建测试 Agent
    agents = [SimpleAgent(f"agent{i}") for i in range(1, 4)]

    for agent in agents:
        orchestrator.register_agent(agent)

    print(f"\n{orchestrator.get_status()}\n")

    # 测试 1：顺序协作
    print("-" * 70)
    print("测试 1: 顺序协作")
    print("-" * 70)

    result1 = await orchestrator.execute_sequential(
        agents=["agent1", "agent2", "agent3"],
        task="顺序任务",
        context={"test": "data"}
    )

    assert result1["status"] == "completed", "❌ 顺序协作失败"
    assert len(result1["results"]) == 3, "❌ 结果数量不正确"
    print("✅ 顺序协作测试通过\n")

    # 测试 2：并行协作
    print("-" * 70)
    print("测试 2: 并行协作")
    print("-" * 70)

    result2 = await orchestrator.execute_parallel(
        agents=["agent1", "agent2", "agent3"],
        tasks=["任务1", "任务2", "任务3"]
    )

    assert result2["status"] == "completed", "❌ 并行协作失败"
    assert len(result2["results"]) == 3, "❌ 结果数量不正确"
    print("✅ 并行协作测试通过\n")

    # 测试 3：迭代协作
    print("-" * 70)
    print("测试 3: 迭代协作")
    print("-" * 70)

    result3 = await orchestrator.execute_iterative(
        agents=["agent1", "agent2"],
        task="迭代任务",
        max_iterations=2
    )

    assert result3["status"] == "max_iterations_reached", "❌ 迭代协作失败"
    assert result3["iterations"] == 2, "❌ 迭代次数不正确"
    print("✅ 迭代协作测试通过\n")

    # 测试 4：状态管理
    print("-" * 70)
    print("测试 4: 状态管理")
    print("-" * 70)

    from agents.state_manager import SharedStateManager

    state_mgr = SharedStateManager("test_session")
    state_mgr.update("agent1", "key1", "value1")
    state_mgr.update("agent2", "key2", "value2")

    assert state_mgr.get("agent1", "key1") == "value1", "❌ 状态存储失败"
    assert state_mgr.get("agent2", "key2") == "value2", "❌ 状态存储失败"
    assert len(state_mgr.get_history()) == 2, "❌ 历史记录失败"
    print("✅ 状态管理测试通过\n")

    # 测试 5：注册表
    print("-" * 70)
    print("测试 5: Agent 注册表")
    print("-" * 70)

    assert orchestrator.registry.count() == 3, "❌ 注册数量不正确"
    assert orchestrator.registry.get("agent1") is not None, "❌ Agent 获取失败"
    print("✅ 注册表测试通过\n")

    print("=" * 70)
    print("🎉 所有测试通过！多 Agent 协作功能正常！")
    print("=" * 70)

    print("\n📊 功能清单:")
    print("  ✅ 顺序协作模式")
    print("  ✅ 并行协作模式")
    print("  ✅ 迭代协作模式")
    print("  ✅ 状态管理")
    print("  ✅ Agent 注册表")
    print("  ✅ 编排器")

    print("\n🚀 下一步:")
    print("  1. 运行示例: python agents/examples/research_team.py")
    print("  2. 查看文档: docs/15-多Agent协作.md")
    print("  3. 创建你自己的协作 Agent！")


if __name__ == "__main__":
    asyncio.run(main())
