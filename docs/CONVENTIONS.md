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
5. [Worktree 使用规范](#worktree-使用规范)
6. [测试规范](#测试规范)
7. [文档命名规范](#文档命名规范)
8. [开发流程规范](#开发流程规范)

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
feature/<phase-name>        # 功能开发分支
hotfix/<issue-name>         # 紧急修复分支
release/v{version}          # 发布分支
```

**示例**：
- `feature/phase3-tool-calling`
- `hotfix/auth-token-leak`
- `release/v3.0.0`

### 🔄 分支工作流

```
master (生产)
  ↑
  │ merge
  │
feature/phase3 (开发)
  ↑
  │ create worktree
  │
phase3-tool-calling (工作树)
```

### 📋 分支切换规则

1. **功能开发** → 创建 `feature/phase{N}` 分支
2. **Worktree** → 从 feature 分支创建，隔离开发环境
3. **完成后** → 合并到 feature 分支，删除 worktree
4. **阶段完成** → 合并到 master，打 tag

### 🏷️ Tag 命名规范

```
v{major}.{minor}.{patch}

示例:
v1.0.0  - Phase 1 完成
v2.0.0  - Phase 2 完成
v3.0.0  - Phase 3 完成
```

---

## Worktree 使用规范

### 🌳 创建 Worktree

**必需步骤**：

```bash
# 1. 从 feature 分支创建 worktree
git worktree add .worktrees/phase{N}-<name> -b feature/phase{N}-<name>

# 2. 验证目录是否被 ignore
git check-ignore -q .worktrees

# 3. 如果未被忽略，添加到 .gitignore
echo ".worktrees/" >> .gitignore
git add .gitignore
git commit -m "chore: add .worktrees to gitignore"
```

### 📁 Worktree 目录结构

```
.worktrees/
├── phase{N}-<name>/
│   ├── agents/
│   ├── services/
│   ├── docs/              # 继承 + 新增
│   ├── tests/
│   └── ...                # 其他代码
```

### 🗑️ 删除 Worktree

**安全删除流程**：

```bash
# 1. 确保所有更改已提交
git status

# 2. 删除 worktree
git worktree remove .worktrees/phase{N}-<name>

# 3. 删除分支（可选）
git branch -d feature/phase{N}-<name>
```

### ⚠️ Worktree 注意事项

1. **禁止提交** `.worktrees/` 目录
2. **必须验证** 目录被 `.gitignore`
3. **定期清理** 完成的 worktree
4. **同步更新** 共享的配置文件（如 `.gitignore`）

---

## 测试规范

### 🧪 测试文件组织

```
tests/
├── unit/                  # 单元测试
│   ├── test_services.py
│   ├── test_agents.py
│   └── ...
├── integration/           # 集成测试
│   ├── test_api_integration.py
│   └── ...
├── performance/           # 性能测试
│   ├── test_tool_performance.py
│   └── ...
└── conftest.py            # pytest 配置
```

### ✅ 测试命名规范

```python
# 文件命名: test_<module>.py
test_tool_adapter.py
test_quota_service.py

# 测试类命名: Test<ClassName>
class TestToolAdapter:
    pass

# 测试函数命名: test_<specific_behavior>
def test_tool_adapter_creation():
    pass

def test_tool_adapter_async_run():
    pass
```

### 📊 测试覆盖率要求

- **单元测试**: 覆盖率 ≥ 80%
- **关键路径**: 覆盖率 = 100%
- **新增代码**: 必须有测试

### 🎯 TDD 流程

**强制流程**：

1. **写失败测试** → `pytest tests/test_xxx.py -v`
2. **验证失败** → 看到 `FAILED`
3. **写最小实现** → 刚好让测试通过
4. **验证通过** → 看到 `PASSED`
5. **提交代码** → `git commit`

**示例**：

```bash
# Step 1: 写测试
vim tests/test_tool_adapter.py

# Step 2: 运行测试（应该失败）
pytest tests/test_tool_adapter.py::test_tool_adapter_creation -v
# Expected: FAILED

# Step 3: 写实现
vim services/tool_adapter.py

# Step 4: 运行测试（应该通过）
pytest tests/test_tool_adapter.py::test_tool_adapter_creation -v
# Expected: PASSED

# Step 5: 提交
git add tests/test_tool_adapter.py services/tool_adapter.py
git commit -m "feat(phase3): add ToolAdapter"
```

---

## 文档命名规范

### 📄 设计文档命名

**格式**：`phase{N}-design.md`

**示例**：
- `phase1-design.md`
- `phase2-design.md`
- `phase3-design.md`

**禁止**：
- ❌ `2026-02-25-agent-paas-phase3-tool-calling-design.md` (过长)
- ❌ `design.md` (不明确)
- ❌ `Phase3_Design.md` (大小写混乱)

### 📊 进度文件命名

**格式**：`phase{N}-progress.md`

**示例**：
- `phase2-progress.md`
- `phase3-progress.md`

### 🛠️ 实施计划命名

**格式**：`YYYY-MM-DD-phase{N}-implementation-plan.md`

**示例**：
- `2026-02-25-phase3-implementation-plan.md`

### 📚 用户指南命名

**格式**：`{序号}-{描述性名称}.md`

**序号规范**：
- `00` - 索引/总览
- `01-09` - 基础入门
- `10-19` - 进阶内容
- `20-29` - 最佳实践
- `30-39` - 参考手册

**示例**：
- `00-README.md`
- `01-quickstart.md`
- `15-multi-agent-collaboration.md`
- `20-best-practices.md`
- `30-code-reference.md`

---

## 开发流程规范

### 🔄 标准开发流程

```
1. 规划阶段
   ├── 创建设计文档 (docs/plans/phase{N}-design.md)
   ├── 创建实施计划 (docs/implementation/...-plan.md)
   └── 创建进度文件 (docs/progress/phase{N}-progress.md)

2. 开发阶段
   ├── 创建 worktree
   ├── 按 TDD 流程开发
   ├── 更新进度文件
   └── 提交代码

3. 测试阶段
   ├── 单元测试
   ├── 集成测试
   ├── 性能测试
   └── 更新文档

4. 完成阶段
   ├── 合并到 feature 分支
   ├── 删除 worktree
   ├── 打 tag
   └── 更新 INDEX.md
```

### ✅ 任务完成检查清单

每个任务完成后，必须：

- [ ] 更新 `docs/progress/phase{N}-progress.md`
- [ ] 运行所有测试 `pytest tests/ -v`
- [ ] 检查测试覆盖率 `pytest --cov`
- [ ] 提交代码（遵循 commit 规范）
- [ ] 更新任务状态（已完成标记）

### 🚀 阶段完成检查清单

每个阶段完成后，必须：

- [ ] 所有任务已完成（100%）
- [ ] 所有测试通过
- [ ] 文档已更新
- [ ] 代码已合并到 feature 分支
- [ ] 已打版本 tag
- [ ] Worktree 已清理
- [ ] INDEX.md 已更新

---

## 配置文件规范

### 📝 必需的配置文件

每个 worktree 必须包含：

```bash
# 1. .gitignore - 忽略规则
.gitignore

# 2. requirements.txt - Python 依赖
requirements.txt

# 3. README.md - 项目说明
README.md

# 4. docs/CONVENTIONS.md - 本规约文档
docs/CONVENTIONS.md

# 5. docs/INDEX.md - 文档索引
docs/INDEX.md
```

### 📋 .gitignore 模板

```bash
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Worktrees (重要!)
.worktrees/

# Database
*.db
*.sqlite
*.sqlite3

# Environment
.env
.env.local

# Logs
*.log

# Frontend
frontend/node_modules/
frontend/dist/
frontend/.next/

# Test
.pytest_cache/
.coverage
htmlcov/
```

---

## 违规处理

### ⚠️ 规约违规分类

1. **轻微违规** - 提醒改正
   - Commit message 格式不标准
   - 文件命名不符合规范
   - 文档缺失次要章节

2. **严重违规** - 要求重做
   - 未写测试就提交
   - 提交敏感信息
   - 破坏文档结构

3. **重大违规** - 禁止合并
   - 未通过测试就合并
   - 提交大文件到仓库
   - 删除必需的文档

### 📝 违规记录

```markdown
## 违规记录

| 日期 | 开发者 | 违规类型 | 描述 | 处理方式 |
|------|--------|----------|------|----------|
| 2026-02-25 | - | - | 初始规约 | - |
```

---

## 规约更新

### 🔄 更新流程

1. 提出变更建议
2. 团队讨论
3. 更新文档
4. 更新版本号
5. 通知所有开发者

### 📋 版本历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| 1.0 | 2026-02-25 | 初始版本，定义基础规约 | Phase 3 Team |

---

## 附录

### A. 常用命令速查

```bash
# 文档相关
cat docs/CONVENTIONS.md           # 查看规约
cat docs/INDEX.md                 # 查看文档索引

# Worktree 相关
git worktree list                 # 列出所有 worktree
git worktree remove <path>        # 删除 worktree

# 测试相关
pytest tests/ -v                  # 运行所有测试
pytest tests/ --cov=services      # 测试覆盖率
pytest tests/ -m integration       # 运行集成测试

# Git 相关
git status --short                # 简短状态
git log --oneline -5              # 最近5次提交
```

### B. 文档模板

见 `docs/templates/` 目录（待创建）：
- `design-doc-template.md` - 设计文档模板
- `progress-file-template.md` - 进度文件模板
- `implementation-plan-template.md` - 实施计划模板

### C. 相关资源

- [Git Worktree 官方文档](https://git-scm.com/docs/git-worktree)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Pytest 文档](https://docs.pytest.org/)

---

**维护者**: Phase 3 开发团队
**更新频率**: 每个阶段结束后审查一次
**反馈**: 在项目 issue 中提出规约改进建议
