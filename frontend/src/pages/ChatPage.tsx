/**
 * 聊天页面
 *
 * 提供对话界面，支持 SSE 流式输出和工具调用状态显示。
 */

import React, { useState, useRef, useEffect } from 'react';
import { ChatBubble } from '../components/Chat/ChatBubble';
import { ChatInput } from '../components/Chat/ChatInput';
import { ToolEventList } from '../components/Tools/ToolEventList';
import { streamChat } from '../services/chat';
import type { ChatMessage, ToolEvent } from '../types';

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [agentType, setAgentType] = useState('llm_chat');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (message: string) => {
    // 清空之前的工具事件
    setToolEvents([]);

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // 创建临时 AI 消息用于流式显示
    const aiMessageId = (Date.now() + 1).toString();
    const aiMessage: ChatMessage = {
      id: aiMessageId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, aiMessage]);

    try {
      let fullResponse = '';

      await streamChat(
        agentType,
        message,
        sessionId,
        {
          onMessage: (content) => {
            // 实时更新 AI 消息
            fullResponse += content;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, content: fullResponse }
                  : msg
              )
            );
          },
          onThought: (thought) => {
            console.log('思考过程:', thought);
          },
          onToolEvent: (event) => {
            // 处理工具事件
            console.log('工具事件:', event);
            setToolEvents((prev) => [...prev, event]);
          },
          onComplete: (data) => {
            console.log('完成:', data);
            setSessionId(data.session_id);

            // 更新最终消息
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      tokens_used: data.tokens_used,
                    }
                  : msg
              )
            );
          },
          onError: (error) => {
            console.error('错误:', error);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, content: `错误: ${error}` }
                  : msg
              )
            );
          },
        }
      );
    } catch (err: any) {
      console.error('发送消息失败:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#fff',
      }}
    >
      {/* Agent 选择器 */}
      <div
        style={{
          padding: '16px 24px',
          borderBottom: '1px solid #e0e0e0',
        }}
      >
        <select
          value={agentType}
          onChange={(e) => setAgentType(e.target.value)}
          disabled={isLoading}
          style={{
            padding: '8px 12px',
            fontSize: '14px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            backgroundColor: '#fff',
          }}
        >
          <option value="llm_chat">LLM 聊天 (真实 AI)</option>
          <option value="tool_using">工具使用 Agent (Phase 3)</option>
          <option value="mock_chat_agent">模拟聊天 (测试)</option>
          <option value="echo_agent">回声 Agent (测试)</option>
        </select>
      </div>

      {/* 消息列表 */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px',
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              marginTop: '100px',
              color: '#999',
            }}
          >
            <div style={{ fontSize: '24px', marginBottom: '16px' }}>💬</div>
            <div>开始对话吧！</div>
          </div>
        ) : (
          messages.map((message) => (
            <React.Fragment key={message.id}>
              <ChatBubble message={message} />
              {/* 在最后一条 AI 消息后显示工具事件 */}
              {message.role === 'assistant' &&
                message === messages[messages.length - 1] &&
                toolEvents.length > 0 && (
                  <ToolEventList events={toolEvents} />
                )}
            </React.Fragment>
          ))
        )}
        {isLoading && (
          <div style={{ textAlign: 'center', color: '#999', padding: '12px' }}>
            正在输入...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div
        style={{
          padding: '16px 24px',
          borderTop: '1px solid #e0e0e0',
        }}
      >
        <ChatInput onSend={handleSend} disabled={isLoading} />
      </div>
    </div>
  );
};
