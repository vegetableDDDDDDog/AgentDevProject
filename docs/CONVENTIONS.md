# Agent PaaS 平台 - 开发规约

> 本文档定义了项目的所有开发规范和约定，所有开发者必须遵守。

**版本**: 1.0
**生效日期**: 2026-02-25
**适用范围**: Phase 3 及后续所有阶段

---

## 目录

1. [文档结构规范](#文档结构规范)
2. [进度记录规范](#进度记录规范)
3. [代码提交规范](#代码提交规范)
4. [分支管理规范](#分支管理规范)
5. [测试规范](#测试规范)
6. [文档命名规范](#文档命名规范)
7. [开发流程规范](#开发流程规范)

---

## 文档结构规范

### 📁 强制性文档结构

每个阶段的 worktree 必须遵循以下文档结构：

```
<worktree>/
├── README.md                    # 项目总览（必需）
├── docs/
│   ├── CONVENTIONS.md           # 开发规约（必需，本文档）
│   ├── INDEX.md                 # 文档索引（必需）
│   ├── plans/                   # 设计文档（必需）
│   │   ├── phase{N}-design.md   # 阶段设计文档
│   │   └── ...
│   ├── progress/                # 进度跟踪（必需）
│   │   ├── phase{N}-progress.md # 阶段进度文件
│   │   └── ...
│   ├── implementation/          # 实施计划（必需）
│   │   └── YYYY-MM-DD-phase{N}-implementation-plan.md
│   ├── guide/                   # 用户指南（可选）
│   │   └── ...
│   └── archive/                 # 归档（必需）
│       ├── phase{N-1}/          # 上一阶段的历史文档
│       ├── deprecated/          # 已废弃的文档
│       └── ...
├── agents/                      # Agent 实现
├── services/                    # 服务层
├── api/                         # API 层
├── tests/                       # 测试文件
└── migrations/                  # 数据库迁移
```

### 📝 目录说明

| 目录 | 用途 | 必需性 | 说明 |
|------|------|--------|------|
| `docs/plans/` | 设计文档 | **必需** | 每个阶段一个设计文档 |
| `docs/progress/` | 进度跟踪 | **必需** | 每个阶段一个进度文件 |
| `docs/implementation/` | 实施计划 | **必需** | 详细的任务分解 |
| `docs/guide/` | 用户指南 | 可选 | 使用说明、最佳实践等 |
| `docs/archive/` | 归档 | **必需** | 历史文档分类存储 |

### 🔗 索引文件要求

每个阶段必须维护 `docs/INDEX.md`，包含：
- 文档结构说明
- 快速导航链接
- 文档更新记录

---

## 进度记录规范

### 📊 进度文件结构

每个阶段必须有一个进度文件：`docs/progress/phase{N}-progress.md`

**必需章节**：

```markdown
# Phase {N} 进度跟踪

## 📋 工作流程规约
（说明完成一个任务后的必要步骤）

## 📅 {日期} - 阶段启动
（阶段启动时的规划）

## 📊 进度状态
（任务清单，使用 checkbox）
- [x] 已完成任务
- [ ] 进行中任务
- [ ] 待开始任务

## 🔗 快速链接
（相关文档链接）

## 📝 变更日志
（按时间倒序记录所有变更）
```

### ✅ 任务完成记录

每次完成任务后，必须在进度文件中更新：

```markdown
### ✅ Task #N: 任务名称 (YYYY-MM-DD)

#### 完成内容
- 具体完成的工作项
- 新增/修改的文件列表

#### 技术特性
- 关键技术点说明

#### 验证结果
- 测试结果
- 性能指标

#### 文件清单
| 文件 | 状态 | 说明 |
```

### 📝 变更日志格式

```markdown
### YYYY-MM-DD
- ✅ 完成任务名称（Task #N）
  - 具体变更内容1
  - 具体变更内容2
  - 测试通过情况
```

### 🎯 进度百分比计算

```markdown
**进度**: X/Y 核心任务完成 (Z%)

计算公式：
- X: 已完成的任务数
- Y: 总任务数
- Z: (X / Y) * 100
```

---

## 代码提交规范

### 📝 Commit Message 格式

**强制格式**：

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Type 类型（必需）

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(phase3): add tool adapter` |
| `fix` | Bug 修复 | `fix(auth): correct token validation` |
| `docs` | 文档更新 | `docs: reorganize documentation` |
| `test` | 测试相关 | `test(api): add integration tests` |
| `refactor` | 重构 | `refactor(db): simplify connection logic` |
| `perf` | 性能优化 | `perf(cache): reduce query time` |
| `style` | 代码风格 | `style: fix indentation` |
| `chore` | 构建/工具 | `chore: update dependencies` |

#### Scope 范围（推荐）

- `phase{N}` - 阶段相关
- `api`, `services`, `agents`, `frontend` - 模块相关
- `auth`, `db`, `llm`, `tools` - 功能相关

#### Subject 主题（必需）

- 使用动词原形开头
- 首字母小写
- 不超过 50 字符
- 不加句号

**示例**：

```bash
✅ 好的提交:
feat(phase3): add ToolAdapter multi-tenant wrapper
fix(auth): correct token expiration handling
docs: update API documentation

❌ 不好的提交:
Added tool adapter
Fixed bug
Update docs
```

#### Body 正文（可选）

- 详细说明做什么、为什么
- 每行不超过 72 字符

#### Footer 脚注（可选）

```bash
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
Refs: #123
```

### 🚫 禁止的提交行为

1. ❌ 提交敏感信息（API Key、密码等）
2. ❌ 提交大文件（> 5MB）
3. ❌ 提交编译产物（`__pycache__`, `.pyc`, `node_modules`）
4. ❌ 提交格式化混乱的代码
5. ❌ 提交未测试的代码到主分支

---

## 分支管理规范

### 🌿 分支命名

```
main                       # 主分支（生产）
feature/<phase-name>      # 功能开发分支
hotfix/<issue-name>       # 紧急修复分支
release/v{version}        # 发布分支
```

**示例**：
- `main` - 主分支
- `feature/new-feature` - 新功能开发
- `hotfix/critical-bug` - 紧急修复
- `release/v3.0.0` - 发布分支

### 🔄 简化的工作流

```
main (主分支)
  ↑
  │ 直接开发
  │
开发者在 main 分支
```

### 📋 分支使用规则

1. **日常开发** → 直接在 `main` 分支
2. **大型功能** → 创建 `feature/<name>` 分支
3. **紧急修复** → 创建 `hotfix/<name>` 分支
4. **版本发布** → 创建 `release/v{version}` 标签

### 🏷️ Tag 命名规范

```
v{major}.{minor}.{patch}

示例:
v1.0.0  - Phase 1 完成
v2.0.0  - Phase 2 完成
v3.0.0  - Phase 3 完成
```

---

