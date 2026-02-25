"""
LLM 服务 - 大语言模型集成

提供统一的 LLM 调用接口，支持多个 LLM 提供商。
当前支持：智谱 AI (GLM-4)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.callbacks import CallbackManagerForLLMRun


# ============================================================================
# LLM 提供商抽象
# ============================================================================

class LLMProvider(ABC):
    """
    LLM 提供商抽象基类

    定义所有 LLM 提供商必须实现的接口。
    """

    @abstractmethod
    def chat(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AIMessage:
        """
        同步聊天

        Args:
            messages: 消息列表
            **kwargs: 额外参数（temperature, max_tokens 等）

        Returns:
            AIMessage: AI 响应消息
        """
        pass

    @abstractmethod
    async def achat(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AIMessage:
        """
        异步聊天

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            AIMessage: AI 响应消息
        """
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天（异步生成器）

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            str: 流式输出的文本片段
        """
        pass


# ============================================================================
# OpenAI 兼容提供商（支持智谱 AI 等）
# ============================================================================

class OpenAICompatibleProvider(LLMProvider):
    """
    OpenAI 兼容的 LLM 提供商

    支持所有兼容 OpenAI API 的提供商：
    - 智谱 AI (https://open.bigmodel.cn/api/paas/v4/)
    - OpenAI (https://api.openai.com/v1/)
    - 百度文心、阿里通义千问等

    使用 LangChain 的 ChatOpenAI 作为底层实现。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ):
        """
        初始化 OpenAI 兼容提供商

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            temperature: 温度参数（0-1，越高越随机）
            max_tokens: 最大生成 Token 数
            **kwargs: 其他 LangChain 参数
        """
        self.client = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        self.model = model

    def chat(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AIMessage:
        """
        同步聊天

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            AIMessage: AI 响应消息
        """
        response = self.client.invoke(messages, **kwargs)
        return response

    async def achat(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AIMessage:
        """
        异步聊天

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            AIMessage: AI 响应消息
        """
        response = await self.client.ainvoke(messages, **kwargs)
        return response

    async def stream_chat(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            str: 流式输出的文本片段
        """
        async for chunk in self.client.astream(messages, **kwargs):
            if chunk.content:
                yield chunk.content


# ============================================================================
# LLM 服务工厂
# ============================================================================

class LLMService:
    """
    LLM 服务工厂

    根据租户配置创建对应的 LLM 提供商实例。
    支持动态配置，不同租户可以使用不同的 LLM 提供商和模型。

    示例:
        # 从租户配置创建 LLM 服务
        llm_service = LLMService.from_tenant_context(tenant_context)

        # 聊天
        messages = [HumanMessage(content="你好")]
        response = await llm_service.achat(messages)

        # 流式聊天
        async for chunk in llm_service.stream_chat(messages):
            print(chunk, end="")
    """

    # 提供商注册表
    PROVIDERS = {
        "openai-compatible": OpenAICompatibleProvider,
    }

    def __init__(self, provider: LLMProvider):
        """
        初始化 LLM 服务

        Args:
            provider: LLM 提供商实例
        """
        self.provider = provider

    @classmethod
    def from_tenant_context(cls, tenant_context, **kwargs):
        """
        从租户上下文创建 LLM 服务

        从租户配置中读取 LLM 提供商、API Key、模型等配置，
        自动创建对应的 Provider 实例。

        Args:
            tenant_context: 租户上下文对象
            **kwargs: 覆盖配置（可选）

        Returns:
            LLMService: LLM 服务实例

        Raises:
            ValueError: 配置缺失或不支持

        示例:
            # 租户配置示例：
            # {
            #     "llm_provider": "openai-compatible",
            #     "llm_api_key": "your-api-key",
            #     "llm_base_url": "https://open.bigmodel.cn/api/paas/v4/",
            #     "llm_model": "glm-4",
            #     "llm_temperature": 0.7,
            #     "llm_max_tokens": 2000
            # }
        """
        # 获取配置（优先使用 kwargs 覆盖）
        provider_type = kwargs.get(
            "llm_provider",
            tenant_context.get_setting("llm_provider", "openai-compatible")
        )

        api_key = kwargs.get(
            "llm_api_key",
            tenant_context.get_setting("llm_api_key")
        )

        base_url = kwargs.get(
            "llm_base_url",
            tenant_context.get_setting("llm_base_url")
        )

        model = kwargs.get(
            "llm_model",
            tenant_context.get_setting("llm_model", "gpt-3.5-turbo")
        )

        temperature = kwargs.get(
            "llm_temperature",
            tenant_context.get_setting("llm_temperature", 0.7)
        )

        max_tokens = kwargs.get(
            "llm_max_tokens",
            tenant_context.get_setting("llm_max_tokens", 2000)
        )

        # 验证必需配置
        if not api_key:
            raise ValueError(
                "租户未配置 LLM API Key，请在租户设置中配置 llm_api_key"
            )

        if not base_url:
            raise ValueError(
                "租户未配置 LLM Base URL，请在租户设置中配置 llm_base_url"
            )

        # 检查提供商是否支持
        provider_class = cls.PROVIDERS.get(provider_type)
        if not provider_class:
            raise ValueError(
                f"不支持的 LLM 提供商: {provider_type}，"
                f"支持的提供商: {list(cls.PROVIDERS.keys())}"
            )

        # 创建提供商实例
        provider = provider_class(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return cls(provider)

    # ========================================================================
    # 便捷方法
    # ========================================================================

    async def achat(self, messages: List[BaseMessage], **kwargs) -> AIMessage:
        """
        异步聊天

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            AIMessage: AI 响应消息
        """
        return await self.provider.achat(messages, **kwargs)

    async def stream_chat(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            str: 流式输出的文本片段
        """
        async for chunk in self.provider.stream_chat(messages, **kwargs):
            yield chunk


# ============================================================================
# 工具函数
# ============================================================================

def create_messages_from_history(
    user_message: str,
    history: List[Dict[str, str]] = None,
    system_prompt: str = None
) -> List[BaseMessage]:
    """
    从对话历史创建消息列表

    Args:
        user_message: 当前用户消息
        history: 对话历史（可选），格式：[{"role": "user", "content": "..."}, ...]
        system_prompt: 系统提示（可选）

    Returns:
        消息列表

    示例:
        messages = create_messages_from_history(
            "你好",
            history=[{"role": "user", "content": "我是小明"}],
            system_prompt="你是一个助手"
        )
    """
    messages = []

    # 添加系统提示
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))

    # 添加历史消息
    if history:
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant" or role == "ai":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))

    # 添加当前用户消息
    messages.append(HumanMessage(content=user_message))

    return messages
