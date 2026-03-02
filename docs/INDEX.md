# 文档索引

> 本项目采用分阶段文档结构，按阶段组织设计文档和进度跟踪。

> **⚠️ 重要**: 开发前请先阅读 [开发规约](CONVENTIONS.md)

## 📚 开发规约

**新开发者必读**：
- [开发规约](CONVENTIONS.md) - 所有开发规范的权威文档
  - 文档结构规范
  - 进度记录规范
  - 代码提交规范
  - 分支管理规范
  - Worktree 使用规范
  - 测试规范
  - 开发流程规范

**模板文件**（快速上手）：
- [进度文件模板](templates/progress-file-template.md)
- [设计文档模板](templates/design-doc-template.md)

---

## 📚 文档结构

```
docs/
├── INDEX.md            # 文档索引（本文件）
├── CONVENTIONS.md      # 开发规约
├── QUICKSTART.md       # 快速开始
├── DEVELOPER_LOGS/     # 开发者日志
│   ├── 2026/
│   │   └── 2026-02-28.md
│   ├── TEMPLATE.md
│   └── README.md
├── plans/              # 设计文档（按阶段）
│   ├── phase1-design.md
│   ├── phase2-design.md
│   └── phase3-design.md
├── progress/           # 进度跟踪（按阶段）
│   ├── phase2-progress.md
│   └── phase3-progress.md
├── implementation/     # 实施计划
│   └── 2026-02-25-phase3-implementation-plan.md
├── guide/              # 用户指南
│   ├── 00-README.md
│   ├── 01-quickstart.md
│   ├── 15-多Agent协作.md
│   ├── 16-rag-guide.md
│   ├── 20-最佳实践.md
│   ├── 30-代码速查.md
│   ├── 31-常见问题.md
│   ├── COMPLETE_ORM_FLOW.md
│   └── 文档优化说明.md
├── api/                # API 文档
│   ├── sse-protocol.md
│   └── endpoints.md
├── reference/          # 参考文档
│   ├── monitor-guide.md
│   ├── orm-flow.md
│   └── code-snippets.md
├── templates/          # 文档模板
│   ├── progress-file-template.md
│   └── design-doc-template.md
└── archive/            # 归档文档
    ├── phase1/         # Phase 1 历史文档
    │   └── summary.md
    └── README.md       # 归档说明
```

## 🔗 快速导航

### 📖 规约与模板
- [开发规约](CONVENTIONS.md) - **必读！**
- [文档记录工作流程](DEVELOPER_LOGS/WORKFLOW.md) - 任务完成后的记录流程
- [进度文件模板](templates/progress-file-template.md)
- [设计文档模板](templates/design-doc-template.md)

### 📝 开发者日志
- [日志索引](DEVELOPER_LOGS/README.md) - 每日开发记录
- [日志模板](DEVELOPER_LOGS/TEMPLATE.md) - 如何写日志

### 设计文档
- [Phase 1 设计](plans/phase1-design.md) - Agent PaaS 平台基础架构
- [Phase 2 设计](plans/phase2-design.md) - 多租户与生产化
- [Phase 3 设计](plans/phase3-design.md) - 工具调用能力增强

### 进度跟踪
- [Phase 2 进度](progress/phase2-progress.md) - 多租户、认证、LLM集成
- [Phase 3 进度](progress/phase3-progress.md) - 工具调用能力

### 实施计划
- [Phase 3 实施计划](implementation/2026-02-25-phase3-implementation-plan.md) - 14任务，4周

### 参考文档
- [监控工具使用](reference/monitor-guide.md) - Linux 系统监控
- [ORM 流程](reference/COMPLETE_ORM_FLOW.md) - 数据库操作详解
- [常见问题](guide/31-常见问题.md) - FAQ

### 用户指南
- [快速入门](guide/01-quickstart.md) - 5分钟上手
- [多Agent协作](guide/15-多Agent协作.md) - 协作模式详解
- [RAG 知识库](guide/16-rag-guide.md) - RAG 使用技巧
- [最佳实践](guide/20-最佳实践.md) - 开发建议
- [常见问题](guide/31-常见问题.md) - FAQ

## 📝 文档维护

### 文档整理历史
- 2026-02-28: 优化归档文档，添加开发者日志
  - 删除 `archive/deprecated/`（过时内容）
  - 移动 `MONITOR_README.md` → `reference/`
  - 移动 `RAG_GUIDE.md` → `guide/`
  - 创建 `DEVELOPER_LOGS/` 目录结构
  - 添加日志模板和索引
  - 添加 2026-02-28 开发日志
- 2026-02-25: 中等整理，建立清晰的文档结构
  - 合并进度文件（PROGRESS.md + project_process.md → progress/phase2-progress.md）
  - 移动用户文档到 guide/
  - 分离实施计划到 implementation/
  - 清理 archive 目录

### 文档命名规范
- 设计文档: `phase{N}-design.md`
- 进度文件: `phase{N}-progress.md`
- 实施计划: `YYYY-MM-DD-phase{N}-implementation-plan.md`
- 用户指南: 数字序号 + 描述性名称

### 归档策略
- `phase1/`: 已完成阶段的历史文档
- `deprecated/`: 已废弃或被替代的文档
- 根目录保留仍有参考价值的文档

---

**更新时间**: 2026-02-25
**维护者**: Phase 3 开发团队
