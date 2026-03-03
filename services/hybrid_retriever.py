"""
混合检索服务（向量相似度 + BM25 关键词）。

手动实现 RRF (Reciprocal Rank Fusion) 融合算法。
"""

import logging
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from typing import List

from services.database import KnowledgeBase
from services.embeddings_service import get_embeddings_service

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    混合检索器（向量 + BM25）。

    手动实现 RRF (Reciprocal Rank Fusion) 融合算法:
    score = sum(weight / (k + rank)) for each retriever

    特性:
    - 租户隔离：每个知识库独立的检索器实例
    - 可配置权重：vector 70% + bm25 30%
    """

    def __init__(self, knowledge_base: KnowledgeBase):
        """
        初始化混合检索器。

        Args:
            knowledge_base: KnowledgeBase ORM 对象
        """
        self.kb = knowledge_base
        self.embeddings = get_embeddings_service()

        # 加载向量检索器
        logger.info(f"加载 ChromaDB collection: {knowledge_base.collection_name}")
        self.vector_store = Chroma(
            collection_name=knowledge_base.collection_name,
            embedding_function=self.embeddings.langchain_embeddings,
            persist_directory=f"data/chroma/{knowledge_base.tenant_id}"
        )
        self.vector_retriever = self.vector_store.as_retriever(
            search_kwargs={"k": knowledge_base.top_k}
        )

        # 加载 BM25 检索器
        self.bm25_retriever = self._load_bm25_retriever()

        # 混合权重
        weights = knowledge_base.hybrid_search_weights or {"vector": 0.7, "bm25": 0.3}
        self.vector_weight = weights.get("vector", 0.7)
        self.bm25_weight = weights.get("bm25", 0.3)

        logger.info(
            f"混合检索器初始化完成 (Vector: {self.vector_weight}, "
            f"BM25: {self.bm25_weight}, Top-K: {knowledge_base.top_k})"
        )

    def _load_bm25_retriever(self) -> BM25Retriever:
        """
        从 ChromaDB 加载 BM25 检索器。

        实现租户隔离：每个知识库构建独立的 BM25 索引。

        Returns:
            BM25Retriever 实例
        """
        try:
            # 从 ChromaDB 加载所有文档
            all_docs = self.vector_store.get()

            documents = [
                Document(page_content=doc['page_content'], metadata=doc['metadata'])
                for doc in all_docs['documents']
            ]

            if not documents:
                logger.warning(f"知识库 {self.kb.name} 没有文档,BM25 检索器为空")
                # 返回空检索器
                return BM25Retriever.from_documents([Document(page_content="")])

            bm25_retriever = BM25Retriever.from_documents(
                documents,
                k=self.kb.top_k
            )
            logger.info(
                f"BM25 检索器加载完成 (租户: {self.kb.tenant_id}, "
                f"文档数: {len(documents)}, Top-K: {self.kb.top_k})"
            )
            return bm25_retriever

        except Exception as e:
            logger.error(f"BM25 检索器加载失败: {e}")
            # 返回空检索器
            return BM25Retriever.from_documents([Document(page_content="")])

    def _get_relevant_documents(self, query: str, run_manager=None) -> List[Document]:
        """
        使用 RRF 算法融合向量和 BM25 结果。

        RRF 公式: score = Σ(weight / (k + rank))
        其中 k=60 (常数), rank 是文档在检索结果中的排名

        Args:
            query: 查询文本
            run_manager: 运行管理器（可选）

        Returns:
            融合后的文档列表
        """
        logger.debug(f"混合检索查询: {query}")

        # 获取向量检索结果
        vector_docs = self.vector_retriever.get_relevant_documents(query)
        logger.debug(f"向量检索返回 {len(vector_docs)} 个文档")

        # 获取 BM25 检索结果
        bm25_docs = self.bm25_retriever.get_relevant_documents(query)
        logger.debug(f"BM25 检索返回 {len(bm25_docs)} 个文档")

        # RRF 融合
        k = 60  # RRF 常数
        scores = {}

        # 计算向量检索得分
        for rank, doc in enumerate(vector_docs, 1):
            doc_id = id(doc)
            scores[doc_id] = scores.get(doc_id, 0) + self.vector_weight / (k + rank)

        # 计算 BM25 检索得分
        for rank, doc in enumerate(bm25_docs, 1):
            doc_id = id(doc)
            scores[doc_id] = scores.get(doc_id, 0) + self.bm25_weight / (k + rank)

        # 按得分排序
        ranked_docs = sorted(
            [(doc_id, score) for doc_id, score in scores.items()],
            key=lambda x: x[1],
            reverse=True
        )

        # 去重并返回
        seen = set()
        final_docs = []
        for doc in vector_docs + bm25_docs:
            doc_id = id(doc)
            if doc_id in scores and doc_id not in seen:
                final_docs.append(doc)
                seen.add(doc_id)
                if len(final_docs) >= self.kb.top_k:
                    break

        logger.info(f"检索到 {len(final_docs)} 个文档片段 (RRF 融合)")
        return final_docs

    def add_documents(self, documents: List[Document]):
        """
        添加新文档到向量库。

        Args:
            documents: 文档列表
        """
        # 添加到向量库
        self.vector_store.add_documents(documents)

        # 重新加载 BM25 检索器
        self.bm25_retriever = self._load_bm25_retriever()

        logger.info(f"已添加 {len(documents)} 个文档到混合检索器")


class RetrieverFactory:
    """
    检索器工厂。

    管理混合检索器的创建和缓存，确保租户隔离。
    """

    _retrievers: dict = {}  # {kb_id: HybridRetriever}

    @classmethod
    def get_retriever(cls, knowledge_base: KnowledgeBase) -> HybridRetriever:
        """
        获取或创建混合检索器。

        Args:
            knowledge_base: KnowledgeBase ORM 对象

        Returns:
            HybridRetriever 实例
        """
        kb_id = knowledge_base.id

        # 如果已缓存，直接返回
        if kb_id in cls._retrievers:
            return cls._retrievers[kb_id]

        # 创建新的检索器
        retriever = HybridRetriever(knowledge_base)
        cls._retrievers[kb_id] = retriever

        return retriever

    @classmethod
    def invalidate(cls, kb_id: str):
        """
        使缓存失效（用于文档更新后）。

        Args:
            kb_id: 知识库 ID
        """
        if kb_id in cls._retrievers:
            del cls._retrievers[kb_id]
            logger.info(f"知识库 {kb_id} 检索器缓存已清除")

    @classmethod
    def clear_all(cls):
        """清除所有缓存"""
        cls._retrievers.clear()
        logger.info("所有检索器缓存已清除")
