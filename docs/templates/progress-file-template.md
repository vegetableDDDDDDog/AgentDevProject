# Phase {N} 进度跟踪

## 📋 工作流程规约

**任务完成后必须执行以下步骤**：
1. ✅ 更新本文档的"进度状态"和"变更日志"
2. ✅ 运行测试验证功能正常
3. ✅ 提交代码到 `feature/phase{N}-{name}` 分支
4. ✅ 更新任务完成时间

**文件位置**：
- 进度跟踪：`/path/to/worktree/docs/progress/phase{N}-progress.md`

---

## 📅 YYYY-MM-DD - 阶段启动

### ✅ 今日完成

#### 1. 规划设计
- **设计文档**: `docs/plans/phase{N}-design.md`
- **核心目标**:
  - 目标1
  - 目标2
  - 目标3

#### 2. 环境设置
- ✅ Git分支创建: `feature/phase{N}-{name}`
- ✅ Worktree创建: `.worktrees/phase{N}-{name}`
- ✅ 基准代码同步

### 📊 技术栈对比

| 组件 | Phase {N-1} | Phase {N} | 升级原因 |
|------|-------------|----------|----------|
| 示例 | 旧方案 | 新方案 | 原因说明 |

### 📋 实施计划

#### Week 1: 分类
- [ ] Task 1: 任务名称
- [ ] Task 2: 任务名称

#### Week 2: 分类
- [ ] Task 3: 任务名称

### 🔑 关键决策记录

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 决策1 | 选择A | 原因说明 |
| 决策2 | 选择B | 原因说明 |

### ⚠️ 重要注意事项

1. **注意点1** - 说明
2. **注意点2** - 说明
3. **注意点3** - 说明

### 📊 进度状态

- [x] 需求分析
- [x] 架构设计
- [x] 技术选型
- [x] 环境搭建
- [ ] 核心开发
- [ ] 测试验证
- [ ] 文档完善

**当前阶段**: {当前阶段}
**下一阶段**: {下一阶段}
**进度**: 0/{任务总数} 任务完成 (0%)

---

## 🔗 快速链接

- **设计文档**: `docs/plans/phase{N}-design.md`
- **实施计划**: `docs/implementation/YYYY-MM-DD-phase{N}-implementation-plan.md`
- **Worktree路径**: `/path/to/worktree`
- **Git分支**: `feature/phase{N}-{name}`
- **Phase {N-1}进度**: `docs/progress/phase{N-1}-progress.md`

---

## 💡 下次启动命令

```bash
# 进入Phase worktree
cd /path/to/.worktrees/phase{N}-{name}

# 查看进度
cat docs/progress/phase{N}-progress.md

# 开始实施
# Step 1: ...
```

**下次继续时间**: 待定
**当前状态**: Ready to implement 🚀

---

## 📝 变更日志

### YYYY-MM-DD
- ✅ 阶段启动
  - 创建设计文档
  - 创建实施计划
  - 创建 worktree

### ✅ Task #N: 任务名称 (YYYY-MM-DD)

#### 完成内容
- 具体完成的工作项1
- 具体完成的工作项2

#### 技术特性
- 关键技术点说明

#### 验证结果
- 测试通过
- 性能指标：XXX

#### 文件清单
| 文件 | 状态 | 说明 |
|------|------|------|
| path/to/file | ✅ 新建 | 说明 |
| path/to/file2 | ✅ 修改 | 说明 |
