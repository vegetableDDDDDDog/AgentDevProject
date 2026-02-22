"""
用于测试和快速开始的简单 Agents

这些 agents 演示了 agent 工厂注册模式，可以用于测试而无需消耗 LLM tokens。
"""

import asyncio
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from services.agent_factory import register_agent


@register_agent("echo_agent")
class EchoAgent(BaseAgent):
    """
    一个简单的 echo agent，原样返回任务文本。

    用于测试 agent 工厂而无需消耗 API tokens。
    """

    def __init__(self, config: dict = None):
        super().__init__(name="echo_agent", role="Echo Agent")
        self.config = config or {}

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """原样返回任务文本。"""
        # 模拟一些处理时间
        await asyncio.sleep(0.1)

        return {
            "response": f"Echo: {task}",
            "context": context,
            "done": True
        }

    def get_capabilities(self) -> List[str]:
        return ["echo", "test", "debug"]


@register_agent("mock_chat_agent")
class MockChatAgent(BaseAgent):
    """
    一个模拟聊天 agent，返回预定义的响应。

    用于测试聊天界面而无需调用真实的 LLM API。
    """

    def __init__(self, config: dict = None):
        super().__init__(name="mock_chat_agent", role="Mock Chat Agent")
        self.config = config or {}
        self.response_count = 0

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """基于任务返回模拟响应。"""
        await asyncio.sleep(0.2)

        self.response_count += 1

        # 生成模拟响应
        responses = [
            f"我理解你说的是: {task}",
            f"有趣！多告诉我一些关于: {task}",
            f"这是我对'{task}'的看法: 这是一个模拟响应。",
            f"处理完成: {task}"
        ]

        response = responses[self.response_count % len(responses)]

        return {
            "response": response,
            "context": {**context, "last_task": task},
            "done": True,
            "tokens_used": 10  # 模拟 token 计数
        }

    def get_capabilities(self) -> List[str]:
        return ["chat", "conversation", "mock"]


@register_agent("counter_agent")
class CounterAgent(BaseAgent):
    """
    一个简单的 agent，计算它被执行了多少次。

    用于测试状态管理和会话持久性。
    """

    def __init__(self, config: dict = None):
        super().__init__(name="counter_agent", role="Counter Agent")
        self.config = config or {}
        self.execution_count = 0

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """增加计数器并返回当前计数。"""
        await asyncio.sleep(0.1)

        self.execution_count += 1

        return {
            "response": f"此 agent 已被执行 {self.execution_count} 次",
            "context": {
                **context,
                "execution_count": self.execution_count
            },
            "done": True
        }

    def get_capabilities(self) -> List[str]:
        return ["count", "state", "test"]

    def reset_count(self) -> None:
        """重置执行计数器。"""
        self.execution_count = 0


@register_agent("error_agent")
class ErrorAgent(BaseAgent):
    """
    一个模拟错误的 agent，用于测试错误处理。

    可以配置为引发不同类型的错误。
    """

    def __init__(self, config: dict = None):
        super().__init__(name="error_agent", role="错误模拟 Agent")
        self.config = config or {}
        self.error_type = self.config.get("error_type", "none")

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """基于配置模拟错误。"""
        await asyncio.sleep(0.1)

        error_map = {
            "value": ValueError("模拟的 ValueError"),
            "runtime": RuntimeError("模拟的 RuntimeError"),
            "timeout": asyncio.TimeoutError("模拟的超时"),
        }

        if self.error_type in error_map:
            raise error_map[self.error_type]

        return {
            "response": f"无错误 (error_type={self.error_type})",
            "context": context,
            "done": True
        }

    def get_capabilities(self) -> List[str]:
        return ["error_simulation", "test", "debug"]
