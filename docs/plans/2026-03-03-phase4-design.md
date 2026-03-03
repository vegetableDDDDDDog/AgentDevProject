# Phase 4 设计文档：从"功能"到"平台"

> **项目名称**: Agent PaaS 平台 - Phase 4
> **设计日期**: 2026-03-03
> **设计者**: Claude + 用户协作
> **状态**: 待审批

---

## 📋 执行摘要

Phase 4 将把现有的 Agent PaaS 平台从"功能集合"升级为**企业级生产力平台**，通过三个递进阶段实现：

| 优先级 | 功能模块 | 核心价值 | 预计工期 |
|--------|----------|----------|----------|
| **P0** | 多租户 RAG 闭环 | 每个部门拥有自己的智能知识库 | 2-3 周 |
| **P1** | HTTP 自定义工具构建器 | 无代码接入企业内部系统 | 1-2 周 |
| **P2** | 推理链可视化 | Agent 决策过程透明可审计 | 1 周 |

**定位**: 企业内部生产力工具（非商业化 SaaS）

---

## 🎯 设计原则

1. **异步优先**: 所有耗时操作（文档处理、向量化）使用后台任务
2. **租户隔离**: 数据、向量、工具完全隔离，支持同一租户多知识库
3. **可观测性**: 每个关键环节都有进度反馈和状态追踪
4. **渐进增强**: MVP 使用免费方案，预留云端服务升级路径

---

## 🔷 P0：多租户 RAG 闭环（含异步处理 + OCR）

### 核心目标

让每个租户（部门）能通过前端上传文档，自动构建专属向量库，并获得混合检索能力。

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (React)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 文档上传     │  │ 进度条       │  │ 知识库管理   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
└─────────┼──────────────────┼──────────────────────────────────┘
          │                  │
          │ POST /upload     │ SSE /tasks/{id}/stream
          ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI 后端                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ POST /api/v1/knowledge/upload                          │   │
│  │  - 返回 task_id (< 500ms)                               │   │
│  └────────────────┬────────────────────────────────────────┘   │
│                   │                                              │
│                   ▼                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ BackgroundTasks (异步处理)                              │   │
│  │  1. 保存文件 (10%)                                      │   │
│  │  2. 文件类型检测 (15%)                                  │   │
│  │  3. 解析/OCR (20-40%)                                   │   │
│  │  4. 分块 (40-60%)                                       │   │
│  │  5. 向量化 (60-90%)                                     │   │
│  │  6. 存储到 ChromaDB (90-100%)                           │   │
│  └────────────────┬────────────────────────────────────────┘   │
│                   │                                              │
│                   ▼                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ChromaDB (多租户隔离)                                    │   │
│  │  Collection: tenant_{id}_kb_{kb_id}                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 关键组件设计

#### 1. 数据模型

```python
# services/database.py

class KnowledgeBase(Base):
    """知识库元数据"""
    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)  # 如"技术文档库"
    description = Column(Text)

    # ChromaDB 配置
    collection_name = Column(String(100), unique=True, nullable=False)
    # 格式: tenant_{tenant_id}_kb_{kb_id}

    # 分块配置
    chunk_size = Column(Integer, default=500)
    chunk_overlap = Column(Integer, default=50)

    # 检索配置
    hybrid_search_weights = Column(JSON, default={"vector": 0.7, "bm25": 0.3})
    top_k = Column(Integer, default=3)

    # OCR 配置
    ocr_enabled = Column(Boolean, default=True)
    ocr_threshold = Column(Integer, default=10)  # 每页少于 N 字触发 OCR

    # 状态
    status = Column(String(20), default="active")  # active/archived
    document_count = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_kb_tenant', 'tenant_id'),
        Index('idx_kb_collection', 'collection_name'),
    )


class Document(Base):
    """文档记录"""
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)

    # 文件信息
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf/md/xlsx/txt/image
    file_size = Column(Integer)  # bytes
    file_path = Column(String(500))  # 本地存储路径

    # 处理信息
    chunk_count = Column(Integer, default=0)
    upload_status = Column(String(20), default="processing")  # processing/ready/failed
    ocr_used = Column(Boolean, default=False)  # 是否使用了 OCR

    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)

    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")

    __table_args__ = (
        Index('idx_doc_kb', 'knowledge_base_id'),
        Index('idx_doc_tenant', 'tenant_id'),
        Index('idx_doc_status', 'upload_status'),
    )


class DocumentProcessingTask(Base):
    """异步处理任务"""
    __tablename__ = "document_processing_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)

    # 任务状态
    status = Column(String(20), default="pending")  # pending/processing/completed/failed
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(100))  # 当前步骤描述
    error_message = Column(Text)

    # 时间戳
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_task_doc', 'document_id'),
        Index('idx_task_status', 'status'),
    )
```

#### 2. 文档类型检测（含 OCR 触发阈值）

```python
# services/document_type_detector.py

import pypdf
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class DocumentTypeDetector:
    """智能文档类型检测"""

    def __init__(self, ocr_threshold: int = 10):
        """
        Args:
            ocr_threshold: 每页少于 N 个字符时触发 OCR（默认 10）
        """
        self.ocr_threshold = ocr_threshold

    def detect_document_type(
        self,
        file_path: str,
        knowledge_base: KnowledgeBase
    ) -> dict:
        """
        检测文档类型和处理策略

        Returns:
            {
                'type': 'text_pdf' | 'image_pdf' | 'image' | 'text',
                'needs_ocr': bool,
                'reason': str
            }
        """
        file_ext = file_path.lower().split('.')[-1]

        # PDF 处理
        if file_ext == 'pdf':
            return self._analyze_pdf(file_path, knowledge_base)

        # 图片处理
        elif file_ext in ['png', 'jpg', 'jpeg', 'tiff', 'bmp']:
            return {
                'type': 'image',
                'needs_ocr': True,
                'reason': '纯图片文件，需要 OCR'
            }

        # 文本文件
        elif file_ext in ['md', 'txt', 'markdown']:
            return {
                'type': 'text',
                'needs_ocr': False,
                'reason': '文本文件，直接解析'
            }

        # Excel
        elif file_ext in ['xlsx', 'xls']:
            return {
                'type': 'excel',
                'needs_ocr': False,
                'reason': 'Excel 文件，使用 openpyxl 解析'
            }

        else:
            raise ValueError(f"不支持的文件类型: {file_ext}")

    def _analyze_pdf(
        self,
        file_path: str,
        knowledge_base: KnowledgeBase
    ) -> dict:
        """分析 PDF 类型（含 OCR 触发阈值判断）"""

        try:
            pdf_reader = pypdf.PdfReader(file_path)
            total_pages = len(pdf_reader.pages)

            # 检查前 3 页的文本内容
            sample_pages = min(3, total_pages)
            total_chars = 0
            has_text = False

            for i in range(sample_pages):
                page = pdf_reader.pages[i]
                text = page.extract_text()
                char_count = len(text.strip())
                total_chars += char_count

                if char_count > 0:
                    has_text = True

            avg_chars_per_page = total_chars / sample_pages

            # OCR 触发阈值判断
            threshold = knowledge_base.ocr_threshold or self.ocr_threshold

            if avg_chars_per_page < threshold:
                logger.info(
                    f"PDF 平均每页 {avg_chars_per_page:.1f} 字符 "
                    f"< 阈值 {threshold}，判定为扫描件"
                )
                return {
                    'type': 'image_pdf',
                    'needs_ocr': True,
                    'reason': f'平均每页 {avg_chars_per_page:.0f} 字 < 阈值 {threshold}'
                }
            else:
                return {
                    'type': 'text_pdf',
                    'needs_ocr': False,
                    'reason': f'包含文本层（平均 {avg_chars_per_page:.0f} 字/页）'
                }

        except Exception as e:
            logger.error(f"PDF 分析失败: {e}")
            # 分析失败时默认使用 OCR
            return {
                'type': 'image_pdf',
                'needs_ocr': True,
                'reason': f'PDF 分析异常，降级为 OCR: {str(e)}'
            }
```

#### 3. OCR 服务（策略模式）

```python
# services/ocr_service.py

from abc import ABC, abstractmethod
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class OCRService(ABC):
    """OCR 服务抽象基类"""

    @abstractmethod
    async def extract_text(self, image_path: str) -> str:
        """从图片/PDF 中提取文字"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """服务名称"""
        pass


class TesseractOCR(OCRService):
    """本地 Tesseract OCR（免费，支持中文）"""

    def __init__(self, lang: str = 'chi_sim+eng'):
        """
        Args:
            lang: 语言包，默认中英文混合
        """
        try:
            import pytesseract
            self.pytesseract = pytesseract
            self.lang = lang
            logger.info(f"初始化 Tesseract OCR (语言: {lang})")
        except ImportError:
            raise ImportError(
                "请安装依赖: pip install pytesseract pdf2image pillow\n"
                "系统依赖: sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim"
            )

    async def extract_text(self, file_path: str) -> str:
        """从 PDF 或图片中提取文字"""

        try:
            # 将 PDF 转为图片
            if file_path.endswith('.pdf'):
                logger.info(f"将 PDF 转为图片: {file_path}")
                images = convert_from_path(file_path, dpi=200)
            else:
                images = [Image.open(file_path)]

            # 提取文字
            all_text = []
            for i, img in enumerate(images, 1):
                logger.debug(f"OCR 处理第 {i}/{len(images)} 页")
                text = self.pytesseract.image_to_string(img, lang=self.lang)
                all_text.append(f"\n--- 第 {i} 页 ---\n{text}")

            result = '\n'.join(all_text)
            logger.info(f"OCR 提取完成，共 {len(result)} 字符")
            return result

        except Exception as e:
            logger.error(f"OCR 提取失败: {e}")
            raise

    @property
    def name(self) -> str:
        return f"Tesseract OCR (语言: {self.lang})"


class OCRServiceFactory:
    """OCR 服务工厂"""

    @staticmethod
    def create_service(config: dict) -> OCRService:
        """
        根据配置创建 OCR 服务

        Args:
            config: {
                'provider': 'tesseract' | 'azure' | 'baidu',
                'lang': 'chi_sim+eng',  # 可选
                'api_key': str,  # 云服务需要
                'endpoint': str  # 云服务需要
            }
        """
        provider = config.get('provider', 'tesseract')

        if provider == 'tesseract':
            return TesseractOCR(lang=config.get('lang', 'chi_sim+eng'))

        elif provider == 'azure':
            # 预留：Azure Computer Vision
            raise NotImplementedError("Azure OCR 尚未实现")

        elif provider == 'baidu':
            # 预留：百度 OCR
            raise NotImplementedError("百度 OCR 尚未实现")

        else:
            raise ValueError(f"未知的 OCR 提供商: {provider}")
```

#### 4. 异步文档处理器

```python
# services/document_processor.py

import os
import shutil
import asyncio
from typing import Optional
from fastapi import BackgroundTasks
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings

from services.database import (
    KnowledgeBase, Document, DocumentProcessingTask,
    get_db
)
from services.document_type_detector import DocumentTypeDetector
from services.ocr_service import OCRServiceFactory
from services.embeddings_service import EmbeddingService
from api.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """异步文档处理器"""

    def __init__(self, db_session):
        self.db = db_session
        self.type_detector = DocumentTypeDetector(ocr_threshold=10)
        self.ocr_service = OCRServiceFactory.create_service(
            settings.OCR_CONFIG
        )
        self.embeddings = EmbeddingService()

    async def upload_document_async(
        self,
        file,
        knowledge_base_id: str,
        tenant_id: str,
        background_tasks: BackgroundTasks
    ) -> str:
        """
        异步上传文档

        Returns:
            task_id: 任务 ID（立即返回）
        """
        # 1. 保存文件到本地
        file_path = await self._save_file(file, tenant_id)

        # 2. 创建文档记录
        document = Document(
            knowledge_base_id=knowledge_base_id,
            tenant_id=tenant_id,
            filename=file.filename,
            file_type=file.filename.split('.')[-1].lower(),
            file_size=os.path.getsize(file_path),
            file_path=file_path,
            upload_status="processing"
        )
        self.db.add(document)
        self.db.commit()

        # 3. 创建处理任务
        task = DocumentProcessingTask(
            document_id=document.id,
            tenant_id=tenant_id,
            status="processing",
            progress=0,
            current_step="任务已创建"
        )
        self.db.add(task)
        self.db.commit()

        # 4. 提交后台任务
        background_tasks.add_task(
            self._process_document_background,
            task.id,
            document.id,
            file_path
        )

        logger.info(f"文档 {file.filename} 已提交处理，任务 ID: {task.id}")
        return task.id

    async def _process_document_background(
        self,
        task_id: str,
        document_id: str,
        file_path: str
    ):
        """后台异步处理文档"""
        db = next(get_db())

        try:
            task = db.query(DocumentProcessingTask).get(task_id)
            document = db.query(Document).get(document_id)
            kb = db.query(KnowledgeBase).get(document.knowledge_base_id)

            # Step 1: 文件类型检测 (10-15%)
            await self._update_progress(task, 10, "正在分析文件类型...")
            detection_result = self.type_detector.detect_document_type(
                file_path, kb
            )

            logger.info(
                f"文件类型检测: {detection_result['type']}, "
                f"需要 OCR: {detection_result['needs_ocr']}"
            )

            # Step 2: 解析文本 (15-40%)
            if detection_result['needs_ocr']:
                await self._update_progress(task, 15, "检测到扫描件，正在 OCR 识别...")
                text = await self.ocr_service.extract_text(file_path)
                document.ocr_used = True
            else:
                await self._update_progress(task, 15, "正在解析文档...")
                text = await self._parse_file(file_path)

            await self._update_progress(task, 40, "文档解析完成")

            # Step 3: 分块 (40-60%)
            await self._update_progress(task, 40, "正在分块...")
            chunks = await self._split_text(text, kb)

            # Step 4: 向量化 (60-90%)
            await self._update_progress(task, 60, "正在向量化...")
            embeddings = await self._embed_chunks(chunks)

            # Step 5: 存储到 ChromaDB (90-100%)
            await self._update_progress(task, 90, "正在存储到向量库...")
            await self._store_to_chroma(chunks, embeddings, kb, document)

            # 完成
            await self._update_progress(task, 100, "处理完成")
            self._mark_task_completed(task, document)

            logger.info(f"文档 {document.filename} 处理完成")

        except Exception as e:
            logger.error(f"文档处理失败: {e}", exc_info=True)
            self._mark_task_failed(task, str(e))

        finally:
            db.close()

    async def _update_progress(
        self,
        task: DocumentProcessingTask,
        progress: int,
        current_step: str
    ):
        """更新任务进度"""
        task.progress = progress
        task.current_step = current_step
        self.db.commit()

    def _mark_task_completed(
        self,
        task: DocumentProcessingTask,
        document: Document
    ):
        """标记任务完成"""
        task.status = "completed"
        task.progress = 100
        task.completed_at = datetime.utcnow()

        document.upload_status = "ready"
        document.processed_at = datetime.utcnow()

        # 更新知识库统计
        kb = document.knowledge_base
        kb.document_count += 1
        kb.total_chunks += document.chunk_count
        kb.updated_at = datetime.utcnow()

        self.db.commit()

    def _mark_task_failed(self, task: DocumentProcessingTask, error: str):
        """标记任务失败"""
        task.status = "failed"
        task.error_message = error
        task.completed_at = datetime.utcnow()

        document = task.document
        document.upload_status = "failed"

        self.db.commit()

    async def _save_file(self, file, tenant_id: str) -> str:
        """保存文件到本地"""
        upload_dir = f"data/knowledge_bases/{tenant_id}"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = f"{upload_dir}/{file.filename}"
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        return file_path

    async def _parse_file(self, file_path: str) -> str:
        """解析文件（文本/Markdown/Excel）"""
        ext = file_path.lower().split('.')[-1]

        if ext in ['md', 'txt']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

        elif ext == 'pdf':
            import pypdf
            pdf_reader = pypdf.PdfReader(file_path)
            return '\n'.join([page.extract_text() for page in pdf_reader.pages])

        elif ext in ['xlsx', 'xls']:
            import openpyxl
            wb = openpyxl.load_workbook(file_path)
            sheets = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                data = []
                for row in ws.iter_rows(values_only=True):
                    data.append('\t'.join([str(cell) for cell in row]))
                sheets.append(f"## {sheet_name}\n" + '\n'.join(data))
            return '\n\n'.join(sheets)

        else:
            raise ValueError(f"不支持的文件类型: {ext}")

    async def _split_text(
        self,
        text: str,
        kb: KnowledgeBase
    ) -> list:
        """分块"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=kb.chunk_size,
            chunk_overlap=kb.chunk_overlap,
            separators=["\n\n##", "\n\n", "\n", "。", "，", " ", ""]
        )
        return splitter.split_text(text)

    async def _embed_chunks(self, chunks: list) -> list:
        """向量化"""
        return await self.embeddings.embed_documents(chunks)

    async def _store_to_chroma(
        self,
        chunks: list,
        embeddings: list,
        kb: KnowledgeBase,
        document: Document
    ):
        """存储到 ChromaDB"""
        from langchain_core.documents import Document

        # 构造 LangChain Document
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    'document_id': document.id,
                    'tenant_id': kb.tenant_id,
                    'knowledge_base_id': kb.id,
                    'filename': document.filename,
                    'chunk_index': i
                }
            )
            for i, chunk in enumerate(chunks)
        ]

        # 存储到租户专属 Collection
        # 命名策略: tenant_{id}_kb_{id}
        collection_name = kb.collection_name

        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=f"data/chroma/{kb.tenant_id}"
        )

        vectorstore.add_documents(documents)

        # 更新文档分块计数
        document.chunk_count = len(chunks)
```

#### 5. 混合检索器

```python
# services/hybrid_retriever.py

from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_community.vectorstores import Chroma

from services.database import KnowledgeBase
from services.embeddings_service import EmbeddingService

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """混合检索器（向量 + BM25）"""

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.embeddings = EmbeddingService()

        # 加载向量检索器
        self.vector_store = Chroma(
            collection_name=knowledge_base.collection_name,
            embedding_function=self.embeddings,
            persist_directory=f"data/chroma/{knowledge_base.tenant_id}"
        )
        self.vector_retriever = self.vector_store.as_retriever(
            search_kwargs={"k": knowledge_base.top_k}
        )

        # 加载 BM25 检索器
        # TODO: 从数据库或缓存加载已索引的文档
        self.bm25_retriever = self._load_bm25_retriever()

        # 混合权重
        weights = knowledge_base.hybrid_search_weights
        self.ensemble = EnsembleRetriever(
            retrievers=[self.vector_retriever, self.bm25_retriever],
            weights=[weights.get("vector", 0.7), weights.get("bm25", 0.3)]
        )

        logger.info(
            f"混合检索器初始化完成 (Vector: {weights['vector']}, "
            f"BM25: {weights['bm25']})"
        )

    def _load_bm25_retriever(self) -> BM25Retriever:
        """加载 BM25 检索器"""
        # 从 ChromaDB 加载所有文档
        all_docs = self.vector_store.get()

        from langchain_core.documents import Document
        documents = [
            Document(page_content=doc['page_content'], metadata=doc['metadata'])
            for doc in all_docs['documents']
        ]

        return BM25Retriever.from_documents(documents)

    def _get_relevant_documents(self, query, run_manager=None):
        """检索相关文档"""
        logger.debug(f"混合检索查询: {query}")
        results = self.ensemble.get_relevant_documents(query)
        logger.info(f"检索到 {len(results)} 个文档片段")
        return results
```

#### 6. API 路由

```python
# api/routers/knowledge.py

from fastapi import APIRouter, UploadFile, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from services.database import get_db
from services.document_processor import DocumentProcessor
from api.schemas.knowledge import (
    DocumentUploadResponse,
    TaskProgressResponse,
    KnowledgeBaseListResponse
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile,
    knowledge_base_id: str,
    tenant_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    上传文档到知识库

    Returns:
        task_id: 任务 ID
    """
    processor = DocumentProcessor(db)
    task_id = await processor.upload_document_async(
        file, knowledge_base_id, tenant_id, background_tasks
    )

    return DocumentUploadResponse(task_id=task_id)


@router.get("/tasks/{task_id}", response_model=TaskProgressResponse)
async def get_task_progress(
    task_id: str,
    db: Session = Depends(get_db)
):
    """查询任务进度（轮询方式）"""
    task = db.query(DocumentProcessingTask).get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskProgressResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress,
        current_step=task.current_step,
        error_message=task.error_message
    )


@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str, db: Session = Depends(get_db)):
    """
    SSE 推送任务进度（推荐）

    消息格式:
    ```
    event: progress
    data: {"type": "progress", "value": 45, "msg": "正在向量化"}

    event: complete
    data: {"type": "complete", "document_id": "xxx"}
    ```
    """

    async def event_stream():
        while True:
            task = db.query(DocumentProcessingTask).get(task_id)

            if not task:
                yield f"event: error\ndata: {json.dumps({'msg': '任务不存在'})}\n\n"
                break

            # 推送进度
            yield f"event: progress\ndata: {json.dumps({
                'type': 'progress',
                'value': task.progress,
                'msg': task.current_step,
                'status': task.status
            })}\n\n"

            # 完成/失败
            if task.status == 'completed':
                yield f"event: complete\ndata: {json.dumps({
                    'type': 'complete',
                    'document_id': task.document_id,
                    'chunks': task.document.chunk_count
                })}\n\n"
                break

            elif task.status == 'failed':
                yield f"event: failed\ndata: {json.dumps({
                    'type': 'failed',
                    'error': task.error_message
                })}\n\n"
                break

            await asyncio.sleep(0.5)  # 每 0.5 秒推送一次

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )


@router.get("/{tenant_id}/collections", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    """列出租户的所有知识库"""
    kbs = db.query(KnowledgeBase).filter(
        KnowledgeBase.tenant_id == tenant_id,
        KnowledgeBase.status == "active"
    ).all()

    return KnowledgeBaseListResponse(
        knowledge_bases=[
            {
                'id': kb.id,
                'name': kb.name,
                'document_count': kb.document_count,
                'total_chunks': kb.total_chunks,
                'created_at': kb.created_at
            }
            for kb in kbs
        ]
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """删除文档及其向量"""
    document = db.query(Document).get(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # TODO: 从 ChromaDB 删除向量
    # vector_store.delete(where={"document_id": document_id})

    # 删除文件
    if os.path.exists(document.file_path):
        os.remove(document.file_path)

    # 删除记录
    db.delete(document)

    # 更新知识库统计
    kb = document.knowledge_base
    kb.document_count -= 1
    kb.total_chunks -= document.chunk_count

    db.commit()

    return {"message": "文档已删除"}
```

#### 7. 前端实现

```tsx
// frontend/src/components/Knowledge/DocumentUploader.tsx

import { useState } from 'react'
import { Upload, Button, Progress, message } from 'antd'
import { UploadOutlined } from '@ant-design/icons'

export function DocumentUploader({ knowledgeBaseId, tenantId }) {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState('')

  const handleUpload = async (file) => {
    setUploading(true)
    setProgress(0)

    try {
      // 1. 上传文件，获取 task_id
      const formData = new FormData()
      formData.append('file', file)
      formData.append('knowledge_base_id', knowledgeBaseId)
      formData.append('tenant_id', tenantId)

      const response = await fetch('/api/v1/knowledge/upload', {
        method: 'POST',
        body: formData
      })

      const { task_id } = await response.json()

      // 2. 建立 SSE 连接监听进度
      const eventSource = new EventSource(
        `/api/v1/knowledge/tasks/${task_id}/stream`
      )

      eventSource.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data)
        setProgress(data.value)
        setCurrentStep(data.msg)
      })

      eventSource.addEventListener('complete', (e) => {
        const data = JSON.parse(e.data)
        message.success(`文档处理完成！共 ${data.chunks} 个分块`)
        setUploading(false)
        eventSource.close()
      })

      eventSource.addEventListener('error', (e) => {
        const data = JSON.parse(e.data)
        message.error(`处理失败: ${data.msg}`)
        setUploading(false)
        eventSource.close()
      })

      eventSource.onerror = () => {
        message.error('连接中断')
        setUploading(false)
        eventSource.close()
      }

    } catch (error) {
      message.error(`上传失败: ${error.message}`)
      setUploading(false)
    }

    return false  // 阻止 Ant Design 默认上传行为
  }

  return (
    <div>
      <Upload
        customRequest={({ file }) => handleUpload(file)}
        disabled={uploading}
        accept=".pdf,.md,.xlsx,.txt"
      >
        <Button icon={<UploadOutlined />} loading={uploading}>
          上传文档
        </Button>
      </Upload>

      {uploading && (
        <div style={{ marginTop: 16 }}>
          <Progress percent={progress} status="active" />
          <p style={{ marginTop: 8, color: '#666' }}>{currentStep}</p>
        </div>
      )}
    </div>
  )
}
```

### P0 验收标准

#### 功能验收
- ✅ 前端能上传 PDF/MD/Excel/TXT 文件
- ✅ 后端自动检测文档类型（文本 vs 扫描件）
- ✅ 扫描件自动触发 OCR（Tesseract 中文支持）
- ✅ 异步处理，上传立即返回 task_id
- ✅ SSE 实时推送处理进度（0-100% + 当前步骤）
- ✅ 不同租户的知识库完全隔离
- ✅ ChromaDB Collection 命名: `tenant_{id}_kb_{id}`
- ✅ 混合检索（Vector 70% + BM25 30%）优于纯向量检索
- ✅ 支持文档删除和重新上传

#### 性能验收
- 文档上传响应时间 < 500ms（仅返回 task_id）
- 10MB 文本 PDF 处理时间 < 30 秒
- 10MB 扫描件 PDF (OCR) 处理时间 < 2 分钟
- 进度更新延迟 < 1 秒

#### 代码质量
- 单元测试覆盖率 > 80%
- 集成测试覆盖完整上传流程
- 错误处理完善（上传失败、OCR 失败、存储失败）

---

## 🔷 P1：HTTP 自定义工具构建器

### 核心目标

让业务人员通过 UI 配置 HTTP API，自动转换为 Agent 可调用的工具，无需写代码。

### 数据模型

```python
# services/database.py

class CustomTool(Base):
    """自定义工具配置"""
    __tablename__ = "custom_tools"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)

    # 工具信息
    name = Column(String(100), nullable=False)  # 如"查询 Jira Issue"
    description = Column(Text, nullable=False)  # Agent 如何使用此工具
    category = Column(String(50))  # api/database/custom

    # API 配置（加密存储）
    api_config = Column(JSON, nullable=False)

    # 示例 api_config 结构:
    # {
    #     "base_url": "https://jira.company.com/rest/api/2/issue/{issue_id}",
    #     "method": "GET",
    #     "headers": {
    #         "Authorization": "Bearer encrypted_xxx",
    #         "Content-Type": "application/json"
    #     },
    #     "path_params": ["issue_id"],
    #     "query_params": {"fields": "summary,status"},
    #     "body_schema": {},
    #     "response_mapping": {
    #         "summary": "$.fields.summary",
    #         "status": "$.fields.status.name"
    #     }
    # }

    # 状态
    is_active = Column(Boolean, default=True)
    test_result = Column(JSON)  # 测试调用结果

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_custom_tool_tenant', 'tenant_id'),
        Index('idx_custom_tool_active', 'is_active'),
    )
```

### 动态工具工厂

```python
# services/dynamic_tool_factory.py

from langchain_core.tools import StructuredTool
from langchain.pydantic_v1 import BaseModel, Field
import requests
import json
from services.encryption_service import EncryptionService

logger = logging.getLogger(__name__)


class DynamicToolFactory:
    """动态工具工厂"""

    def __init__(self, encryption_service: EncryptionService):
        self.encryption = encryption_service

    def create_tool(self, custom_tool: CustomTool) -> StructuredTool:
        """根据数据库配置动态构造 LangChain 工具"""

        config = custom_tool.api_config

        # 解密 API Key
        headers = self._decrypt_headers(config.get("headers", {}))

        # 构造参数 Schema
        args_schema = self._build_schema(
            config.get("path_params", []),
            config.get("body_schema", {})
        )

        def _run(**kwargs):
            """实际执行 HTTP 请求"""
            try:
                # 构造 URL
                url = self._build_url(
                    config["base_url"],
                    kwargs,
                    config.get("path_params", [])
                )

                # 提取 body 参数
                body_params = {
                    k: v for k, v in kwargs.items()
                    if k not in config.get("path_params", [])
                }

                # 发送请求
                response = requests.request(
                    method=config["method"],
                    url=url,
                    headers=headers,
                    params=config.get("query_params"),
                    json=body_params if body_params else None,
                    timeout=30
                )

                response.raise_for_status()

                # 提取返回值
                return self._extract_response(
                    response.json(),
                    config.get("response_mapping", {})
                )

            except Exception as e:
                logger.error(f"工具调用失败: {e}")
                return f"工具调用失败: {str(e)}"

        return StructuredTool.from_function(
            name=custom_tool.name,
            description=custom_tool.description,
            func=_run,
            args_schema=args_schema
        )

    def _decrypt_headers(self, headers: dict) -> dict:
        """解密 Headers 中的敏感信息"""
        decrypted = {}
        for key, value in headers.items():
            if key.lower() in ['authorization', 'x-api-key']:
                # 解密
                decrypted[key] = self.encryption.decrypt(value)
            else:
                decrypted[key] = value
        return decrypted

    def _build_url(self, base_url: str, kwargs: dict, path_params: list) -> str:
        """构造完整 URL（替换路径参数）"""
        url = base_url
        for param in path_params:
            if param in kwargs:
                url = url.replace(f"{{{param}}}", str(kwargs[param]))
        return url

    def _build_schema(self, path_params: list, body_schema: dict):
        """动态构造 Pydantic Schema"""
        fields = {}

        # 路径参数
        for param in path_params:
            fields[param] = Field(
                description=f"路径参数: {param}",
                default=...  # 必填
            )

        # Body 参数
        for field_name, field_config in body_schema.items():
            fields[field_name] = Field(
                description=field_config.get("description", ""),
                default=field_config.get("default", ...),
                type=field_config.get("type", "str")
            )

        # 动态创建 Schema 类
        SchemaClass = type(
            'DynamicToolSchema',
            (BaseModel,),
            {'__annotations__': {k: str for k in fields.keys()}, **fields}
        )

        return SchemaClass

    def _extract_response(self, response: dict, mapping: dict) -> str:
        """从响应中提取字段"""
        if not mapping:
            return json.dumps(response, ensure_ascii=False)

        extracted = {}
        for key, path in mapping.items():
            # 简单的 JSONPath 实现（支持 $.field.subfield）
            if path.startswith('$.'):
                parts = path[2:].split('.')
                value = response
                for part in parts:
                    value = value.get(part, {})
                extracted[key] = value
            else:
                extracted[key] = response.get(path)

        return json.dumps(extracted, ensure_ascii=False, indent=2)
```

### API 密钥加密服务

```python
# services/encryption_service.py

from cryptography.fernet import Fernet
import base64
import os

logger = logging.getLogger(__name__)


class EncryptionService:
    """API Key 加密服务（对称加密）"""

    def __init__(self, secret_key: str = None):
        """
        Args:
            secret_key: 32 字节密钥，从环境变量读取
        """
        key = secret_key or os.getenv('ENCRYPTION_SECRET_KEY')
        if not key:
            # 生成新密钥
            key = Fernet.generate_key()
            logger.warning("未设置 ENCRYPTION_SECRET_KEY，已生成新密钥")

        # 确保 32 字节（Fernet 要求）
        if len(key) < 32:
            key = key.ljust(32, b'0')
        elif len(key) > 32:
            key = key[:32]

        self.cipher = Fernet(base64.urlsafe_b64encode(key))

    def encrypt(self, plaintext: str) -> str:
        """加密"""
        if not plaintext:
            return ""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, ciphertext: str) -> str:
        """解密"""
        if not ciphertext:
            return ""
        decrypted = self.cipher.decrypt(ciphertext.encode())
        return decrypted.decode()
```

### 前端工具构建器

```tsx
// frontend/src/pages/Tools/CustomToolBuilder.tsx

import { Form, Input, Select, Button, message } from 'antd'

export function CustomToolBuilder({ tenantId }) {
  const [form] = Form.useForm()

  const handleSave = async (values) => {
    try {
      // 加密 API Key（前端不加密，后端处理）
      const config = {
        base_url: values.apiUrl,
        method: values.method,
        headers: JSON.parse(values.headers),
        path_params: values.pathParams,
        query_params: values.queryParams ? JSON.parse(values.queryParams) : {},
        response_mapping: values.responseMapping ? JSON.parse(values.responseMapping) : {}
      }

      await api.post('/api/v1/tools/custom', {
        tenant_id: tenantId,
        name: values.name,
        description: values.description,
        api_config: config
      })

      message.success('工具创建成功！')
      form.resetFields()

    } catch (error) {
      message.error(`创建失败: ${error.message}`)
    }
  }

  return (
    <Form form={form} onFinish={handleSave} layout="vertical">
      <Form.Item
        name="name"
        label="工具名称"
        rules={[{ required: true }]}
      >
        <Input placeholder="如：查询 Jira Issue" />
      </Form.Item>

      <Form.Item
        name="description"
        label="功能描述"
        rules={[{ required: true }]}
      >
        <Input.TextArea
          rows={3}
          placeholder="如：根据 Jira Issue ID 查询 issue 的详细信息，包括摘要、状态、优先级等"
        />
      </Form.Item>

      <Form.Item
        name="apiUrl"
        label="API 地址"
        rules={[{ required: true }]}
      >
        <Input placeholder="https://api.company.com/v1/resource/{id}" />
      </Form.Item>

      <Form.Item
        name="method"
        label="HTTP 方法"
        rules={[{ required: true }]}
      >
        <Select>
          <Select.Option value="GET">GET</Select.Option>
          <Select.Option value="POST">POST</Select.Option>
          <Select.Option value="PUT">PUT</Select.Option>
          <Select.Option value="DELETE">DELETE</Select.Option>
        </Select>
      </Form.Item>

      <Form.Item
        name="headers"
        label="请求 Headers (JSON)"
      >
        <Input.TextArea
          rows={3}
          placeholder='{"Authorization": "Bearer xxx", "Content-Type": "application/json"}'
        />
      </Form.Item>

      <Form.Item
        name="pathParams"
        label="路径参数"
      >
        <Select
          mode="tags"
          placeholder="如：issue_id, project_key"
        />
      </Form.Item>

      <Form.Item
        name="responseMapping"
        label="响应映射 (JSONPath，可选)"
      >
        <Input.TextArea
          rows={3}
          placeholder='{"summary": "$.fields.summary", "status": "$.fields.status.name"}'
        />
      </Form.Item>

      <Form.Item>
        <Button type="primary" htmlType="submit">
          创建工具
        </Button>
      </Form.Item>
    </Form>
  )
}
```

### P1 验收标准

- ✅ 前端能通过表单配置 HTTP API 工具
- ✅ 支持自定义 Headers（含 API Key）
- ✅ 支持路径参数替换（如 `{issue_id}`）
- ✅ API Key 加密存储，数据库中不可见明文
- ✅ 配置后的工具自动出现在 Agent 可用工具列表
- ✅ Agent 能正确调用工具并解析返回值
- ✅ 提供测试调用功能

---

## 🔷 P2：推理链可视化

### 核心目标

在前端展示 Agent 的完整思考过程，包括检索的文档片段、工具调用详情。

### SSE 协议扩展

```python
# api/sse_protocol.py (扩展)

from enum import Enum


class SSEEventType(Enum):
    # ... 现有类型 ...
    SOURCE = "source"  # 检索到的文档片段
    RETRIEVAL_SCORE = "retrieval_score"  # 检索相似度分数


class SourceEvent:
    """检索结果事件"""

    def __init__(self, sources: list):
        """
        Args:
            sources: [
                {
                    "content": "文档片段内容...",
                    "metadata": {"source": "doc.pdf", "page": 1},
                    "score": 0.85
                }
            ]
        """
        self.sources = sources

    def to_sse(self) -> str:
        return f"event: source\ndata: {json.dumps({
            'type': 'source',
            'sources': self.sources
        })}\n\n"
```

### RAGAgent 改造

```python
# agents/rag_agent.py (扩展)

async def astream_with_observations(self, query: str):
    """流式输出，附带检索观察"""

    # 1. 检索阶段
    docs_with_scores = await self.retriever.aretrieve_with_scores(query)

    # 发送检索结果到前端
    yield SourceEvent([
        {
            "content": doc.page_content[:200],  # 前 200 字符
            "metadata": doc.metadata,
            "score": float(score)
        }
        for doc, score in docs_with_scores
    ]).to_sse()

    # 2. 构造提示词
    context = "\n\n".join([doc.page_content for doc, _ in docs_with_scores])
    prompt = self.prompt_template.format(
        context=context,
        question=query
    )

    # 3. 生成阶段
    async for chunk in self.llm.astream(prompt):
        yield TokenEvent(content=chunk).to_sse()
```

### 前端"思考过程"面板

```tsx
// frontend/src/components/Chat/ThinkingProcess.tsx

import { Collapse, Card, Tag, Progress } from 'antd'

export function ThinkingProcess({ events }: { events: SSEEvent[] }) {
  const sourceEvents = events.filter(e => e.type === 'source')
  const toolEvents = events.filter(e => e.type.startsWith('tool_'))

  return (
    <div className="thinking-panel">
      <Collapse>
        {/* 检索文档片段 */}
        <Panel header="检索到的文档片段" key="sources">
          {sourceEvents.map((event, idx) => (
            <div key={idx}>
              {event.data.sources.map((source, i) => (
                <Card key={i} size="small" style={{ marginBottom: 8 }}>
                  <div>
                    <strong>相似度：</strong>
                    <Progress
                      percent={Math.round(source.score * 100)}
                      size="small"
                      format={percent => `${percent}%`}
                    />
                  </div>
                  <div>
                    <strong>来源：</strong>
                    <Tag>{source.metadata.source}</Tag>
                    {source.metadata.page && (
                      <Tag>第 {source.metadata.page} 页</Tag>
                    )}
                  </div>
                  <div>
                    <strong>内容：</strong>
                    <p>{source.content}</p>
                  </div>
                </Card>
              ))}
            </div>
          ))}
        </Panel>

        {/* 工具调用详情 */}
        <Panel header="工具调用详情" key="tools">
          {toolEvents.map((event, idx) => (
            <div key={idx}>
              {event.type === 'tool_start' && (
                <Tag color="blue">
                  调用 {event.data.tool_name}
                </Tag>
              )}
              {event.type === 'tool_end' && (
                <pre style={{ background: '#f5f5f5', padding: 8 }}>
                  {JSON.stringify(event.data.output, null, 2)}
                </pre>
              )}
              {event.type === 'tool_error' && (
                <Tag color="red">
                  {event.data.error}
                </Tag>
              )}
            </div>
          ))}
        </Panel>
      </Collapse>
    </div>
  )
}
```

### P2 验收标准

- ✅ 对话界面侧边栏显示"思考过程"面板
- ✅ 检索到的文档片段显示：内容、来源、相似度分数（百分比）
- ✅ 工具调用显示：工具名称、输入参数、原始返回值
- ✅ 面板可折叠，不影响正常聊天体验
- ✅ 支持复制文档片段内容

---

## 📊 数据库迁移

```python
# migrations/004_add_phase4_tables.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # 1. knowledge_bases 表
    op.create_table(
        'knowledge_bases',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('collection_name', sa.String(100), unique=True, nullable=False),
        sa.Column('chunk_size', sa.Integer(), default=500),
        sa.Column('chunk_overlap', sa.Integer(), default=50),
        sa.Column('hybrid_search_weights', postgresql.JSON(), default={"vector": 0.7, "bm25": 0.3}),
        sa.Column('top_k', sa.Integer(), default=3),
        sa.Column('ocr_enabled', sa.Boolean(), default=True),
        sa.Column('ocr_threshold', sa.Integer(), default=10),
        sa.Column('status', sa.String(20), default="active"),
        sa.Column('document_count', sa.Integer(), default=0),
        sa.Column('total_chunks', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_kb_tenant', 'knowledge_bases', ['tenant_id'])
    op.create_index('idx_kb_collection', 'knowledge_bases', ['collection_name'])

    # 2. documents 表
    op.create_table(
        'documents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('knowledge_base_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(20), nullable=False),
        sa.Column('file_size', sa.Integer()),
        sa.Column('file_path', sa.String(500)),
        sa.Column('chunk_count', sa.Integer(), default=0),
        sa.Column('upload_status', sa.String(20), default="processing"),
        sa.Column('ocr_used', sa.Boolean(), default=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_doc_kb', 'documents', ['knowledge_base_id'])
    op.create_index('idx_doc_status', 'documents', ['upload_status'])

    # 3. document_processing_tasks 表
    op.create_table(
        'document_processing_tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(20), default="pending"),
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('current_step', sa.String(100)),
        sa.Column('error_message', sa.Text()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_task_status', 'document_processing_tasks', ['status'])

    # 4. custom_tools 表
    op.create_table(
        'custom_tools',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(50)),
        sa.Column('api_config', postgresql.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('test_result', postgresql.JSON()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_custom_tool_tenant', 'custom_tools', ['tenant_id'])
    op.create_index('idx_custom_tool_active', 'custom_tools', ['is_active'])


def downgrade():
    op.drop_table('custom_tools')
    op.drop_table('document_processing_tasks')
    op.drop_table('documents')
    op.drop_table('knowledge_bases')
```

---

## 🔧 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| **后端** | FastAPI 0.104+ | 异步支持，BackgroundTasks |
| **数据库** | SQLite → PostgreSQL | 生产环境升级到 PostgreSQL |
| **向量库** | ChromaDB | 多租户 Collection 隔离 |
| **OCR** | Tesseract | 本地免费，支持中文 |
| **嵌入** | 智谱 embedding-3 | 兼容 OpenAI API |
| **检索** | LangChain EnsembleRetriever | Vector + BM25 |
| **加密** | cryptography.fernet | API Key 对称加密 |
| **前端** | React 18 + Ant Design | SSE 原生支持 |
| **通信** | SSE (Server-Sent Events) | 单向推送，轻量级 |

---

## 📅 实施时间线

### Week 1-2: P0 多租户 RAG

**Day 1-2: 基础设施**
- [ ] 数据库模型和迁移（004_add_phase4_tables.py）
- [ ] ChromaDB 多租户 Collection 命名规范
- [ ] 文件存储目录结构

**Day 3-4: 文档处理核心**
- [ ] DocumentTypeDetector（含 OCR 触发阈值）
- [ ] TesseractOCR 服务
- [ ] DocumentProcessor（异步处理）

**Day 5-7: 检索能力**
- [ ] HybridRetriever 实现
- [ ] 混合检索测试和调优
- [ ] 向量化服务优化

**Day 8-10: API 和前端**
- [ ] 知识库管理 API（上传、查询、删除）
- [ ] SSE 进度推送
- [ ] 前端文档上传页面
- [ ] 进度条组件

**Day 11-12: 测试和优化**
- [ ] 端到端集成测试
- [ ] 大文件处理测试
- [ ] OCR 准确率测试
- [ ] 性能优化

### Week 3: P1 自定义工具

**Day 1-3: 后端实现**
- [ ] CustomTool 数据模型
- [ ] EncryptionService（API Key 加密）
- [ ] DynamicToolFactory
- [ ] 工具测试 API

**Day 4-5: 前端实现**
- [ ] 工具构建器表单
- [ ] 工具列表和详情页
- [ ] 测试调用功能

**Day 6-7: 集成测试**
- [ ] Agent 调用自定义工具
- [ ] 错误处理测试
- [ ] 安全测试（API Key 加密验证）

### Week 4: P2 推理链可视化

**Day 1-3: 后端扩展**
- [ ] SSE 协议扩展（source 事件）
- [ ] RAGAgent 观察者模式改造
- [ ] 工具调用详情捕获

**Day 4-5: 前端实现**
- [ ] 思考过程面板组件
- [ ] 文档片段展示（含相似度）
- [ ] 工具调用详情展示

**Day 6-7: 测试和文档**
- [ ] 端到端测试
- [ ] 用户体验优化
- [ ] 用户文档更新

---

## ⚠️ 风险评估与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **Tesseract OCR 准确率低** | 中 | 高 | 预留 Azure/百度 OCR 接口，支持切换 |
| **ChromaDB 多租户性能** | 中 | 高 | 预先测试并发，考虑升级到 Qdrant/Weaviate |
| **大文件处理超时** | 低 | 中 | BackgroundTasks + 进度推送，无阻塞 |
| **API Key 泄露** | 低 | 高 | Fernet 加密，数据库审计日志 |
| **SSE 连接中断** | 中 | 低 | 前端自动重连，任务状态持久化 |
| **混合检索效果不佳** | 低 | 中 | 可配置权重，支持降级为纯向量 |

---

## 🎯 成功指标

### P0 指标
- 文档上传成功率 > 95%
- 平均处理时间 < 30 秒（10MB 文本 PDF）
- 混合检索准确率提升 > 15%（对比纯向量）
- OCR 识别准确率 > 85%（中文文档）

### P1 指标
- 自定义工具配置成功率 > 90%
- 工具调用成功率 > 95%
- API Key 加密验证通过

### P2 指标
- 推理链展示覆盖率 > 80%
- 用户满意度调研 > 4.0/5.0

---

## 📚 参考文档

### 内部文档
- [Phase 3 设计](./phase3-design.md)
- [开发规约](../CONVENTIONS.md)
- [API 文档](../api/endpoints.md)

### 外部资源
- [ChromaDB 多租户最佳实践](https://docs.trychroma.com/usage-guide)
- [Tesseract OCR 中文优化](https://github.com/tesseract-ocr/tessdoc)
- [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [SSE 协议标准](https://html.spec.whatwg.org/multipage/server-sent-events.html)

---

## 📝 附录

### A. ChromaDB 命名规范

**Collection 命名**: `tenant_{tenant_id}_kb_{kb_id}`

**示例**:
- `tenant_abc123_kb_kb001` - 租户 abc123 的第一个知识库
- `tenant_abc123_kb_kb002` - 租户 abc123 的第二个知识库

**优势**:
- 同一租户多知识库完全隔离
- 便于管理和调试
- 支持知识库级别的删除

### B. SSE 消息格式规范

**进度推送**:
```
event: progress
data: {"type": "progress", "value": 45, "msg": "正在向量化", "status": "processing"}
```

**完成通知**:
```
event: complete
data: {"type": "complete", "document_id": "xxx", "chunks": 150}
```

**错误通知**:
```
event: failed
data: {"type": "failed", "error": "OCR 识别失败"}
```

### C. OCR 触发阈值配置

**默认配置**:
```python
ocr_threshold = 10  # 每页少于 10 个字符触发 OCR
```

**调优建议**:
- 中文文档: 10-15 字
- 英文文档: 20-30 字
- 技术文档: 5-10 字（公式多）

---

**设计版本**: v1.0
**最后更新**: 2026-03-03
**审批状态**: ⏳ 待审批
