"""
Mock Embeddings 服务（用于测试）

不调用真实的 API，返回随机向量。
"""

from typing import List
from langchain_core.embeddings import Embeddings
import numpy as np


class MockEmbeddings(Embeddings):
    """Mock embeddings 用于测试"""

    def __init__(self, size: int = 1536):
        """初始化
        Args:
            size: 向量维度（默认1536，兼容 OpenAI）
        """
        self.size = size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入多个文档"""
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        # 使用文本哈希生成一致的"随机"向量
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        np.random.seed(hash_val)
        vector = np.random.rand(self.size).tolist()
        return vector

    @property
    def langchain_embeddings(self):
        """返回自身（用于 ChromaDB 兼容）"""
        return self


def get_mock_embeddings():
    """获取 Mock embeddings 单例"""
    return MockEmbeddings()
