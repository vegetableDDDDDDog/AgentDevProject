#!/bin/bash
# 一键更新模型配置并重启服务

echo "========================================="
echo "模型配置更新工具"
echo "========================================="
echo ""

# 显示当前 .env 配置
echo "📝 当前 .env 配置:"
grep OPENAI_MODEL .env
echo ""

# 同步配置到数据库
echo "🔄 同步配置到数据库..."
python sync_model_config.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🔄 重启后端服务..."
    pkill -f 'python -m api.main'
    sleep 2
    nohup python -m api.main > /tmp/backend.log 2>&1 &
    sleep 3

    if pgrep -f 'python -m api.main' > /dev/null; then
        echo "✅ 后端服务已重启 (PID: $(pgrep -f 'python -m api.main' | head -1))"
        echo ""
        echo "========================================="
        echo "✅ 模型配置更新完成！"
        echo "========================================="
    else
        echo "❌ 后端服务启动失败"
        echo "查看日志: tail -f /tmp/backend.log"
    fi
else
    echo "❌ 配置同步失败"
fi
