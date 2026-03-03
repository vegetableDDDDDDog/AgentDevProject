"""
知识库相关的 Pydantic 模型。
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    task_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_1234567890"
            }
        }


class TaskProgressResponse(BaseModel):
    """任务进度响应"""
    task_id: str
    status: str
    progress: int
    current_step: str
    error_message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_1234567890",
                "status": "processing",
                "progress": 45,
                "current_step": "正在分块...",
                "error_message": None
            }
        }


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str
    description: Optional[str] = None
    chunk_size: int = 500
    chunk_overlap: int = 50
    ocr_enabled: bool = True
    ocr_threshold: int = 10

    class Config:
        json_schema_extra = {
            "example": {
                "name": "技术文档库",
                "description": "存储API文档和技术规范",
                "chunk_size": 500,
                "chunk_overlap": 50,
                "ocr_enabled": True,
                "ocr_threshold": 10
            }
        }


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    collection_name: str
    chunk_size: int
    chunk_overlap: int
    ocr_enabled: bool
    ocr_threshold: int
    document_count: int
    total_chunks: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    knowledge_bases: List[KnowledgeBaseResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "knowledge_bases": [
                    {
                        "id": "kb_123",
                        "tenant_id": "tenant_456",
                        "name": "技术文档库",
                        "description": "API文档",
                        "collection_name": "tenant_456_kb_123",
                        "document_count": 5,
                        "total_chunks": 150
                    }
                ]
            }
        }


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str
    knowledge_base_id: str
    tenant_id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    upload_status: str
    ocr_used: Optional[bool]
    uploaded_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: List[DocumentResponse]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "documents": [],
                "total": 0
            }
        }
