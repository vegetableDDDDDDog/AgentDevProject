"""
多 Agent 协作 - 核心编排器

实现三种协作模式：顺序、并行、迭代。
"""

import asyncio
from typing import Dict, List, Any
from agents.registry import AgentRegistry
from agents.state_manager import SharedStateManager


class AgentOrchestrator:
    """
    多 Agent 编排器

    负责 Agent 的任务分发、流程控制和结果聚合。
    支持三种协作模式：顺序、并行、迭代。
    """

    def __init__(self, session_id: str = "default"):
        """
        初始化编排器

        Args:
            session_id: 会话唯一标识
        """
        self.registry = AgentRegistry()
        self.state_manager = SharedStateManager(session_id)
        self.max_iterations = 10

    def register_agent(self, agent) -> None:
        """
        注册 Agent

        Args:
            agent: Agent 实例
        """
        self.registry.register(agent)

    async def execute_sequential(
        self,
        agents: List[str],
        task: str,
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        顺序协作模式

        Agent 按顺序依次执行，每个 Agent 的输出会传递给下一个 Agent。

        Example:
            Researcher → Analyst → Writer

        Args:
            agents: Agent 名称列表
            task: 任务描述
            context: 初始上下文

        Returns:
            包含执行结果的字典
        """
        results = {}
        current_context = context or {}

        for agent_name in agents:
            agent = self.registry.get(agent_name)
            if not agent:
                print(f"❌ Agent 未找到: {agent_name}")
                continue

            print(f"\n{'='*50}")
            print(f"[{agent_name}] 开始执行...")
            print(f"{'='*50}")

            try:
                result = await agent.execute(task, current_context)
                results[agent_name] = result

                # 传递上下文
                if "context" in result:
                    current_context.update(result["context"])

                # 更新状态管理器
                for key, value in result.items():
                    if key != "context":
                        self.state_manager.update(agent_name, key, value)

            except Exception as e:
                print(f"❌ [{agent_name}] 执行失败: {e}")
                results[agent_name] = {"error": str(e)}

        return {
            "status": "completed",
            "results": results,
            "final_context": current_context
        }

    async def execute_parallel(
        self,
        agents: List[str],
        tasks: List[str],
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        并行协作模式

        多个 Agent 同时执行任务，最后聚合结果。

        Example:
            Writer1 + Writer2 + Writer3

        Args:
            agents: Agent 名称列表
            tasks: 对应的任务列表
            context: 初始上下文

        Returns:
            包含所有执行结果的字典
        """
        if len(agents) != len(tasks):
            raise ValueError("Agent 数量必须与任务数量相同")

        current_context = context or {}
        tasks_coroutines = []

        print(f"\n{'='*50}")
        print(f"🚀 启动 {len(agents)} 个 Agent 并行执行...")
        print(f"{'='*50}\n")

        for agent_name, task in zip(agents, tasks):
            agent = self.registry.get(agent_name)
            if not agent:
                print(f"❌ Agent 未找到: {agent_name}")
                continue

            print(f"[{agent_name}] 准备执行...")
            tasks_coroutines.append(
                agent.execute(task, current_context)
            )

        # 并行执行
        results = await asyncio.gather(*tasks_coroutines, return_exceptions=True)

        # 处理结果
        processed_results = {}
        for agent_name, result in zip(agents, results):
            if isinstance(result, Exception):
                print(f"❌ [{agent_name}] 执行失败: {result}")
                processed_results[agent_name] = {"error": str(result)}
            else:
                print(f"✅ [{agent_name}] 执行完成")
                processed_results[agent_name] = result

        return {
            "status": "completed",
            "results": processed_results
        }

    async def execute_iterative(
        self,
        agents: List[str],
        task: str,
        context: Dict = None,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        迭代协作模式

        Agent 循环执行直到任务完成或达到最大迭代次数。

        Example:
            Drafter → Reviewer → Drafter(改进) → Reviewer(确认)

        Args:
            agents: Agent 名称列表（按循环顺序）
            task: 任务描述
            context: 初始上下文
            max_iterations: 最大迭代次数

        Returns:
            包含执行结果的字典
        """
        current_context = context or {}
        iteration = 0

        while iteration < max_iterations:
            print(f"\n{'='*50}")
            print(f"📈 迭代 {iteration + 1}/{max_iterations}")
            print(f"{'='*50}")

            for agent_name in agents:
                agent = self.registry.get(agent_name)
                if not agent:
                    continue

                print(f"\n[{agent_name}] 执行中...")

                try:
                    result = await agent.execute(task, current_context)

                    # 检查是否完成
                    if result.get("done", False):
                        print(f"✅ [{agent_name}] 任务完成！")
                        return {
                            "status": "completed",
                            "iterations": iteration + 1,
                            "results": result
                        }

                    # 更新上下文
                    if "context" in result:
                        current_context.update(result["context"])

                    # 更新状态
                    for key, value in result.items():
                        if key != "context":
                            self.state_manager.update(agent_name, key, value)

                except Exception as e:
                    print(f"❌ [{agent_name}] 执行失败: {e}")

            iteration += 1

        return {
            "status": "max_iterations_reached",
            "iterations": iteration,
            "final_context": current_context
        }

    def get_status(self) -> Dict[str, Any]:
        """
        获取编排器状态

        Returns:
            包含注册信息和状态的字典
        """
        return {
            "session_id": self.state_manager.session_id,
            "registered_agents": self.registry.list_all(),
            "agent_count": self.registry.count(),
            "state_history": len(self.state_manager.get_history())
        }

    def __repr__(self) -> str:
        return f"AgentOrchestrator(session={self.state_manager.session_id}, agents={self.registry.count()})"
