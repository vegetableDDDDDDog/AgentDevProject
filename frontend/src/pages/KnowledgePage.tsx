/**
 * 知识库管理页面
 *
 * 提供知识库创建、文档上传、文档管理等完整功能
 */

import React, { useState, useCallback } from 'react';
import { Card, Row, Col, message, Alert } from 'antd';
import { getUserInfo } from '../utils/token';
import { KnowledgeBaseList } from '../components/Knowledge/KnowledgeBaseList';
import { DocumentUploader } from '../components/Knowledge/DocumentUploader';
import type { KnowledgeBase } from '../types';

export const KnowledgePage: React.FC = () => {
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  /**
   * 处理知识库选择
   */
  const handleKnowledgeBaseSelect = useCallback((kb: KnowledgeBase) => {
    setSelectedKb(kb);
  }, []);

  /**
   * 处理上传成功，刷新知识库列表
   */
  const handleUploadSuccess = useCallback(() => {
    setRefreshTrigger((prev) => prev + 1);
  }, []);

  const user = getUserInfo();

  if (!user) {
    return (
      <Alert
        message="未登录"
        description="请先登录后再访问知识库"
        type="error"
        showIcon
      />
    );
  }

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      <Row gutter={[24, 24]}>
        {/* 左侧：知识库列表 */}
        <Col xs={24} lg={12}>
          <KnowledgeBaseList
            tenantId={user.tenant_id}
            onKnowledgeBaseSelect={handleKnowledgeBaseSelect}
            refreshTrigger={refreshTrigger}
          />
        </Col>

        {/* 右侧：文档上传 */}
        <Col xs={24} lg={12}>
          {selectedKb ? (
            <Card title={`上传文档到 ${selectedKb.name}`}>
              <Alert
                message={
                  <div>
                    <p>
                      <strong>知识库ID:</strong> {selectedKb.id}
                    </p>
                    <p>
                      <strong>租户ID:</strong> {user.tenant_id}
                    </p>
                    <p style={{ marginTop: 8, color: '#666' }}>
                      支持的文件格式: PDF、Markdown、Excel、TXT、图片
                    </p>
                  </div>
                }
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <DocumentUploader
                knowledgeBaseId={selectedKb.id}
                tenantId={user.tenant_id}
                onUploadSuccess={handleUploadSuccess}
              />
            </Card>
          ) : (
            <Card>
              <Alert
                message="请先选择一个知识库"
                description="从左侧列表中选择一个知识库后，即可上传文档"
                type="info"
                showIcon
              />
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
};
