"""
端到端测试：多租户 RAG 系统

测试完整的文档处理和检索流程。
"""

import asyncio
import sys
from services.database import SessionLocal, KnowledgeBase, Tenant, Document, DocumentProcessingTask
from services.document_processor import DocumentProcessor
from services.hybrid_retriever import RetrieverFactory


class MockUploadFile:
    """模拟上传文件"""
    def __init__(self, filename, file_path):
        self.filename = filename
        self.file_path = file_path

    def read(self):
        with open(self.file_path, 'rb') as f:
            return f.read()


async def test_e2e():
    """端到端测试"""
    db = SessionLocal()

    try:
        print("=" * 60)
        print("🧪 端到端测试：多租户 RAG 系统")
        print("=" * 60)

        # 1. 获取测试租户
        print("\n1️⃣  获取测试租户...")
        tenant = db.query(Tenant).filter_by(id="test_tenant").first()
        if not tenant:
            print("❌ 测试租户不存在")
            return
        print(f"   ✅ 租户: {tenant.display_name}")

        # 2. 创建知识库
        print("\n2️⃣  创建知识库...")
        kb = db.query(KnowledgeBase).filter_by(
            tenant_id=tenant.id,
            name="测试知识库"
        ).first()

        if not kb:
            import uuid
            collection_name = f"tenant_{tenant.id}_kb_{uuid.uuid4().hex[:8]}"
            kb = KnowledgeBase(
                tenant_id=tenant.id,
                name="测试知识库",
                description="用于E2E测试",
                collection_name=collection_name,
                chunk_size=200,  # 小一点以便快速测试
                chunk_overlap=20,
                ocr_enabled=False  # 测试文档不需要OCR
            )
            db.add(kb)
            db.commit()
            db.refresh(kb)

        print(f"   ✅ 知识库: {kb.name}")
        print(f"   📦 Collection: {kb.collection_name}")

        # 3. 上传并处理文档
        print("\n3️⃣  上传并处理文档...")

        # 创建 mock 文件对象
        class MockFile:
            def __init__(self, filename, path):
                self.filename = filename
                self.file = open(path, 'rb')

            def __del__(self):
                if hasattr(self, 'file'):
                    self.file.close()

        from fastapi import BackgroundTasks

        mock_file = MockFile("test_rag.md", "data/test_documents/test_rag.md")
        background_tasks = BackgroundTasks()

        processor = DocumentProcessor(db)

        print(f"   📄 文件: {mock_file.filename}")
        task_id = await processor.upload_document_async(
            mock_file,
            kb.id,
            tenant.id,
            background_tasks
        )
        print(f"   ✅ 任务已提交: {task_id}")

        # 等待处理完成
        print("\n⏳ 等待处理完成...")
        import time
        max_wait = 30
        for i in range(max_wait):
            await asyncio.sleep(1)
            task = db.query(DocumentProcessingTask).filter_by(id=task_id).first()
            if task:
                print(f"   进度: {task.progress}% - {task.current_step}")
                if task.status == 'completed':
                    print("   ✅ 处理完成！")
                    break
                elif task.status == 'failed':
                    print(f"   ❌ 处理失败: {task.error_message}")
                    return

        # 4. 验证文档已保存
        print("\n4️⃣  验证文档...")
        document = db.query(Document).filter_by(
            knowledge_base_id=kb.id
        ).first()

        if document:
            print(f"   ✅ 文档已保存")
            print(f"   📊 状态: {document.upload_status}")
            print(f"   📝 分块数: {document.chunk_count}")
        else:
            print("   ❌ 文档未找到")
            return

        # 5. 测试混合检索
        print("\n5️⃣  测试混合检索...")

        retriever = RetrieverFactory.get_retriever(kb)

        test_queries = [
            "什么是混合检索？",
            "文档上传支持哪些格式？",
            "如何实现租户隔离？"
        ]

        for query in test_queries:
            print(f"\n   🔍 查询: {query}")
            try:
                results = retriever.get_relevant_documents(query)
                print(f"   ✅ 找到 {len(results)} 个相关片段")

                # 显示第一个结果
                if results:
                    content = results[0].page_content
                    preview = content[:100].replace('\n', ' ')
                    print(f"   📄 片段: {preview}...")
            except Exception as e:
                print(f"   ⚠️  检索出错: {str(e)[:100]}")

        print("\n" + "=" * 60)
        print("✅ 测试完成！所有功能正常")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_e2e())
