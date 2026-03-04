"""
知识库管理 API。

提供文档上传、知识库管理、进度查询等功能。
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, UploadFile, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from services.database import get_db, KnowledgeBase, Document, DocumentProcessingTask, Tenant
from services.document_processor import DocumentProcessor

from api.schemas.knowledge import (
    DocumentUploadResponse,
    TaskProgressResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    DocumentListResponse
)

logger = logging.getLogger(__name__)

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
    上传文档到知识库。

    Args:
        file: 上传的文件
        knowledge_base_id: 知识库 ID
        tenant_id: 租户 ID
        background_tasks: FastAPI 后台任务

    Returns:
        task_id: 任务 ID(立即返回)
    """
    # 验证知识库存在
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == knowledge_base_id,
        KnowledgeBase.tenant_id == tenant_id
    ).first()

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 提交异步处理任务
    processor = DocumentProcessor(db)
    task_id = await processor.upload_document_async(
        file, knowledge_base_id, tenant_id, background_tasks
    )

    logger.info(f"文档 {file.filename} 上传成功,任务 ID: {task_id}")
    return DocumentUploadResponse(task_id=task_id)


@router.get("/tasks/{task_id}", response_model=TaskProgressResponse)
async def get_task_progress(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    查询任务进度(轮询方式)。

    Args:
        task_id: 任务 ID

    Returns:
        任务进度信息
    """
    task = db.query(DocumentProcessingTask).get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskProgressResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress,
        current_step=task.current_step or "",
        error_message=task.error_message
    )


@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str, db: Session = Depends(get_db)):
    """
    SSE 推送任务进度(推荐)。

    消息格式:
    ```
    event: progress
    data: {"type": "progress", "value": 45, "msg": "正在向量化", "status": "processing"}

    event: complete
    data: {"type": "complete", "document_id": "xxx", "chunks": 150}
    ```
    """
    async def event_stream():
        while True:
            # 重新查询获取最新状态
            db.expire_all()
            task = db.query(DocumentProcessingTask).get(task_id)

            if not task:
                yield f"event: error\ndata: {json.dumps({'msg': '任务不存在'}, ensure_ascii=False)}\n\n"
                break

            # 推送进度
            yield f"event: progress\ndata: {json.dumps({
                'type': 'progress',
                'value': task.progress,
                'msg': task.current_step or '',
                'status': task.status
            }, ensure_ascii=False)}\n\n"

            # 完成/失败
            if task.status == 'completed':
                doc = db.query(Document).get(task.document_id)
                yield f"event: complete\ndata: {json.dumps({
                    'type': 'complete',
                    'document_id': task.document_id,
                    'chunks': doc.chunk_count if doc else 0
                }, ensure_ascii=False)}\n\n"
                break

            elif task.status == 'failed':
                yield f"event: failed\ndata: {json.dumps({
                    'type': 'failed',
                    'error': task.error_message or '未知错误'
                }, ensure_ascii=False)}\n\n"
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


@router.post("/{tenant_id}/knowledge-bases", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    tenant_id: str,
    kb_data: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """创建知识库"""
    # 验证租户存在
    tenant = db.query(Tenant).get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 生成唯一 collection 名称
    import uuid
    collection_name = f"tenant_{tenant_id}_kb_{uuid.uuid4().hex[:8]}"

    kb = KnowledgeBase(
        tenant_id=tenant_id,
        name=kb_data.name,
        description=kb_data.description,
        collection_name=collection_name,
        chunk_size=kb_data.chunk_size,
        chunk_overlap=kb_data.chunk_overlap,
        ocr_enabled=kb_data.ocr_enabled,
        ocr_threshold=kb_data.ocr_threshold
    )

    db.add(kb)
    db.commit()
    db.refresh(kb)

    logger.info(f"知识库创建成功: {kb.name} (ID: {kb.id})")
    return kb


@router.get("/{tenant_id}/knowledge-bases", response_model=KnowledgeBaseListResponse)
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
        knowledge_bases=kbs
    )


@router.get("/knowledge-bases/{kb_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """列出知识库的所有文档"""
    docs = db.query(Document).filter(
        Document.knowledge_base_id == kb_id
    ).all()

    return DocumentListResponse(
        documents=docs,
        total=len(docs)
    )


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """获取知识库详情"""
    kb = db.query(KnowledgeBase).get(kb_id)

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    return kb


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """删除文档"""
    doc = db.query(Document).get(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 先删除关联的任务记录
    from services.database import DocumentProcessingTask
    tasks = db.query(DocumentProcessingTask).filter(
        DocumentProcessingTask.document_id == document_id
    ).all()
    for task in tasks:
        db.delete(task)
    logger.info(f"已删除 {len(tasks)} 个关联任务")

    # TODO: 从 ChromaDB 删除向量(后续实现)

    # 删除文件
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
        logger.info(f"文件已删除: {doc.file_path}")

    # 更新知识库统计
    kb = doc.knowledge_base
    kb.document_count = max(0, kb.document_count - 1)
    if doc.chunk_count:
        kb.total_chunks = max(0, kb.total_chunks - doc.chunk_count)
    kb.updated_at = datetime.now(timezone.utc)

    # 删除记录
    db.delete(doc)
    db.commit()

    logger.info(f"文档已删除: {doc.filename}")
    return {"message": "文档已删除", "document_id": document_id}


@router.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """删除知识库"""
    kb = db.query(KnowledgeBase).get(kb_id)

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    kb_name = kb.name

    # 先删除所有文档关联的处理任务
    from services.database import DocumentProcessingTask
    doc_ids = [doc.id for doc in kb.documents]
    if doc_ids:
        deleted_tasks = db.query(DocumentProcessingTask).filter(
            DocumentProcessingTask.document_id.in_(doc_ids)
        ).delete(synchronize_session=False)
        logger.info(f"已删除 {deleted_tasks} 个关联任务")

    # 删除所有文档文件
    for doc in kb.documents:
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                logger.warning(f"删除文件失败: {e}")

    # 删除知识库(级联删除文档)
    db.delete(kb)
    db.commit()

    logger.info(f"知识库已删除: {kb_name}")
    return {"message": "知识库已删除", "knowledge_base_id": kb_id}
