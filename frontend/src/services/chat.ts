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

  // 获取 token 并检查是否需要刷新
  let token = localStorage.getItem('token');

  // 手动检查并刷新 token（因为 SSE 绕过了 Axios 拦截器）
  if (token) {
    const { isTokenExpiring } = await import('../utils/token');
    const { setToken, setExpiresAt } = await import('../utils/token');

    if (isTokenExpiring()) {
      console.log('🔄 Token 即将过期，主动刷新中...');
      try {
        // 直接使用 fetch 刷新（避免拦截器循环）
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await fetch('http://localhost:8000/api/v1/auth/refresh', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // 更新 token
        token = data.access_token;
        setToken(token);
        setExpiresAt(data.expires_in);

        console.log('✅ Token 刷新成功');
      } catch (error) {
        console.error('❌ Token 刷新失败:', error);
        // 如果刷新失败，继续使用旧 token（可能收到 401）
      }
    }
  }

  await fetchEventSource('http://localhost:8000/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify({
      agent_type: agentType,
      message: message,
      session_id: sessionId || undefined,
    }),
    onmessage(msg: MessageEvent) {
      try {
        // SSE 格式: msg.event = 事件类型, msg.data = JSON 数据
        const eventType = msg.event;
        const data = JSON.parse(msg.data);

        console.log('SSE 事件:', eventType, data);

        switch (eventType) {
          case 'thought':
            if (callbacks.onThought) {
              callbacks.onThought(data.content);
            }
            break;

          case 'message':
            if (data.type === 'text') {
              callbacks.onMessage(data.content);
            }
            break;

          case 'error':
            if (callbacks.onError) {
              callbacks.onError(data.message);
            }
            break;

          case 'done':
            if (callbacks.onComplete) {
              callbacks.onComplete(data);
            }
            break;

          // 工具事件（Phase 3）
          case 'tool_start':
          case 'tool_end':
          case 'tool_error':
            if (callbacks.onToolEvent) {
              callbacks.onToolEvent({
                type: eventType,
                tool_name: data.tool_name,
                input: data.input,
                output: data.output,
                error: data.error,
                timestamp: data.timestamp || Date.now() / 1000,
              });
            }
            break;
        }
      } catch (e) {
        console.error('解析 SSE 消息失败:', e, '原始消息:', msg);
      }
    },
    onerror(err: Error) {
      console.error('SSE 连接错误:', err);
      if (callbacks.onError) {
        callbacks.onError(`网络错误: ${err.message}`);
      }
    },
    async onopen(response) {
      console.log('SSE 连接已建立', response.status);

      // 处理 401 错误 - 自动刷新 token 并重试
      if (response.status === 401) {
        console.log('⚠️ SSE 收到 401，尝试刷新 token...');

        try {
          const refreshToken = localStorage.getItem('refresh_token');
          if (!refreshToken) {
            throw new Error('No refresh token available');
          }

          // 刷新 token
          const refreshResponse = await fetch('http://localhost:8000/api/v1/auth/refresh', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken })
          });

          if (!refreshResponse.ok) {
            throw new Error(`Token refresh failed: ${refreshResponse.status}`);
          }

          const data = await refreshResponse.json();

          // 更新 token
          const { setToken, setExpiresAt } = await import('../utils/token');
          setToken(data.access_token);
          setExpiresAt(data.expires_in);

          console.log('✅ Token 刷新成功，重新连接...');

          // 重新发送请求（递归调用）
          return await streamChat(agentType, message, sessionId, callbacks);
        } catch (error) {
          console.error('❌ Token 刷新失败:', error);
          const { forceLogout } = await import('./auth');
          forceLogout('session_expired');
          throw error;
        }
      }

      if (response.ok) {
        console.log('Content-Type:', response.headers.get('Content-Type'));
        return;
      }
      console.error('SSE 响应错误:', response.status, response.statusText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
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
