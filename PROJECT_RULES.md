# 🚨 项目开发规约 - AI 助手必读

> Claude Code 用户：在开始任何任务前，我必须遵守以下规约

## ⚡ 快速检查清单（每次开发前）

### 1️⃣ 文档结构（强制）
```
docs/
├── CONVENTIONS.md        # 完整规约（已读过）
├── plans/               # 设计文档
├── progress/            # 进度文件（每阶段一个）
├── implementation/      # 实施计划
└── templates/           # 模板文件
```

### 2️⃣ 进度记录（每次任务后）
- ✅ 更新 `docs/progress/phase{N}-progress.md`
- ✅ 使用 checkbox 标记完成任务
- ✅ 记录变更日志（日期 + 内容）

### 3️⃣ Commit 格式（强制）
```bash
<type>(<scope>): <subject>

# Type: feat, fix, docs, test, refactor, perf, style, chore
# Scope: phase{N}, api, services, agents, frontend, auth, db, llm, tools
# Subject: 动词原形，小写，不超过50字符

✅ feat(phase3): add ToolAdapter multi-tenant wrapper
✅ fix(auth): correct token validation
✅ docs: update API documentation
```

### 4️⃣ TDD 流程（强制）
```bash
# 1. 写测试
# 2. 运行测试（预期失败）
# 3. 写实现
# 4. 运行测试（预期通过）
# 5. 提交
```

### 5️⃣ 文件命名（强制）
- 设计文档: `phase{N}-design.md`
- 进度文件: `phase{N}-progress.md`
- 实施计划: `YYYY-MM-DD-phase{N}-implementation-plan.md`

## 🎯 行为准则

### 📖 遇到以下任务时，自动做：

**创建新阶段时**：
1. 读取 `docs/templates/design-doc-template.md`
2. 读取 `docs/templates/progress-file-template.md`
3. 使用模板创建文档

**开发任务时**：
1. 先读取 `docs/progress/phase{N}-progress.md`
2. 遵循 TDD 流程
3. 完成后更新进度文件

**提交代码时**：
1. 检查 Commit Message 格式
2. 确保有测试
3. 确认文档已更新

**创建文件时**：
1. 检查文件名是否符合规范
2. 检查文件位置是否正确

## 🚨 禁止行为

❌ 跳过测试直接实现
❌ 提交时不用规范的 Commit Message
❌ 创建文档不用模板
❌ 完成任务后不更新进度文件
❌ 忽略 .gitignore 规则

## 📝 记住

- **文档优先**: 创建文档前先看模板
- **测试先行**: 实现功能前先写测试
- **规范命名**: 文件名必须符合规范
- **及时记录**: 完成任务立即更新进度
- **标准提交**: Commit Message 必须规范

---

**生效**: 所有后续对话自动遵守
**更新**: 规约更新时自动同步
