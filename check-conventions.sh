#!/bin/bash

# 开发规约检查脚本
# 在每次 commit 前自动运行

echo "🚀 开发规约检查..."
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 1: Commit Message 格式
echo "📝 检查 Commit Message 格式..."
commit_msg_file=$1
if [ -f "$commit_msg_file" ]; then
    commit_msg=$(cat "$commit_msg_file")
    if [[ ! $commit_msg =~ ^(feat|fix|docs|test|refactor|perf|style|chore)\(.*\):.*$ ]]; then
        echo -e "${RED}❌ Commit Message 格式不符合规范${NC}"
        echo "正确格式: <type>(<scope>): <subject>"
        echo "Type: feat, fix, docs, test, refactor, perf, style, chore"
        echo "示例: feat(phase3): add ToolAdapter"
        exit 1
    else
        echo -e "${GREEN}✅ Commit Message 格式正确${NC}"
    fi
fi

# 检查 2: 是否有测试
echo ""
echo "🧪 检查测试文件..."
staged_files=$(git diff --cached --name-only)
if echo "$staged_files" | grep -q "services/\|agents/\|api/"; then
    if ! echo "$staged_files" | grep -q "tests/"; then
        echo -e "${YELLOW}⚠️  警告: 修改了代码但没有添加测试${NC}"
        echo "建议: 遵循 TDD 流程，先写测试再实现"
    else
        echo -e "${GREEN}✅ 包含测试文件${NC}"
    fi
fi

# 检查 3: 文档是否更新
echo ""
echo "📚 检查文档更新..."
if echo "$staged_files" | grep -q "services/\|agents/"; then
    if ! echo "$staged_files" | grep -q "docs/"; then
        echo -e "${YELLOW}⚠️  提醒: 记得更新进度文件${NC}"
        echo "位置: docs/progress/phase{N}-progress.md"
    fi
fi

# 检查 4: 文件命名规范
echo ""
echo "📝 检查文件命名..."
for file in $staged_files; do
    if [[ $file =~ docs/plans/.*\.md ]]; then
        basename=$(basename "$file")
        if [[ ! $basename =~ ^phase[0-9]+-.*\.md$ ]]; then
            echo -e "${YELLOW}⚠️  警告: 设计文档命名不规范${NC}"
            echo "文件: $file"
            echo "正确格式: phase{N}-design.md"
        fi
    fi
done

echo ""
echo -e "${GREEN}✅ 规约检查完成${NC}"
echo "详细规约: docs/CONVENTIONS.md"
echo ""
