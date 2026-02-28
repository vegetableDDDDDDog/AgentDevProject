"""
真实 LLM Agents - 集成大语言模型

提供基于真实 LLM 的 Agent 实现，支持智谱 AI 等。
"""

from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage

from agents.base_agent import BaseAgent
from services.agent_factory import register_agent
from services.llm_service import LLMService, create_messages_from_history
from services.token_service import record_llm_usage


# ============================================================================
# 真实 LLM 聊天 Agent
# ============================================================================

@register_agent("llm_chat")
class LLMChatAgent(BaseAgent):
    """
    真实 LLM 聊天 Agent

    使用大语言模型进行对话的 Agent。
    支持流式输出和多轮对话。

    配置:
        tenant_context: 租户上下文（必需）
        system_prompt: 系统提示（可选）
        temperature: 温度参数（可选）
        max_tokens: 最大 Token 数（可选）

    示例:
        agent = LLMChatAgent({
            "tenant_context": tenant_context,
            "system_prompt": "你是一个助手"
        })

        result = await agent.execute("你好", {})
        print(result["response"])
    """

    def __init__(self, config: dict = None):
        super().__init__(
            name="llm_chat",
            role="LLM Chat Agent"
        )
        self.config = config or {}

        # 获取租户上下文（必需）
        self.tenant_context = self.config.get("tenant_context")
        if not self.tenant_context:
            raise ValueError("LLMChatAgent 需要租户上下文 (tenant_context)")

        # 创建 LLM 服务（从 config 中移除 tenant_context 避免重复传递）
        llm_config = {k: v for k, v in self.config.items() if k != "tenant_context"}
        self.llm_service = LLMService.from_tenant_context(
            self.tenant_context,
            **llm_config
        )

        # 获取配置
        self.system_prompt = self.config.get("system_prompt")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_tokens = self.config.get("max_tokens", 2000)

    async def execute(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行 LLM 聊天

        Args:
            task: 用户消息
            context: 上下文信息，可能包含：
                - history: 对话历史（可选）
                - session_id: 会话 ID（用于记录 Token）
                - tenant_id: 租户 ID（用于记录 Token）

        Returns:
            {
                "response": "AI 响应",
                "context": {...},
                "done": True,
                "tokens_used": 100
            }
        """
        # 获取对话历史
        history = context.get("history", [])

        # 创建消息列表
        messages = create_messages_from_history(
            user_message=task,
            history=history,
            system_prompt=self.system_prompt
        )

        # 调用 LLM
        response_message = await self.llm_service.achat(messages)

        # 提取响应文本
        response_text = response_message.content

        # 记录 Token 使用量
        session_id = context.get("session_id")
        tenant_id = context.get("tenant_id", self.tenant_context.tenant_id)

        if session_id and tenant_id:
            record_llm_usage(
                session_id=session_id,
                tenant_id=tenant_id,
                response_message=response_message
            )

        # 获取 Token 使用量（用于返回）
        tokens_used = 0
        if hasattr(response_message, 'response_metadata'):
            token_usage = response_message.response_metadata.get('token_usage', {})
            tokens_used = token_usage.get('total_tokens', 0)

        return {
            "response": response_text,
            "context": {
                **context,
                "last_response": response_text
            },
            "done": True,
            "tokens_used": tokens_used
        }

    async def stream_execute(
        self,
        task: str,
        context: Dict[str, Any]
    ):
        """
        流式执行 LLM 聊天

        生成器函数，逐步生成响应。

        Args:
            task: 用户消息
            context: 上下文信息

        Yields:
            {
                "type": "content",
                "content": "文本片段"
            }
            或
            {
                "type": "done",
                "tokens_used": 100
            }
        """
        # 获取对话历史
        history = context.get("history", [])

        # 创建消息列表
        messages = create_messages_from_history(
            user_message=task,
            history=history,
            system_prompt=self.system_prompt
        )

        # 流式调用 LLM
        full_response = ""
        async for chunk in self.llm_service.stream_chat(messages):
            full_response += chunk
            yield {
                "type": "content",
                "content": chunk
            }

        # 记录 Token 使用量（估算）
        session_id = context.get("session_id")
        tenant_id = context.get("tenant_id", self.tenant_context.tenant_id)

        if session_id and tenant_id:
            # 简单估算：大约 1 token ≈ 1.5 个中文字符或 0.75 个英文单词
            estimated_tokens = int(len(full_response) * 0.7)

            from services.token_service import TokenService
            token_service = TokenService()
            token_service.record_token_usage(
                session_id=session_id,
                tenant_id=tenant_id,
                prompt_tokens=int(len(task) * 0.7),
                completion_tokens=estimated_tokens
            )

        yield {
            "type": "done",
            "content": full_response
        }

    def get_capabilities(self) -> List[str]:
        """返回 Agent 能力列表"""
        return [
            "chat",
            "conversation",
            "llm",
            "streaming",
            "multi-turn"
        ]


# ============================================================================
# 单轮 LLM Agent（无历史记录）
# ============================================================================

@register_agent("llm_single_turn")
class LLMSingleTurnAgent(BaseAgent):
    """
    单轮 LLM Agent

    不使用对话历史，每次调用都是独立的。
    适用于一次性任务处理。
    """

    def __init__(self, config: dict = None):
        super().__init__(
            name="llm_single_turn",
            role="Single-turn LLM Agent"
        )
        self.config = config or {}

        # 获取租户上下文
        self.tenant_context = self.config.get("tenant_context")
        if not self.tenant_context:
            raise ValueError("LLMSingleTurnAgent 需要租户上下文 (tenant_context)")

        # 创建 LLM 服务（从 config 中移除 tenant_context 避免重复传递）
        llm_config = {k: v for k, v in self.config.items() if k != "tenant_context"}
        self.llm_service = LLMService.from_tenant_context(
            self.tenant_context,
            **llm_config
        )

        # 获取配置
        self.system_prompt = self.config.get("system_prompt")

    async def execute(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单轮 LLM 调用

        不使用对话历史，每次都是独立的调用。
        """
        # 创建消息（不包含历史）
        messages = create_messages_from_history(
            user_message=task,
            history=None,
            system_prompt=self.system_prompt
        )

        # 调用 LLM
        response_message = await self.llm_service.achat(messages)
        response_text = response_message.content

        # 记录 Token 使用量
        session_id = context.get("session_id")
        tenant_id = context.get("tenant_id", self.tenant_context.tenant_id)

        if session_id and tenant_id:
            record_llm_usage(
                session_id=session_id,
                tenant_id=tenant_id,
                response_message=response_message
            )

        # 获取 Token 使用量
        tokens_used = 0
        if hasattr(response_message, 'response_metadata'):
            token_usage = response_message.response_metadata.get('token_usage', {})
            tokens_used = token_usage.get('total_tokens', 0)

        return {
            "response": response_text,
            "context": context,
            "done": True,
            "tokens_used": tokens_used
        }

    def get_capabilities(self) -> List[str]:
        """返回 Agent 能力列表"""
        return ["llm", "single-turn", "task-processing"]
