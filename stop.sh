#!/bin/bash
# AgentDevProject Phase 4 - 快速停止脚本
# 用途: 一键停止后端和前端服务

echo "========================================="
echo "Agent PaaS Platform - Phase 4 停止脚本"
echo "========================================="
echo ""

# 工作目录
WORK_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORK_DIR" || exit 1

echo "📁 工作目录: $WORK_DIR"
echo ""

# ============================================================================
# 检查服务状态
# ============================================================================

BACKEND_RUNNING=false
FRONTEND_RUNNING=false

if pgrep -f "python -m api.main" > /dev/null; then
    BACKEND_RUNNING=true
    BACKEND_PID=$(pgrep -f 'python -m api.main' | head -1)
    echo "✅ 后端服务运行中 (PID: $BACKEND_PID)"
else
    echo "⚪ 后端服务未运行"
fi

if pgrep -f "vite" > /dev/null; then
    FRONTEND_RUNNING=true
    FRONTEND_PID=$(pgrep -f 'vite' | head -1)
    echo "✅ 前端服务运行中 (PID: $FRONTEND_PID)"
else
    echo "⚪ 前端服务未运行"
fi

echo ""

# 如果没有服务运行，直接退出
if [ "$BACKEND_RUNNING" = false ] && [ "$FRONTEND_RUNNING" = false ]; then
    echo "❌ 没有运行中的服务"
    exit 0
fi

# ============================================================================
# 停止服务
# ============================================================================

echo "🛑 正在停止服务..."
echo ""

# 停止后端服务
if [ "$BACKEND_RUNNING" = true ]; then
    echo "🔄 停止后端服务..."
    pkill -f "python -m api.main"

    # 等待进程结束
    for i in {1..10}; do
        if ! pgrep -f "python -m api.main" > /dev/null; then
            echo "✅ 后端服务已停止"
            break
        fi
        sleep 0.5
    done

    # 如果还没停止，强制杀死
    if pgrep -f "python -m api.main" > /dev/null; then
        echo "⚠️  强制停止后端服务..."
        pkill -9 -f "python -m api.main"
        sleep 1
    fi
fi

# 停止前端服务
if [ "$FRONTEND_RUNNING" = true ]; then
    echo "🔄 停止前端服务..."
    pkill -f "vite"

    # 等待进程结束
    for i in {1..10}; do
        if ! pgrep -f "vite" > /dev/null; then
            echo "✅ 前端服务已停止"
            break
        fi
        sleep 0.5
    done

    # 如果还没停止，强制杀死
    if pgrep -f "vite" > /dev/null; then
        echo "⚠️  强制停止前端服务..."
        pkill -9 -f "vite"
        sleep 1
    fi
fi

echo ""

# ============================================================================
# 验证服务已停止
# ============================================================================

ALL_STOPPED=true

if pgrep -f "python -m api.main" > /dev/null; then
    echo "❌ 后端服务仍在运行 (PID: $(pgrep -f 'python -m api.main' | head -1))"
    ALL_STOPPED=false
else
    echo "✅ 后端服务已确认停止"
fi

if pgrep -f "vite" > /dev/null; then
    echo "❌ 前端服务仍在运行 (PID: $(pgrep -f 'vite' | head -1))"
    ALL_STOPPED=false
else
    echo "✅ 前端服务已确认停止"
fi

echo ""

if [ "$ALL_STOPPED" = true ]; then
    echo "========================================="
    echo "✅ 所有服务已成功停止！"
    echo "========================================="
    echo ""
    echo "💡 提示:"
    echo "  重新启动: bash start.sh"
    echo "  查看日志: tail -f /tmp/backend.log 或 /tmp/frontend.log"
    echo ""
else
    echo "========================================="
    echo "⚠️  部分服务未能停止，请手动处理"
    echo "========================================="
    echo ""
    echo "🔧 手动停止命令:"
    echo "  停止后端: pkill -9 -f 'python -m api.main'"
    echo "  停止前端: pkill -9 -f vite"
    echo ""
    exit 1
fi
