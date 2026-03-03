"""
测试知识库相关数据库模型。

测试新的知识库功能，包括：
- KnowledgeBase 模型（知识库）
- Document 模型（文档）
- DocumentProcessingTask 模型（文档处理任务）
- 数据完整性、关系和级联删除
"""

import pytest
import uuid
from datetime import datetime, timezone

from services.database import SessionLocal, Base, engine, Tenant, KnowledgeBase, Document, DocumentProcessingTask


@pytest.fixture(scope="function")
def db_session():
    """
    为每个测试创建新的数据库会话。
    """
    # 创建所有表
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        # 测试后删除所有表
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_tenant(db_session):
    """
    创建测试租户。
    """
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="test-tenant",
        display_name="Test Tenant",
        plan="pro",
        status="active"
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


class TestKnowledgeBaseModel:
    """测试知识库模型。"""

    def test_create_knowledge_base(self, db_session, test_tenant):
        """测试创建知识库。"""
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Test Knowledge Base",
            description="A test knowledge base",
            collection_name="test_collection_unique",
            chunk_size=500,
            chunk_overlap=50,
            hybrid_search_weights={"semantic": 0.7, "keyword": 0.3},
            top_k=3,
            ocr_enabled=True,
            ocr_threshold=10,
            status="active",
            document_count=0,
            total_chunks=0
        )
        db_session.add(kb)
        db_session.commit()

        retrieved = db_session.query(KnowledgeBase).filter(
            KnowledgeBase.collection_name == "test_collection_unique"
        ).first()

        assert retrieved is not None
        assert retrieved.name == "Test Knowledge Base"
        assert retrieved.description == "A test knowledge base"
        assert retrieved.collection_name == "test_collection_unique"
        assert retrieved.chunk_size == 500
        assert retrieved.chunk_overlap == 50
        assert retrieved.hybrid_search_weights == {"semantic": 0.7, "keyword": 0.3}
        assert retrieved.top_k == 3
        assert retrieved.ocr_enabled is True
        assert retrieved.ocr_threshold == 10
        assert retrieved.status == "active"
        assert retrieved.document_count == 0
        assert retrieved.total_chunks == 0

    def test_knowledge_base_default_values(self, db_session, test_tenant):
        """测试知识库默认值。"""
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="KB with defaults",
            collection_name="default_collection",
            description="Testing defaults"
        )
        db_session.add(kb)
        db_session.commit()

        retrieved = db_session.query(KnowledgeBase).filter(
            KnowledgeBase.collection_name == "default_collection"
        ).first()

        assert retrieved.chunk_size == 500  # default
        assert retrieved.chunk_overlap == 50  # default
        assert retrieved.top_k == 3  # default
        assert retrieved.ocr_enabled is True  # default
        assert retrieved.ocr_threshold == 10  # default

    def test_knowledge_base_tenant_relationship(self, db_session, test_tenant):
        """测试知识库属于租户。"""
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Tenant KB",
            collection_name="tenant_kb"
        )
        db_session.add(kb)
        db_session.commit()

        # 通过知识库访问租户关系（如果有 back_populates）
        assert kb.tenant_id == test_tenant.id

    def test_unique_collection_name(self, db_session, test_tenant):
        """测试集合名称唯一性。"""
        kb1 = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="KB 1",
            collection_name="duplicate_collection"
        )
        db_session.add(kb1)
        db_session.commit()

        # 尝试创建重复的集合名称
        kb2 = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="KB 2",
            collection_name="duplicate_collection"  # 重复
        )
        db_session.add(kb2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.flush()

        # Rollback to clear the session state
        db_session.rollback()


class TestDocumentModel:
    """测试文档模型。"""

    def test_create_document(self, db_session, test_tenant):
        """测试创建文档。"""
        # 首先创建知识库
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Test KB",
            collection_name="test_kb_for_doc"
        )
        db_session.add(kb)
        db_session.commit()

        # 创建文档
        doc = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="test_document.pdf",
            file_type="application/pdf",
            file_size=1024000,
            file_path="/uploads/test_document.pdf",
            chunk_count=10,
            upload_status="completed",
            ocr_used=True
        )
        db_session.add(doc)
        db_session.commit()

        retrieved = db_session.query(Document).filter(Document.filename == "test_document.pdf").first()
        assert retrieved is not None
        assert retrieved.filename == "test_document.pdf"
        assert retrieved.file_type == "application/pdf"
        assert retrieved.file_size == 1024000
        assert retrieved.file_path == "/uploads/test_document.pdf"
        assert retrieved.chunk_count == 10
        assert retrieved.upload_status == "completed"
        assert retrieved.ocr_used is True

    def test_document_timestamps(self, db_session, test_tenant):
        """测试文档时间戳。"""
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Test KB",
            collection_name="test_kb_timestamps"
        )
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="timestamp_test.pdf",
            file_type="application/pdf",
            file_size=5000,
            file_path="/uploads/timestamp_test.pdf"
        )
        db_session.add(doc)
        db_session.commit()

        assert doc.uploaded_at is not None
        assert isinstance(doc.uploaded_at, datetime)
        assert doc.processed_at is None  # 尚未处理

    def test_document_pending_status(self, db_session, test_tenant):
        """测试文档待处理状态。"""
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Test KB",
            collection_name="test_kb_pending"
        )
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="pending.pdf",
            file_type="application/pdf",
            file_size=8000,
            file_path="/uploads/pending.pdf",
            upload_status="pending",
            chunk_count=0
        )
        db_session.add(doc)
        db_session.commit()

        retrieved = db_session.query(Document).filter(Document.filename == "pending.pdf").first()
        assert retrieved.upload_status == "pending"
        assert retrieved.chunk_count == 0


class TestDocumentProcessingTaskModel:
    """测试文档处理任务模型。"""

    def test_create_processing_task(self, db_session, test_tenant):
        """测试创建处理任务。"""
        # 创建知识库和文档
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Test KB",
            collection_name="test_kb_task"
        )
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="task_test.pdf",
            file_type="application/pdf",
            file_size=10000,
            file_path="/uploads/task_test.pdf"
        )
        db_session.add(doc)
        db_session.commit()

        # 创建处理任务
        task = DocumentProcessingTask(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            document_id=doc.id,
            status="processing",
            progress=0,
            current_step="uploading"
        )
        db_session.add(task)
        db_session.commit()

        retrieved = db_session.query(DocumentProcessingTask).filter(
            DocumentProcessingTask.document_id == doc.id
        ).first()

        assert retrieved is not None
        assert retrieved.status == "processing"
        assert retrieved.progress == 0
        assert retrieved.current_step == "uploading"
        assert retrieved.error_message is None

    def test_task_progress_update(self, db_session, test_tenant):
        """测试任务进度更新。"""
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Test KB",
            collection_name="test_kb_progress"
        )
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="progress.pdf",
            file_type="application/pdf",
            file_size=12000,
            file_path="/uploads/progress.pdf"
        )
        db_session.add(doc)
        db_session.commit()

        task = DocumentProcessingTask(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            document_id=doc.id,
            status="processing",
            progress=50,
            current_step="chunking"
        )
        db_session.add(task)
        db_session.commit()

        # 更新进度
        task.progress = 75
        task.current_step = "embedding"
        db_session.commit()

        retrieved = db_session.query(DocumentProcessingTask).filter(
            DocumentProcessingTask.id == task.id
        ).first()

        assert retrieved.progress == 75
        assert retrieved.current_step == "embedding"

    def test_task_completion(self, db_session, test_tenant):
        """测试任务完成。"""
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Test KB",
            collection_name="test_kb_completion"
        )
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="complete.pdf",
            file_type="application/pdf",
            file_size=15000,
            file_path="/uploads/complete.pdf"
        )
        db_session.add(doc)
        db_session.commit()

        task = DocumentProcessingTask(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            document_id=doc.id,
            status="processing"
        )
        db_session.add(task)
        db_session.commit()

        # 标记为完成
        task.status = "completed"
        task.progress = 100
        task.current_step = "done"
        task.completed_at = datetime.now(timezone.utc)
        db_session.commit()

        retrieved = db_session.query(DocumentProcessingTask).filter(
            DocumentProcessingTask.id == task.id
        ).first()

        assert retrieved.status == "completed"
        assert retrieved.progress == 100
        assert retrieved.completed_at is not None

    def test_task_error(self, db_session, test_tenant):
        """测试任务错误处理。"""
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Test KB",
            collection_name="test_kb_error"
        )
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="error.pdf",
            file_type="application/pdf",
            file_size=20000,
            file_path="/uploads/error.pdf"
        )
        db_session.add(doc)
        db_session.commit()

        task = DocumentProcessingTask(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            document_id=doc.id,
            status="processing"
        )
        db_session.add(task)
        db_session.commit()

        # 模拟错误
        task.status = "failed"
        task.error_message = "OCR processing failed: unable to extract text"
        task.completed_at = datetime.now(timezone.utc)
        db_session.commit()

        retrieved = db_session.query(DocumentProcessingTask).filter(
            DocumentProcessingTask.id == task.id
        ).first()

        assert retrieved.status == "failed"
        assert "OCR processing failed" in retrieved.error_message


class TestKnowledgeBaseRelationships:
    """测试知识库关系。"""

    def test_knowledge_base_document_relationship(self, db_session, test_tenant):
        """测试知识库与文档的关系。"""
        # 创建知识库
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Document Relationship KB",
            collection_name="doc_rel_kb"
        )
        db_session.add(kb)
        db_session.commit()

        # 创建多个文档
        doc1 = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="doc1.pdf",
            file_type="application/pdf",
            file_size=1000,
            file_path="/uploads/doc1.pdf",
            chunk_count=5,
            upload_status="completed"
        )
        doc2 = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="doc2.pdf",
            file_type="application/pdf",
            file_size=2000,
            file_path="/uploads/doc2.pdf",
            chunk_count=8,
            upload_status="completed"
        )
        db_session.add_all([doc1, doc2])
        db_session.commit()

        # 刷新以获取关系
        db_session.refresh(kb)

        # 通过知识库访问文档
        assert kb.documents is not None
        assert len(kb.documents) == 2
        assert kb.documents[0].filename in ["doc1.pdf", "doc2.pdf"]
        assert kb.documents[1].filename in ["doc1.pdf", "doc2.pdf"]

    def test_document_knowledge_base_relationship(self, db_session, test_tenant):
        """测试文档属于知识库。"""
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Parent KB",
            collection_name="parent_kb"
        )
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="child.pdf",
            file_type="application/pdf",
            file_size=3000,
            file_path="/uploads/child.pdf"
        )
        db_session.add(doc)
        db_session.commit()

        # 通过文档访问知识库（如果有 back_populates）
        db_session.refresh(doc)
        assert doc.knowledge_base_id == kb.id

    def test_cascade_delete_knowledge_base(self, db_session, test_tenant):
        """测试删除知识库级联删除文档。"""
        # 创建知识库和文档
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Cascade KB",
            collection_name="cascade_kb"
        )
        db_session.add(kb)
        db_session.commit()

        doc1 = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="cascade1.pdf",
            file_type="application/pdf",
            file_size=4000,
            file_path="/uploads/cascade1.pdf"
        )
        doc2 = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="cascade2.pdf",
            file_type="application/pdf",
            file_size=5000,
            file_path="/uploads/cascade2.pdf"
        )
        db_session.add_all([doc1, doc2])
        db_session.commit()

        doc1_id = doc1.id
        doc2_id = doc2.id
        kb_id = kb.id

        # 删除知识库
        db_session.delete(kb)
        db_session.commit()

        # 文档应该被级联删除
        retrieved_doc1 = db_session.query(Document).filter(Document.id == doc1_id).first()
        retrieved_doc2 = db_session.query(Document).filter(Document.id == doc2_id).first()

        assert retrieved_doc1 is None, "Document 1 should be cascade deleted"
        assert retrieved_doc2 is None, "Document 2 should be cascade deleted"

        # 知识库也应该被删除
        retrieved_kb = db_session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        assert retrieved_kb is None


class TestDocumentTaskRelationship:
    """测试文档与任务的关系。"""

    def test_document_task_relationship(self, db_session, test_tenant):
        """测试文档与处理任务的关系。"""
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            name="Task Rel KB",
            collection_name="task_rel_kb"
        )
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            tenant_id=test_tenant.id,
            filename="task_rel.pdf",
            file_type="application/pdf",
            file_size=6000,
            file_path="/uploads/task_rel.pdf"
        )
        db_session.add(doc)
        db_session.commit()

        task = DocumentProcessingTask(
            id=str(uuid.uuid4()),
            tenant_id=test_tenant.id,
            document_id=doc.id,
            status="processing",
            current_step="parsing"
        )
        db_session.add(task)
        db_session.commit()

        # 查询文档的所有任务
        tasks = db_session.query(DocumentProcessingTask).filter(
            DocumentProcessingTask.document_id == doc.id
        ).all()

        assert len(tasks) == 1
        assert tasks[0].status == "processing"
        assert tasks[0].current_step == "parsing"
