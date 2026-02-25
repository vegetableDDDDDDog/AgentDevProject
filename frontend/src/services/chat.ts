/**
 * 聊天服务
 *
 * 提供聊天、会话管理、SSE 流式输出等功能。
 */

import apiClient from './api';
import type {
  ChatRequest,
  ChatResponse,
  ChatMessage
} from '../types';

/**
 * 发送聊天消息（SSE 流式）
 *
 * @param agentType - Agent 类型
 * @param message - 用户消息
 * @param sessionId - 会话 ID（可选）
 * @param callbacks - 回调函数
 */
export const streamChat = async (
  agentType: string,
  message: string,
  sessionId: string | null,
  callbacks: {
    onMessage: (content: string) => void;
    onThought?: (thought: string) => void;
    onError?: (error: string) => void;
    onComplete?: (data: any) => void;
    onToolEvent?: (event: any) => void;  // 新增：工具事件回调
  }
): Promise<void> => {
  const { fetchEventSource } = await import('@microsoft/fetch-event-source');

  await fetchEventSource('/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      agent_type: agentType,
      message: message,
      session_id: sessionId || undefined,
    }),
    onmessage(msg: MessageEvent) {
      try {
        const data = JSON.parse(msg.data);

        switch (data.event) {
          case 'thought':
            if (callbacks.onThought) {
              callbacks.onThought(data.data.content);
            }
            break;

          case 'message':
            if (data.data.type === 'text') {
              callbacks.onMessage(data.data.content);
            }
            break;

          case 'error':
            if (callbacks.onError) {
              callbacks.onError(data.data.message);
            }
            break;

          case 'done':
            if (callbacks.onComplete) {
              callbacks.onComplete(data.data);
            }
            break;

          // 工具事件（Phase 3）
          case 'tool_start':
          case 'tool_end':
          case 'tool_error':
            if (callbacks.onToolEvent) {
              callbacks.onToolEvent({
                type: data.event,
                tool_name: data.data.tool_name,
                input: data.data.input,
                output: data.data.output,
                error: data.data.error,
                timestamp: data.data.timestamp || Date.now() / 1000,
              });
            }
            break;
        }
      } catch (e) {
        console.error('解析 SSE 消息失败:', e);
      }
    },
    onerror(err: Error) {
      if (callbacks.onError) {
        callbacks.onError(err.message);
      }
    },
  });
};

/**
 * 获取会话历史
 */
export const getChatHistory = async (
  sessionId: string
): Promise<ChatResponse> => {
  const response = await apiClient.get<ChatResponse>(
    `/chat/history?session_id=${sessionId}`
  );
  return response.data;
};

/**
 * 获取可用 Agents 列表
 */
export const listAgents = async (): Promise<string[]> => {
  // TODO: 实现获取 agents 列表的 API
  return ['llm_chat', 'mock_chat_agent', 'echo_agent'];
};
