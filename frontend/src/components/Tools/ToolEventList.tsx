/**
 * 工具事件列表组件
 *
 * 显示 Agent 调用工具时的状态变化。
 */
import React from 'react';
import type { ToolEvent } from '../../types';

interface Props {
  events: ToolEvent[];
}

export const ToolEventList: React.FC<Props> = ({ events }) => {
  if (events.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        margin: '8px 0',
        padding: '12px',
        backgroundColor: '#f5f5f5',
        borderRadius: '8px',
        fontSize: '13px',
      }}
    >
      <div
        style={{
          marginBottom: '8px',
          fontWeight: 500,
          color: '#666',
          fontSize: '12px',
          textTransform: 'uppercase',
        }}
      >
        🔧 工具调用 ({events.length})
      </div>
      {events.map((event, index) => (
        <div
          key={index}
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '8px',
            marginBottom: index < events.length - 1 ? '8px' : 0,
            backgroundColor: '#fff',
            borderRadius: '4px',
            borderLeft: `3px solid ${
              event.type === 'tool_start'
                ? '#2196F3'
                : event.type === 'tool_end'
                ? '#4CAF50'
                : '#f44336'
            }`,
          }}
        >
          <span style={{ marginRight: '8px' }}>
            {event.type === 'tool_start' && '⚙️'}
            {event.type === 'tool_end' && '✅'}
            {event.type === 'tool_error' && '❌'}
          </span>
          <span
            style={{
              fontWeight: 500,
              marginRight: '8px',
              color: '#333',
            }}
          >
            {event.tool_name}
          </span>
          <span
            style={{
              color:
                event.type === 'tool_start'
                  ? '#2196F3'
                  : event.type === 'tool_end'
                  ? '#4CAF50'
                  : '#f44336',
            }}
          >
            {event.type === 'tool_start' && '正在调用...'}
            {event.type === 'tool_end' && '完成'}
            {event.type === 'tool_error' && '失败'}
          </span>
          {event.output && typeof event.output === 'string' && (
            <div
              style={{
                marginLeft: 'auto',
                color: '#666',
                fontSize: '12px',
                maxWidth: '200px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {event.output.length > 50
                ? event.output.substring(0, 50) + '...'
                : event.output}
            </div>
          )}
          {event.error && (
            <div
              style={{
                marginLeft: '8px',
                color: '#f44336',
                fontSize: '12px',
              }}
            >
              {event.error}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
