/**
 * 聊天气泡组件
 *
 * 显示用户和 AI 的消息。
 */

import React from 'react';
import type { ChatMessage as ChatMessageType } from '../../types';

interface ChatBubbleProps {
  message: ChatMessageType;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return null; // 不显示系统消息
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '16px',
      }}
    >
      <div
        style={{
          maxWidth: '70%',
          padding: '12px 16px',
          borderRadius: '12px',
          backgroundColor: isUser ? '#1976d2' : '#f5f5f5',
          color: isUser ? '#fff' : '#000',
          wordBreak: 'break-word',
        }}
      >
        <div style={{ fontSize: '14px', lineHeight: '1.5' }}>
          {message.content}
        </div>
        {message.tokens_used && (
          <div
            style={{
              fontSize: '12px',
              opacity: 0.7,
              marginTop: '4px',
            }}
          >
            {message.tokens_used} tokens
          </div>
        )}
      </div>
    </div>
  );
};
