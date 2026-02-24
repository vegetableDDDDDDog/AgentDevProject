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
