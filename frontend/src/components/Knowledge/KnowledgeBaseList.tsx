/**
 * 知识库列表组件
 *
 * 展示知识库列表，支持创建、删除知识库和查看文档列表
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  List,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Space,
  Popconfirm,
  message,
  Tag,
  Descriptions,
  Empty,
  Spin,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  FileTextOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import {
  listKnowledgeBases,
  createKnowledgeBase,
  deleteKnowledgeBase,
  listDocuments,
  deleteDocument,
} from '../../services/knowledge';
import type { KnowledgeBase, KnowledgeBaseCreate, Document } from '../../types';

interface KnowledgeBaseListProps {
  tenantId: string;
  onKnowledgeBaseSelect?: (kb: KnowledgeBase) => void;
  refreshTrigger?: number;
}

export const KnowledgeBaseList: React.FC<KnowledgeBaseListProps> = ({
  tenantId,
  onKnowledgeBaseSelect,
  refreshTrigger,
}) => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [documentsModalVisible, setDocumentsModalVisible] = useState(false);
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [form] = Form.useForm();

  /**
   * 加载知识库列表
   */
  const loadKnowledgeBases = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listKnowledgeBases(tenantId);
      setKnowledgeBases(data);
    } catch (error: any) {
      message.error(`加载知识库失败: ${error.message || '未知错误'}`);
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    loadKnowledgeBases();
  }, [loadKnowledgeBases, refreshTrigger]);

  /**
   * 创建知识库
   */
  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      const data: KnowledgeBaseCreate = {
        name: values.name,
        description: values.description,
        chunk_size: values.chunk_size,
        chunk_overlap: values.chunk_overlap,
        ocr_enabled: values.ocr_enabled,
        ocr_threshold: values.ocr_threshold,
      };

      await createKnowledgeBase(tenantId, data);
      message.success('知识库创建成功');
      setCreateModalVisible(false);
      form.resetFields();
      loadKnowledgeBases();
    } catch (error: any) {
      if (error.errorFields) {
        return; // 表单验证错误
      }
      message.error(`创建失败: ${error.message || '未知错误'}`);
    }
  };

  /**
   * 删除知识库
   */
  const handleDelete = async (kbId: string) => {
    try {
      await deleteKnowledgeBase(kbId);
      message.success('知识库已删除');
      loadKnowledgeBases();
    } catch (error: any) {
      message.error(`删除失败: ${error.message || '未知错误'}`);
    }
  };

  /**
   * 查看文档列表
   */
  const handleViewDocuments = async (kb: KnowledgeBase) => {
    setSelectedKb(kb);
    setDocumentsLoading(true);
    setDocumentsModalVisible(true);

    try {
      const { documents: docs } = await listDocuments(kb.id);
      setDocuments(docs);
    } catch (error: any) {
      message.error(`加载文档失败: ${error.message || '未知错误'}`);
    } finally {
      setDocumentsLoading(false);
    }
  };

  /**
   * 删除文档
   */
  const handleDeleteDocument = async (documentId: string) => {
    try {
      await deleteDocument(documentId);
      message.success('文档已删除');

      // 重新加载文档列表
      if (selectedKb) {
        const { documents: docs } = await listDocuments(selectedKb.id);
        setDocuments(docs);
      }

      // 刷新知识库列表以更新统计数字
      await loadKnowledgeBases();
    } catch (error: any) {
      message.error(`删除失败: ${error.message || '未知错误'}`);
    }
  };

  /**
   * 选择知识库
   */
  const handleSelect = (kb: KnowledgeBase) => {
    setSelectedKb(kb);
    onKnowledgeBaseSelect?.(kb);
  };

  return (
    <>
      <Card
        title="知识库列表"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            创建知识库
          </Button>
        }
      >
        <Spin spinning={loading}>
          {knowledgeBases.length === 0 ? (
            <Empty description="暂无知识库，请先创建" />
          ) : (
            <List
              dataSource={knowledgeBases}
              renderItem={(kb) => (
                <List.Item
                  style={{ cursor: 'pointer', transition: 'background-color 0.2s' }}
                  onClick={() => handleSelect(kb)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f5f5f5';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                  actions={[
                    <Button
                      key="view"
                      type="link"
                      icon={<FileTextOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleViewDocuments(kb);
                      }}
                    >
                      文档 ({kb.document_count})
                    </Button>,
                    <Popconfirm
                      key="delete"
                      title="确定要删除这个知识库吗？"
                      description="删除后无法恢复，所有文档也将被删除"
                      onConfirm={(e) => {
                        e?.stopPropagation();
                        handleDelete(kb.id);
                      }}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e) => e.stopPropagation()}
                      >
                        删除
                      </Button>
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<DatabaseOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                    title={
                      <Space>
                        <span>{kb.name}</span>
                        {kb.ocr_enabled && <Tag color="blue">OCR</Tag>}
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size="small">
                        <span>{kb.description || '无描述'}</span>
                        <span style={{ color: '#999', fontSize: 12 }}>
                          {kb.document_count} 个文档 · {kb.total_chunks} 个分块
                        </span>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Spin>
      </Card>

      {/* 创建知识库对话框 */}
      <Modal
        title="创建知识库"
        open={createModalVisible}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
        }}
        okText="创建"
        cancelText="取消"
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="知识库名称"
            rules={[{ required: true, message: '请输入知识库名称' }]}
          >
            <Input placeholder="例如: 技术文档库" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="知识库用途说明（可选）" />
          </Form.Item>

          <Form.Item label="分块配置">
            <Space.Compact style={{ width: '100%' }}>
              <Form.Item
                name="chunk_size"
                noStyle
                initialValue={500}
                rules={[{ required: true, message: '请输入分块大小' }]}
              >
                <InputNumber
                  style={{ width: '50%' }}
                  placeholder="分块大小"
                  min={100}
                  max={2000}
                  addonAfter="字符"
                />
              </Form.Item>
              <Form.Item
                name="chunk_overlap"
                noStyle
                initialValue={50}
                rules={[{ required: true, message: '请输入重叠大小' }]}
              >
                <InputNumber
                  style={{ width: '50%' }}
                  placeholder="重叠大小"
                  min={0}
                  max={500}
                  addonAfter="字符"
                />
              </Form.Item>
            </Space.Compact>
          </Form.Item>

          <Form.Item label="OCR 配置">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Form.Item name="ocr_enabled" noStyle valuePropName="checked" initialValue={true}>
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
              <Form.Item
                name="ocr_threshold"
                noStyle
                initialValue={10}
                rules={[{ required: true, message: '请输入OCR阈值' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="OCR触发阈值"
                  min={1}
                  max={100}
                  addonAfter="字符/页"
                />
              </Form.Item>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 文档列表对话框 */}
      <Modal
        title={`文档列表 - ${selectedKb?.name || ''}`}
        open={documentsModalVisible}
        onCancel={() => {
          setDocumentsModalVisible(false);
          setSelectedKb(null);
          setDocuments([]);
        }}
        footer={null}
        width={800}
      >
        <Spin spinning={documentsLoading}>
          {documents.length === 0 ? (
            <Empty description="暂无文档" />
          ) : (
            <List
              dataSource={documents}
              renderItem={(doc) => (
                <List.Item
                  actions={[
                    <Popconfirm
                      key="delete"
                      title="确定要删除这个文档吗？"
                      onConfirm={() => handleDeleteDocument(doc.id)}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button danger icon={<DeleteOutlined />}>
                        删除
                      </Button>
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<FileTextOutlined style={{ fontSize: 20 }} />}
                    title={doc.filename}
                    description={
                      <Descriptions size="small" column={2}>
                        <Descriptions.Item label="类型">{doc.file_type}</Descriptions.Item>
                        <Descriptions.Item label="大小">
                          {(doc.file_size / 1024).toFixed(2)} KB
                        </Descriptions.Item>
                        <Descriptions.Item label="分块数">{doc.chunk_count}</Descriptions.Item>
                        <Descriptions.Item label="OCR">
                          {doc.ocr_used ? <Tag color="blue">是</Tag> : <Tag>否</Tag>}
                        </Descriptions.Item>
                        <Descriptions.Item label="状态">
                          <Tag
                            color={
                              doc.upload_status === 'completed'
                                ? 'success'
                                : doc.upload_status === 'failed'
                                ? 'error'
                                : 'processing'
                            }
                          >
                            {doc.upload_status === 'completed'
                              ? '已完成'
                              : doc.upload_status === 'failed'
                              ? '失败'
                              : '处理中'}
                          </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="上传时间">
                          {new Date(doc.uploaded_at).toLocaleString()}
                        </Descriptions.Item>
                      </Descriptions>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Spin>
      </Modal>
    </>
  );
};
