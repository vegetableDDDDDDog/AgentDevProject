#!/bin/bash
# AgentDevProject Phase 3 - 快速启动脚本
# 用途: 一键启动后端和前端服务

echo "========================================="
echo "Agent PaaS Platform - Phase 3 启动脚本"
echo "========================================="
echo ""

# 工作目录 - worktree 目录
WORK_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORK_DIR" || exit 1

echo "📁 工作目录: $WORK_DIR"
echo "当前分支: $(git branch --show-current)"
echo ""

# ============================================================================
# 启动后端服务
# ============================================================================

if pgrep -f "python -m api.main" > /dev/null; then
    # 检查是否是旧的工作目录
    BACKEND_CWD=$(pwdx $(pgrep -f 'python -m api.main' | head -1) 2>/dev/null | cut -d: -f2)
    if [[ "$BACKEND_CWD" != "$WORK_DIR" ]]; then
        echo "⚠️  检测到旧的后端服务运行在其他目录，正在重启..."
        pkill -f "python -m api.main"
        sleep 2
    else
        echo "✅ 后端服务已在运行 (PID: $(pgrep -f 'python -m api.main' | head -1))"
    fi
fi

if ! pgrep -f "python -m api.main" > /dev/null; then
    echo "🚀 启动后端服务..."
    nohup python -m api.main > /tmp/backend.log 2>&1 &
    sleep 3

    if pgrep -f "python -m api.main" > /dev/null; then
        echo "✅ 后端服务启动成功 (PID: $(pgrep -f 'python -m api.main' | head -1))"
    else
        echo "❌ 后端服务启动失败，查看日志: tail -f /tmp/backend.log"
        tail -20 /tmp/backend.log
        exit 1
    fi
fi

# ============================================================================
# 启动前端服务
# ============================================================================

if pgrep -f "vite" > /dev/null; then
    # 检查是否是旧的工作目录
    FRONTEND_CWD=$(pwdx $(pgrep -f 'vite' | head -1) 2>/dev/null | cut -d: -f2)
    if [[ "$FRONTEND_CWD" != "$WORK_DIR/frontend" ]]; then
        echo "⚠️  检测到旧的前端服务运行在其他目录，正在重启..."
        pkill -f "vite"
        sleep 2
    else
        echo "✅ 前端服务已在运行 (PID: $(pgrep -f 'vite' | head -1))"
    fi
fi

if ! pgrep -f "vite" > /dev/null; then
    echo "🚀 启动前端服务..."

    # 检查 node_modules
    if [ ! -d "frontend/node_modules" ]; then
        echo "📦 安装前端依赖..."
        cd frontend && npm install && cd ..
    fi

    cd frontend
    nohup npm run dev > /tmp/frontend.log 2>&1 &
    cd ..
    sleep 3

    if pgrep -f "vite" > /dev/null; then
        echo "✅ 前端服务启动成功 (PID: $(pgrep -f 'vite' | head -1))"
    else
        echo "❌ 前端服务启动失败，查看日志: tail -f /tmp/frontend.log"
        tail -20 /tmp/frontend.log
        exit 1
    fi
fi

# ============================================================================
# 显示服务状态
# ============================================================================

echo ""
echo "========================================="
echo "✅ 所有服务已启动！"
echo "========================================="
echo ""

echo "📊 服务状态:"
echo ""
echo "  后端服务:"
BACKEND_PID=$(pgrep -f 'python -m api.main' | head -1)
echo "    PID: $BACKEND_PID"
echo "    健康检查:"
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if [ -n "$HEALTH" ]; then
    echo "$HEALTH" | python -m json.tool 2>/dev/null | sed 's/^/      /' | head -5
else
    echo "    ❌ 未响应"
fi

echo ""
echo "  前端服务:"
FRONTEND_PID=$(pgrep -f 'vite' | head -1)
echo "    PID: $FRONTEND_PID"
FRONTEND_PORT=$(netstat -tlnp 2>/dev/null | grep -E ":(3000|5173)" | awk '{print $4}' | cut -d: -f2 | head -1)
echo "    端口: ${FRONTEND_PORT:-3000}"

echo ""
echo "🌐 访问地址:"
echo "  前端:     http://localhost:3000"
echo "  后端API:  http://localhost:8000"
echo "  API文档:  http://localhost:8000/docs"
echo "  健康检查: http://localhost:8000/health"
echo ""

echo "👤 测试账号:"
echo "  邮箱: test@example.com"
echo "  密码: test12345"
echo ""

echo "📝 查看日志:"
echo "  后端: tail -f /tmp/backend.log"
echo "  前端: tail -f /tmp/frontend.log"
echo ""

echo "🛑 停止服务:"
echo "  停止后端: pkill -f 'python -m api.main'"
echo "  停止前端: pkill -f vite"
echo "  停止全部: pkill -f 'python -m api.main' && pkill -f vite"
echo ""

echo "📖 查看进度文档:"
echo "  cat docs/progress/phase3-progress.md"
echo ""
