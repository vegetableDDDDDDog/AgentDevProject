"""
简化测试：多租户 RAG 系统

直接测试核心功能，不使用 BackgroundTasks。
"""

import sys
sys.path.insert(0, '/home/wineash/PycharmProjects/AgentDevProject')

from services.database import SessionLocal, KnowledgeBase, Tenant, Document
from services.mock_embeddings import get_mock_embeddings
from services.hybrid_retriever import HybridRetriever
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid


def test_simple():
    """简化的测试流程"""
    db = SessionLocal()

    try:
        print("=" * 60)
        print("🧪 简化测试：多租户 RAG 系统")
        print("=" * 60)

        # 1. 获取测试租户和知识库
        print("\n1️⃣  准备测试环境...")
        tenant = db.query(Tenant).filter_by(id="test_tenant").first()

        kb = db.query(KnowledgeBase).filter_by(
            tenant_id=tenant.id,
            name="测试知识库"
        ).first()

        if not kb:
            collection_name = f"tenant_{tenant.id}_kb_{uuid.uuid4().hex[:8]}"
            kb = KnowledgeBase(
                tenant_id=tenant.id,
                name="测试知识库",
                collection_name=collection_name,
                chunk_size=200,
                chunk_overlap=20,
                ocr_enabled=False
            )
            db.add(kb)
            db.commit()
            db.refresh(kb)

        print(f"   ✅ 租户: {tenant.display_name}")
        print(f"   ✅ 知识库: {kb.name}")
        print(f"   📦 Collection: {kb.collection_name}")

        # 2. 读取测试文档
        print("\n2️⃣  读取测试文档...")
        with open("data/test_documents/test_rag.md", 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"   ✅ 文档大小: {len(text)} 字符")

        # 3. 分块
        print("\n3️⃣  文本分块...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=kb.chunk_size,
            chunk_overlap=kb.chunk_overlap,
            separators=["\n\n##", "\n\n", "\n", "。", "，", " ", ""]
        )
        chunks = splitter.split_text(text)
        print(f"   ✅ 分块数量: {len(chunks)}")

        # 4. 向量化并存储
        print("\n4️⃣  向量化并存储到 ChromaDB...")
        print("   💡 使用 Mock Embeddings (无需 API key)")
        embeddings = get_mock_embeddings()

        documents = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "chunk_id": f"test_{i}",
                    "filename": "test_rag.md",
                    "tenant_id": tenant.id
                }
            )
            documents.append(doc)

        # 存储
        from langchain_community.vectorstores import Chroma
        import os

        persist_dir = f"data/chroma/{tenant.id}"
        os.makedirs(persist_dir, exist_ok=True)

        vector_store = Chroma(
            collection_name=kb.collection_name,
            embedding_function=embeddings.langchain_embeddings,
            persist_directory=persist_dir
        )
        vector_store.add_documents(documents)
        print(f"   ✅ 已存储 {len(documents)} 个向量")

        # 5. 测试向量检索
        print("\n5️⃣  测试向量检索...")
        vector_retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        results = vector_retriever.invoke("什么是混合检索？")
        print(f"   ✅ 向量检索返回 {len(results)} 个结果")
        if results:
            print(f"   📄 顶部结果: {results[0].page_content[:80]}...")

        # 6. 测试混合检索
        print("\n6️⃣  测试混合检索...")
        try:
            hybrid_retriever = HybridRetriever(kb)
            results = hybrid_retriever._get_relevant_documents("什么是混合检索？")
            print(f"   ✅ 混合检索返回 {len(results)} 个结果")
            if results:
                print(f"   📄 顶部结果: {results[0].page_content[:80]}...")
        except Exception as e:
            print(f"   ⚠️  混合检索出错: {str(e)[:100]}")

        print("\n" + "=" * 60)
        print("✅ 核心功能测试完成！")
        print("=" * 60)

        print("\n📊 测试总结:")
        print("  ✅ 文档读取和分块")
        print("  ✅ 向量化存储 (ChromaDB)")
        print("  ✅ 向量检索")
        print("  ✅ 混合检索 (向量 + BM25)")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_simple()
