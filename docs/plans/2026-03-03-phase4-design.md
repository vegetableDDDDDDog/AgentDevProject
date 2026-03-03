# Phase 4 设计文档：从"功能"到"平台"（精简版）

> **项目名称**: Agent PaaS 平台 - Phase 4
> **设计日期**: 2026-03-03
> **设计者**: Claude + 用户协作
> **状态**: 待审批

---

## 📋 执行摘要

Phase 4 将把现有的 Agent PaaS 平台从"功能集合"升级为**企业级生产力平台**：

| 优先级 | 功能模块 | 核心价值 | 预计工期 |
|--------|----------|----------|----------|
| **P0** | 多租户 RAG 闭环 | 每个部门拥有自己的智能知识库 | 2-3 周 |
| **P1** | HTTP 自定义工具构建器 | 无代码接入企业内部系统 | 1-2 周 |
| **P2** | 推理链可视化 | Agent 决策过程透明可审计 | 1 周 |

**设计原则**：异步优先、租户隔离、可观测性、渐进增强

---

## 🔷 P0：多租户 RAG 闭环（含异步处理 + OCR）

### 核心目标

让每个租户（部门）能通过前端上传文档，自动构建专属向量库，并获得混合检索能力。

### 架构概览

```
前端上传 → 返回task_id → 后台异步处理 → SSE推送进度
                     ↓
        保存 → 类型检测 → OCR(可选) → 分块 → 向量化 → ChromaDB
```

**关键设计**：
- 上传立即返回 task_id（< 500ms）
- 异步处理进度通过 SSE 实时推送（0-100%）
- ChromaDB Collection 命名：`tenant_{id}_kb_{kb_id}`
- 支持文本/扫描件 PDF 自动检测和 OCR

### 数据模型

**KnowledgeBase**（知识库元数据）
- 核心字段：id, tenant_id, name, collection_name
- 配置：chunk_size, chunk_overlap, hybrid_search_weights, top_k
- OCR配置：ocr_enabled, ocr_threshold（每页少于N字触发OCR）
- 统计：document_count, total_chunks

**Document**（文档记录）
- 文件信息：filename, file_type, file_size, file_path
- 处理信息：chunk_count, upload_status, ocr_used
- 状态：processing → ready/failed

**DocumentProcessingTask**（异步任务）
- 进度追踪：progress(0-100), current_step, status
- 错误处理：error_message

### 核心服务设计

**1. 文档类型检测器（DocumentTypeDetector）**
- 支持格式：PDF/MD/Excel/TXT/图片
- PDF智能检测：采样前3页，平均字符数 < 阈值（默认10字）触发OCR
- 返回：type, needs_ocr, reason

**2. OCR服务（策略模式）**
- MVP：Tesseract本地OCR（免费，支持中文）
- 预留：Azure/百度OCR接口
- 配置：语言包（chi_sim+eng）

**3. 异步文档处理器（DocumentProcessor）**
- 流程：保存 → 类型检测 → OCR/解析 → 分块 → 向量化 → 存储
- 进度更新：每步更新数据库，SSE推送到前端
- 错误处理：异常时标记任务失败，记录error_message

**4. 混合检索器（HybridRetriever）**
- 组合：Vector检索（70%）+ BM25检索（30%）
- 实现：LangChain EnsembleRetriever
- 权重可配置

### API 设计

**POST /api/v1/knowledge/upload** - 上传文档
- 参数：file, knowledge_base_id, tenant_id
- 返回：task_id（立即返回，< 500ms）

**GET /api/v1/knowledge/tasks/{task_id}/stream** - SSE进度推送
- 事件类型：progress, complete, failed
- 推送频率：每0.5秒

**GET /api/v1/knowledge/{tenant_id}/collections** - 列出知识库

**DELETE /api/v1/knowledge/documents/{document_id}** - 删除文档

### 前端交互流程

1. 用户选择文件 → POST上传 → 获得task_id
2. 建立SSE连接 → 监听进度事件 → 更新进度条
3. 收到complete事件 → 显示成功提示 + 分块数

### P0 验收标准

**功能**
- 支持格式：PDF/MD/Excel/TXT/图片
- 自动检测扫描件并触发OCR（中文支持）
- 异步处理 + SSE实时进度推送
- 租户隔离：ChromaDB Collection命名 `tenant_{id}_kb_{id}`
- 混合检索优于纯向量检索

**性能**
- 上传响应 < 500ms
- 10MB文本PDF处理 < 30秒
- 10MB扫描件PDF（OCR）< 2分钟

---

## 🔷 P1：HTTP 自定义工具构建器

### 核心目标

让业务人员通过 UI 配置 HTTP API，自动转换为 Agent 可调用的工具。

### 设计思路

**数据模型（CustomTool）**
- 工具信息：name, description, category
- API配置（JSON）：base_url, method, headers, path_params, response_mapping
- 状态：is_active, test_result

**动态工具工厂（DynamicToolFactory）**
- 根据数据库配置构造LangChain StructuredTool
- 动态生成Pydantic Schema（路径参数 + Body参数）
- 执行时解密API Key、替换路径参数、提取响应字段

**API密钥加密（EncryptionService）**
- 使用cryptography.fernet对称加密
- 密钥从环境变量读取（ENCRYPTION_SECRET_KEY）
- 仅解密Authorization/X-API-Key字段

**前端工具构建器**
- 表单字段：名称、描述、API地址、方法、Headers(JSON)、路径参数、响应映射
- 提交后端自动加密API Key

### 验收标准

- 前端能通过表单配置HTTP API工具
- 支持路径参数替换（如`{issue_id}`）
- API Key加密存储
- Agent能正确调用工具并解析返回值

---

## 🔷 P2：推理链可视化

### 核心目标

在前端展示 Agent 的完整思考过程：检索文档片段 + 工具调用详情。

### 实现方式

**SSE协议扩展**
- 新增事件类型：source（检索片段）, retrieval_score（相似度）

**RAGAgent改造**
- 检索阶段：推送文档片段（内容前200字 + metadata + score）
- 生成阶段：流式推送token

**前端思考过程面板**
- 可折叠侧边栏
- 显示检索片段：相似度进度条、来源文件/页码、内容预览
- 显示工具调用：工具名称、输入、返回值

### 验收标准

- 侧边栏显示"思考过程"面板
- 检索片段显示：内容、来源、相似度分数
- 工具调用显示：名称、参数、返回值
- 面板可折叠，支持复制片段

---

## 🔧 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 后端 | FastAPI 0.104+ | 异步支持，BackgroundTasks |
| 数据库 | PostgreSQL | 生产环境 |
| 向量库 | ChromaDB | 多租户 Collection 隔离 |
| OCR | Tesseract | 本地免费，支持中文 |
| 嵌入 | 智谱 embedding-3 | 兼容 OpenAI API |
| 检索 | LangChain EnsembleRetriever | Vector + BM25 |
| 加密 | cryptography.fernet | API Key 对称加密 |
| 前端 | React 18 + Ant Design | SSE 原生支持 |

---

## 📅 实施计划

### Week 1-2: P0 多租户 RAG
- 数据库模型和迁移
- 文档处理核心（类型检测、OCR、异步处理）
- 混合检索器
- API和前端（上传、进度推送）
- 集成测试和性能优化

### Week 3: P1 自定义工具
- CustomTool数据模型
- API Key加密服务
- 动态工具工厂
- 前端工具构建器

### Week 4: P2 推理链可视化
- SSE协议扩展
- RAGAgent观察者改造
- 前端思考过程面板

---

## ⚠️ 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| Tesseract OCR准确率低 | 预留Azure/百度OCR接口 |
| ChromaDB多租户性能 | 预先测试并发，考虑升级Qdrant |
| API Key泄露 | Fernet加密 + 审计日志 |
| SSE连接中断 | 前端自动重连 + 状态持久化 |

---

## 🎯 成功指标

**P0**: 上传成功率>95%, 处理时间<30秒, 检索准确率提升>15%
**P1**: 工具配置成功率>90%, 调用成功率>95%
**P2**: 推理链展示覆盖率>80%

---

## 📚 参考资源

- [ChromaDB 多租户最佳实践](https://docs.trychroma.com/usage-guide)
- [Tesseract OCR 中文优化](https://github.com/tesseract-ocr/tessdoc)
- [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)

---

**设计版本**: v1.1 (精简版)
**最后更新**: 2026-03-03
**审批状态**: ⏳ 待审批
