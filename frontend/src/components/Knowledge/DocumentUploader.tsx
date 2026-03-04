/**
 * 文档上传组件
 *
 * 支持文件上传、实时进度显示（SSE）和错误提示
 */

import React, { useState, useCallback, useRef } from 'react';
import { Upload, message, Progress, Button, Card, Space } from 'antd';
import { InboxOutlined, CloudUploadOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { uploadDocument, getTaskProgressStreamUrl } from '../../services/knowledge';
import type { SSEProgressEvent, SSECompleteEvent, SSEFailedEvent } from '../../types';

const { Dragger } = Upload;

interface DocumentUploaderProps {
  knowledgeBaseId: string;
  tenantId: string;
  onUploadSuccess?: () => void;
}

interface UploadTask {
  fileId: string;
  filename: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  message: string;
  error?: string;
}

export const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  knowledgeBaseId,
  tenantId,
  onUploadSuccess,
}) => {
  const [uploadTasks, setUploadTasks] = useState<Map<string, UploadTask>>(new Map());
  const eventSourcesRef = useRef<Map<string, EventSource>>(new Map());

  /**
   * 处理文件上传
   */
  const handleUpload = useCallback(async (file: File) => {
    const fileId = `${Date.now()}-${file.name}`;

    // 添加任务到列表
    setUploadTasks((prev) => {
      const next = new Map(prev);
      next.set(fileId, {
        fileId,
        filename: file.name,
        progress: 0,
        status: 'uploading',
        message: '正在上传...',
      });
      return next;
    });

    try {
      // 上传文件
      const { task_id } = await uploadDocument(file, knowledgeBaseId, tenantId);

      // 更新为处理中
      setUploadTasks((prev) => {
        const next = new Map(prev);
        const task = next.get(fileId);
        if (task) {
          next.set(fileId, {
            ...task,
            status: 'processing',
            message: '正在处理文档...',
          });
        }
        return next;
      });

      // 连接 SSE 进度流
      connectToProgressStream(fileId, task_id);
    } catch (error: any) {
      setUploadTasks((prev) => {
        const next = new Map(prev);
        const task = next.get(fileId);
        if (task) {
          next.set(fileId, {
            ...task,
            status: 'failed',
            message: '上传失败',
            error: error.message || '未知错误',
          });
        }
        return next;
      });
      message.error(`上传失败: ${error.message || '未知错误'}`);
    }

    return false; // 阻止 antd 默认上传行为
  }, [knowledgeBaseId, tenantId]);

  /**
   * 连接 SSE 进度流
   */
  const connectToProgressStream = useCallback((fileId: string, taskId: string) => {
    const streamUrl = getTaskProgressStreamUrl(taskId);
    const eventSource = new EventSource(streamUrl);

    eventSourcesRef.current.set(fileId, eventSource);

    // 监听进度事件
    eventSource.addEventListener('progress', (e: MessageEvent) => {
      try {
        const data: SSEProgressEvent = JSON.parse(e.data);
        setUploadTasks((prev) => {
          const next = new Map(prev);
          const task = next.get(fileId);
          if (task) {
            next.set(fileId, {
              ...task,
              progress: data.value,
              message: data.msg,
            });
          }
          return next;
        });
      } catch (error) {
        console.error('解析进度事件失败:', error);
      }
    });

    // 监听完成事件
    eventSource.addEventListener('complete', (e: MessageEvent) => {
      try {
        const data: SSECompleteEvent = JSON.parse(e.data);
        setUploadTasks((prev) => {
          const next = new Map(prev);
          const task = next.get(fileId);
          if (task) {
            next.set(fileId, {
              ...task,
              status: 'completed',
              progress: 100,
              message: `处理完成 (${data.chunks} 个分块)`,
            });
          }
          return next;
        });

        message.success(`${data.chunks > 0 ? '文档处理成功' : '文档处理完成'}`);
        onUploadSuccess?.();

        // 关闭连接
        eventSource.close();
        eventSourcesRef.current.delete(fileId);

        // 3 秒后移除任务
        setTimeout(() => {
          setUploadTasks((prev) => {
            const next = new Map(prev);
            next.delete(fileId);
            return next;
          });
        }, 3000);
      } catch (error) {
        console.error('解析完成事件失败:', error);
      }
    });

    // 监听失败事件
    eventSource.addEventListener('failed', (e: MessageEvent) => {
      try {
        const data: SSEFailedEvent = JSON.parse(e.data);
        setUploadTasks((prev) => {
          const next = new Map(prev);
          const task = next.get(fileId);
          if (task) {
            next.set(fileId, {
              ...task,
              status: 'failed',
              message: '处理失败',
              error: data.error,
            });
          }
          return next;
        });

        message.error(`处理失败: ${data.error}`);

        // 关闭连接
        eventSource.close();
        eventSourcesRef.current.delete(fileId);
      } catch (error) {
        console.error('解析失败事件失败:', error);
      }
    });

    // 监听错误事件
    eventSource.addEventListener('error', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        message.error(`错误: ${data.msg}`);
      } catch (error) {
        message.error('连接进度流失败');
      }

      // 关闭连接
      eventSource.close();
      eventSourcesRef.current.delete(fileId);
    });

    // 连接错误
    eventSource.onerror = () => {
      message.error('进度连接中断');
      eventSource.close();
      eventSourcesRef.current.delete(fileId);
    };
  }, [onUploadSuccess]);

  /**
   * 组件卸载时关闭所有 SSE 连接
   */
  React.useEffect(() => {
    return () => {
      eventSourcesRef.current.forEach((es) => es.close());
      eventSourcesRef.current.clear();
    };
  }, []);

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    accept: '.pdf,.md,.txt,.xlsx,.xls,.png,.jpg,.jpeg',
    beforeUpload: handleUpload,
    showUploadList: false,
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card title="上传文档" bordered={false}>
        <Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持 PDF、Markdown、Excel、TXT、图片格式
          </p>
        </Dragger>
      </Card>

      {/* 上传任务列表 */}
      {Array.from(uploadTasks.values()).map((task) => (
        <Card
          key={task.fileId}
          size="small"
          title={task.filename}
          extra={
            task.status === 'completed' ? (
              <span style={{ color: '#52c41a' }}>✓ 完成</span>
            ) : task.status === 'failed' ? (
              <span style={{ color: '#ff4d4f' }}>✗ 失败</span>
            ) : null
          }
        >
          <Progress
            percent={task.progress}
            status={
              task.status === 'failed'
                ? 'exception'
                : task.status === 'completed'
                ? 'success'
                : 'active'
            }
          />
          <p style={{ marginTop: 8, color: '#666' }}>{task.message}</p>
          {task.error && (
            <p style={{ marginTop: 4, color: '#ff4d4f', fontSize: 12 }}>
              错误: {task.error}
            </p>
          )}
        </Card>
      ))}
    </Space>
  );
};
