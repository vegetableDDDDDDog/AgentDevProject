"""
文本嵌入服务。

支持多种嵌入模型提供商（OpenAI, 本地模型等）。
"""

import logging
from typing import List
from langchain_openai import OpenAIEmbeddings
from api.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """
    文本嵌入服务包装类。

    提供 LangChain 兼容的嵌入接口，用于向量化和检索。
    """

    def __init__(self):
        """初始化嵌入服务"""
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY 未配置，使用默认配置")
            self.embeddings = OpenAIEmbeddings(
                model=settings.embedding_model,
                openai_api_key="sk-placeholder"  # 会被实际调用时替换
            )
        else:
            self.embeddings = OpenAIEmbeddings(
                model=settings.embedding_model,
                openai_api_key=settings.openai_api_key,
                openai_api_base=settings.openai_api_base
            )
        logger.info(f"EmbeddingsService 初始化完成 (模型: {settings.embedding_model})")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        嵌入多个文档。

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        return self.embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """
        嵌入查询文本。

        Args:
            text: 查询文本

        Returns:
            嵌入向量
        """
        return self.embeddings.embed_query(text)

    def __call__(self, text: str) -> List[float]:
        """
        让对象可像函数一样调用。

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        return self.embed_query(text)

    @property
    def langchain_embeddings(self):
        """返回 LangChain embeddings 对象（用于 ChromaDB 等）"""
        return self.embeddings


# 单例模式
_embeddings_service = None


def get_embeddings_service() -> EmbeddingsService:
    """
    获取 EmbeddingsService 单例。

    Returns:
        EmbeddingsService 实例
    """
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service
