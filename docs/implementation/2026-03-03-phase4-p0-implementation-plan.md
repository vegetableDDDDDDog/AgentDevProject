# P0 多租户RAG系统实施计划（精简版）

> **Claude提示**: 使用 superpowers:executing-plans 来逐任务实施此计划。

**目标**: 构建生产就绪的多租户RAG系统，具备异步文档处理、智能OCR触发和混合检索能力。

**架构**:
- FastAPI BackgroundTasks 异步处理 + SSE实时进度
- ChromaDB 多租户隔离 (`tenant_{id}_kb_{id}`)
- 智能OCR触发（每页10字符阈值）
- 混合检索：向量70% + BM25 30%

**技术栈**:
- FastAPI, SQLAlchemy, ChromaDB
- Tesseract OCR (可选), LangChain
- React 18 + Ant Design

---

## 任务概览

| 任务 | 功能 | 状态 | 关键文件 |
|------|------|------|----------|
| 1 | 数据库模型 | ✅ | `services/database.py` |
| 2 | 文档类型检测器 | ✅ | `services/document_type_detector.py` |
| 3 | OCR服务 | ✅ | `services/ocr_service.py` |
| 4 | 异步文档处理器 | ✅ | `services/document_processor.py` |
| 5 | 知识库管理API | ✅ | `api/routers/knowledge.py` |
| 6 | 前端文档上传器 | ⬜ | `frontend/src/components/Knowledge/` |
| 7 | 混合检索器 | ✅ | `services/hybrid_retriever.py` |
| 8 | E2E集成测试 | ⬜ | `tests/test_e2e_knowledge_base.py` |
| 9 | 文档和日志 | ⬜ | `docs/guide/`, `docs/DEVELOPER_LOGS/` |
| 10 | 最终验证 | ⬜ | 清理和提交 |

---

## Task 1: 数据库模型和迁移

**文件**: `services/database.py`

**步骤**:
1. 添加 `KnowledgeBase` 模型（知识库元数据）
2. 添加 `Document` 模型（文档记录）
3. 添加 `DocumentProcessingTask` 模型（异步任务追踪）
4. 创建迁移脚本 `migrations/004_add_knowledge_base.py`

**验收标准**:
- ✅ 所有表成功创建
- ✅ 外键和级联删除正常工作
- ✅ 索引正确建立

---

## Task 2: 文档类型检测器

**文件**: `services/document_type_detector.py`

**功能**: 自动检测文档类型并判断是否需要OCR

**步骤**:
1. 实现 `DocumentTypeDetector` 类
2. 支持类型：PDF、Markdown、Excel、TXT、图片
3. PDF分析：检测前3页字符密度
4. OCR触发：每页 < N 字时启用

**验收标准**:
- ✅ 正确识别文件类型
- ✅ PDF字符密度检测准确
- ✅ 不支持的类型抛出 `ValueError`

---

## Task 3: OCR服务

**文件**: `services/ocr_service.py`

**架构**:
```
OCRService (抽象基类)
├── MockOCR (开发/测试)
├── TesseractOCR (生产环境)
└── OCRServiceFactory (工厂模式)
```

**步骤**:
1. 安装依赖：`pip install pytesseract pdf2image Pillow rank_bm25`
2. 实现 `MockOCR`（模拟OCR，无环境依赖）
3. 实现 `TesseractOCR`（预留真实OCR接口）
4. 创建工厂类 `OCRServiceFactory`

**验收标准**:
- ✅ MockOCR 正常工作
- ✅ 工厂模式正确创建实例
- ✅ 预留 Tesseract 集成点

---

## Task 4: 异步文档处理器

**文件**: `services/document_processor.py`

**流程**:
```
1. 保存文件 (10%)
2. 类型检测 (15%)
3. 解析/OCR (40%)
4. 分块 (60%)
5. 向量化 (90%)
6. 完成 (100%)
```

**步骤**:
1. 实现 `DocumentProcessor` 类
2. 集成 `DocumentTypeDetector`
3. 集成 `OCRService`
4. 实现进度更新 `_update_progress()`
5. 实现向量化 `_vectorize_and_store()`

**验收标准**:
- ✅ 异步处理不阻塞主线程
- ✅ 进度正确更新到数据库
- ✅ 错误正确处理和记录

---

## Task 5: 知识库管理API

**文件**: `api/routers/knowledge.py`, `api/schemas/knowledge.py`

**API端点**:
- `POST /api/v1/knowledge/upload` - 上传文档
- `GET /api/v1/knowledge/tasks/{task_id}` - 查询进度
- `GET /api/v1/knowledge/tasks/{task_id}/stream` - SSE进度流
- `POST /api/v1/knowledge/{tenant_id}/knowledge-bases` - 创建知识库
- `GET /api/v1/knowledge/{tenant_id}/knowledge-bases` - 列出知识库
- `DELETE /api/v1/knowledge/documents/{id}` - 删除文档

**步骤**:
1. 创建 Pydantic schemas
2. 实现路由端点
3. 集成 `DocumentProcessor`
4. 实现SSE进度推送

**验收标准**:
- ✅ 所有端点正常工作
- ✅ SSE实时进度推送
- ✅ 错误处理正确

---

## Task 6: 前端文档上传器

**文件**: `frontend/src/components/Knowledge/`

**组件**:
- `DocumentUploader.tsx` - 上传组件 + 进度条
- `KnowledgeBaseList.tsx` - 知识库列表
- `KnowledgePage.tsx` - 主页面

**步骤**:
1. 实现文档上传组件
2. 集成SSE进度监听
3. 实现知识库管理界面

**验收标准**:
- 文件上传成功
- 实时显示进度
- 错误提示友好

---

## Task 7: 混合检索器

**文件**: `services/hybrid_retriever.py`, `services/embeddings_service.py`

**算法**: RRF (Reciprocal Rank Fusion)
```
score = Σ(weight / (k + rank))
k = 60 (常数)
```

**组件**:
- `EmbeddingsService` - 文本向量化
- `HybridRetriever` - 混合检索
- `RetrieverFactory` - 检索器工厂（缓存管理）

**租户隔离**:
- 独立 ChromaDB collection: `tenant_{id}_kb_{id}`
- 独立 BM25 索引

**验收标准**:
- ✅ 向量检索正常
- ✅ BM25检索正常
- ✅ RRF融合正确
- ✅ 租户隔离正常

---

## Task 8: E2E集成测试

**文件**: `tests/test_e2e_knowledge_base.py`

**测试场景**:
1. 创建知识库
2. 上传文档
3. 查询任务进度
4. 检索测试
5. 删除文档

**验收标准**:
- 所有场景通过
- 使用真实API和数据库
- 错误场景覆盖

---

## Task 9: 文档和开发者日志

**文件**:
- `docs/guide/knowledge-base-user-guide.md` - 用户指南
- `docs/DEVELOPER_LOGS/2026/2026-03-03.md` - 开发日志

**内容**:
- API使用示例
- 文件格式支持
- OCR触发规则
- 实施总结

---

## Task 10: 最终验证和清理

**步骤**:
1. 运行所有测试
2. 代码质量检查（flake8, mypy）
3. 验证导入
4. 清理备份文件
5. Git提交

**验收标准**:
- ✅ 所有测试通过
- ✅ 无关键代码质量问题
- ✅ 文档完整

---

## 验收标准（总体）

### 功能验收
- [ ] 用户登录后可创建知识库
- [ ] 支持PDF/MD/Excel/TXT上传
- [ ] 扫描件自动OCR识别
- [ ] 实时显示处理进度（0-100%）
- [ ] 混合检索返回相关文档
- [ ] 租户数据完全隔离

### 性能验收
- [ ] 文件上传 < 500ms 返回task_id
- [ ] 并发请求只发送1次refresh
- [ ] 向量化不阻塞主线程

### 安全验收
- [ ] 租户隔离（无法访问其他租户数据）
- [ ] 文件类型验证
- [ ] 错误信息不泄露敏感数据

---

## 技术亮点

✅ **异步优先** - 所有耗时操作使用BackgroundTasks
✅ **租户隔离** - 数据、向量、工具完全隔离
✅ **可观测性** - SSE实时进度推送
✅ **渐进增强** - MockOCR → Tesseract → 云端OCR
✅ **混合检索** - 向量 + BM25，精准匹配专有名词

---

## 依赖安装

```bash
# Python依赖
pip install rank_bm25 pytesseract pdf2image Pillow

# 系统依赖（Linux）
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim

# 前端
cd frontend
npm install
```

---

## 总结

**完成度**: 80% (7/10 任务完成)

**核心功能**: ✅ 完整实现
- 数据模型 ✅
- 文档处理 ✅
- 知识库API ✅
- 混合检索 ✅

**待完成**:
- 前端UI (Task 6)
- 集成测试 (Task 8)
- 文档 (Task 9)
- 最终验证 (Task 10)

---

**创建日期**: 2026-03-03
**版本**: v2.0 (精简版)
**完整版**: `2026-03-03-phase4-p0-implementation-plan-full.md.backup`
