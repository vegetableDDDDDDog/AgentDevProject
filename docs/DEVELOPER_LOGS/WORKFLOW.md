# 📝 任务完成后的文档记录工作流程

根据《开发规约》，每个任务完成后需要更新以下文档：

---

## 🔄 标准工作流程

### 步骤 1: 更新进度文件（必需）

**文件位置**: `docs/progress/phase{N}-progress.md`

**更新内容**:
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

**命令**:
```bash
vim docs/progress/phase3-progress.md
```

---

### 步骤 2: 记录开发者日志（必需，新增）

**文件位置**: `docs/DEVELOPER_LOGS/YYYY/YYYY-MM-DD.md`

**创建新日志**:
```bash
# 1. 复制模板
cp docs/DEVELOPER_LOGS/TEMPLATE.md docs/DEVELOPER_LOGS/2026/$(date +%Y-%m-%d).md

# 2. 编辑日志
vim docs/DEVELOPER_LOGS/2026/$(date +%Y-%m-%d).md

# 3. 更新索引
vim docs/DEVELOPER_LOGS/README.md
```

**日志内容要点**:
- 📋 基本信息（日期、任务）
- 🎯 完成的工作
- 🐛 修复的 Bug
- 📁 修改的文件清单
- 💡 经验总结

---

### 步骤 3: 更新变更日志

**文件位置**: `docs/progress/phase{N}-progress.md` 中的 `📝 变更日志` 章节

**格式**:
```markdown
### YYYY-MM-DD
- ✅ 完成任务名称（Task #N）
  - 具体变更内容1
  - 具体变更内容2
  - 测试通过情况
```

---

### 步骤 4: 提交代码（必需）

**提交格式**:
```bash
git add .
git commit -m "feat(phase3): <任务描述>

- 完成内容1
- 完成内容2

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## ✅ 任务完成检查清单

每个任务完成后，必须完成以下所有项目：

### 📝 文档记录
- [ ] 更新 `docs/progress/phase{N}-progress.md`
- [ ] 记录开发者日志 `docs/DEVELOPER_LOGS/YYYY/YYYY-MM-DD.md`
- [ ] 更新变更日志
- [ ] 更新任务状态（标记为已完成）

### 🧪 测试验证
- [ ] 运行所有测试 `pytest tests/ -v`
- [ ] 检查测试覆盖率 `pytest --cov`
- [ ] 手动测试功能

### 📦 代码提交
- [ ] 代码已格式化
- [ ] 遵循 commit 规范
- [ ] 已推送到远程仓库

---

## 🎯 一键记录脚本（推荐）

为了简化流程，我创建了一个辅助脚本：

### 创建快速日志脚本

```bash
#!/bin/bash
# quick-log.sh - 快速记录开发者日志

DATE=$(date +%Y-%m-%d)
LOG_FILE="docs/DEVELOPER_LOGS/2026/$DATE.md"

# 如果今天的日志不存在，从模板创建
if [ ! -f "$LOG_FILE" ]; then
    cp docs/DEVELOPER_LOGS/TEMPLATE.md "$LOG_FILE"
    echo "✅ 已创建日志文件: $LOG_FILE"
fi

# 打开日志文件
vim "$LOG_FILE"

# 询问是否更新索引
echo "是否更新日志索引？(y/n)"
read -r answer
if [ "$answer" = "y" ]; then
    vim docs/DEVELOPER_LOGS/README.md
fi
```

**使用方法**:
```bash
chmod +x quick-log.sh
./quick-log.sh
```

---

## 📋 每日工作结束时的标准流程

### 工作结束前（5-10分钟）

1. **查看今日修改的文件**
   ```bash
   git status
   git diff --stat
   ```

2. **更新进度文件**
   ```bash
   vim docs/progress/phase3-progress.md
   ```

3. **记录开发者日志**
   ```bash
   ./quick-log.sh
   # 或手动创建
   cp docs/DEVELOPER_LOGS/TEMPLATE.md docs/DEVELOPER_LOGS/2026/$(date +%Y-%m-%d).md
   vim docs/DEVELOPER_LOGS/2026/$(date +%Y-%m-%d).md
   ```

4. **提交代码**
   ```bash
   git add .
   git commit -m "feat(phase3): <今日总结>"
   ```

---

## 💡 最佳实践

### 1. 及时记录
- ✅ 任务完成后立即记录，不要等到下班前
- ✅ 遇到的问题和解决方案要详细记录
- ✅ 代码片段和配置要保存

### 2. 内容质量
- ✅ Bug 修复要说明根本原因
- ✅ 新功能要说明使用方法
- ✅ 性能优化要有对比数据

### 3. 持续改进
- ✅ 定期回顾开发者日志
- ✅ 总结经验教训
- ✅ 更新工作流程

---

## 📚 相关文档

- [开发规约完整版](../CONVENTIONS.md)
- [进度文件示例](../progress/phase3-progress.md)
- [日志模板](./TEMPLATE.md)
- [今日日志示例](./2026/2026-02-28.md)

---

## 🔗 快速链接

```bash
# 查看进度文件
cat docs/progress/phase3-progress.md

# 查看今日日志
cat docs/DEVELOPER_LOGS/2026/$(date +%Y-%m-%d).md

# 查看日志模板
cat docs/DEVELOPER_LOGS/TEMPLATE.md

# 编辑进度文件
vim docs/progress/phase3-progress.md

# 编辑今日日志
vim docs/DEVELOPER_LOGS/2026/$(date +%Y-%m-%d).md
```

---

**记住**: 文档记录是开发工作的重要组成部分，花费 5-10 分钟记录可以节省未来数小时的查询时间！
