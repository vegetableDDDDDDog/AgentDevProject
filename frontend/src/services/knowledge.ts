/**
 * 知识库 API 服务
 */

import apiClient from './api';
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
  Document,
  TaskProgress,
  DocumentUploadResponse,
} from '../types';

/**
 * 上传文档到知识库
 */
export const uploadDocument = async (
  file: File,
  knowledgeBaseId: string,
  tenantId: string
): Promise<DocumentUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<DocumentUploadResponse>(
    '/knowledge/upload',
    formData,
    {
      params: {
        knowledge_base_id: knowledgeBaseId,
        tenant_id: tenantId,
      },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
};

/**
 * 查询任务进度（轮询方式）
 */
export const getTaskProgress = async (taskId: string): Promise<TaskProgress> => {
  const response = await apiClient.get<TaskProgress>(
    `/knowledge/tasks/${taskId}`
  );

  return response.data;
};

/**
 * 获取 SSE 进度流 URL
 */
export const getTaskProgressStreamUrl = (taskId: string): string => {
  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
  return `${baseUrl}/knowledge/tasks/${taskId}/stream`;
};

/**
 * 创建知识库
 */
export const createKnowledgeBase = async (
  tenantId: string,
  data: KnowledgeBaseCreate
): Promise<KnowledgeBase> => {
  const response = await apiClient.post<KnowledgeBase>(
    `/knowledge/${tenantId}/knowledge-bases`,
    data
  );

  return response.data;
};

/**
 * 列出租户的所有知识库
 */
export const listKnowledgeBases = async (
  tenantId: string
): Promise<KnowledgeBase[]> => {
  const response = await apiClient.get<{ knowledge_bases: KnowledgeBase[] }>(
    `/knowledge/${tenantId}/knowledge-bases`
  );

  return response.data.knowledge_bases;
};

/**
 * 获取知识库详情
 */
export const getKnowledgeBase = async (
  kbId: string
): Promise<KnowledgeBase> => {
  const response = await apiClient.get<KnowledgeBase>(
    `/knowledge/knowledge-bases/${kbId}`
  );

  return response.data;
};

/**
 * 列出知识库的所有文档
 */
export const listDocuments = async (
  kbId: string
): Promise<{ documents: Document[]; total: number }> => {
  const response = await apiClient.get<{ documents: Document[]; total: number }>(
    `/knowledge/knowledge-bases/${kbId}/documents`
  );

  return response.data;
};

/**
 * 删除文档
 */
export const deleteDocument = async (
  documentId: string
): Promise<{ message: string; document_id: string }> => {
  const response = await apiClient.delete<{
    message: string;
    document_id: string;
  }>(`/knowledge/documents/${documentId}`);

  return response.data;
};

/**
 * 删除知识库
 */
export const deleteKnowledgeBase = async (
  kbId: string
): Promise<{ message: string; knowledge_base_id: string }> => {
  const response = await apiClient.delete<{
    message: string;
    knowledge_base_id: string;
  }>(`/knowledge/knowledge-bases/${kbId}`);

  return response.data;
};
