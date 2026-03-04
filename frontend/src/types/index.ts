/**
 * TypeScript 类型定义
 */

// ============================================================================
// 认证相关类型
// ============================================================================

export interface User {
  id: string;
  email: string;
  role: string;
  tenant_id: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name?: string;
}

// ============================================================================
// 聊天相关类型
// ============================================================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokens_used?: number;
  created_at: string;
}

export interface ChatRequest {
  agent_type: string;
  message: string;
  session_id?: string;
  config?: Record<string, any>;
}

export interface ChatResponse {
  session_id: string;
  agent_type: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface SSEMessage {
  event: 'thought' | 'message' | 'error' | 'done';
  data: string;
}

// ============================================================================
// SSE 事件类型
// ============================================================================

export interface SSEThoughtEvent {
  event: 'thought';
  data: {
    content: string;
    step: number;
  };
}

export interface SSEMessageEvent {
  event: 'message';
  data: {
    type: string;
    content: string;
  };
}

export interface SSEErrorEvent {
  event: 'error';
  data: {
    message: string;
    code: string;
  };
}

export interface SSEDoneEvent {
  event: 'done';
  data: {
    session_id: string;
    tokens_used: number;
    execution_time_ms: number;
  };
}

// ============================================================================
// API 错误类型
// ============================================================================

export interface APIError {
  error: string;
  message: string;
  code?: string;
  details?: any;
}

// ============================================================================
// Agent 类型
// ============================================================================

export interface AgentInfo {
  name: string;
  role: string;
  capabilities: string[];
}

// ============================================================================
// 工具调用事件类型 (Phase 3)
// ============================================================================

export interface ToolEvent {
  type: 'tool_start' | 'tool_end' | 'tool_error';
  tool_name: string;
  input?: any;
  output?: any;
  error?: string;
  timestamp: number;
}

export interface SSEToolEvent {
  event: 'tool_start' | 'tool_end' | 'tool_error';
  data: {
    tool_name: string;
    input?: any;
    output?: any;
    error?: string;
    timestamp: number;
  };
}

// ============================================================================
// 知识库相关类型 (Phase 4)
// ============================================================================

export interface KnowledgeBase {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  collection_name: string;
  chunk_size: number;
  chunk_overlap: number;
  ocr_enabled: boolean;
  ocr_threshold: number;
  document_count: number;
  total_chunks: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeBaseCreate {
  name: string;
  description?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  ocr_enabled?: boolean;
  ocr_threshold?: number;
}

export interface Document {
  id: string;
  knowledge_base_id: string;
  tenant_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  upload_status: string;
  ocr_used: boolean | null;
  uploaded_at: string;
  processed_at: string | null;
  file_path?: string;
}

export interface TaskProgress {
  task_id: string;
  status: string;
  progress: number;
  current_step: string;
  error_message?: string;
}

export interface DocumentUploadResponse {
  task_id: string;
}

// SSE 进度事件类型
export interface SSEProgressEvent {
  type: 'progress';
  value: number;
  msg: string;
  status: string;
}

export interface SSECompleteEvent {
  type: 'complete';
  document_id: string;
  chunks: number;
}

export interface SSEFailedEvent {
  type: 'failed';
  error: string;
}

export interface SSEErrorEvent {
  msg: string;
}
