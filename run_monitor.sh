#!/bin/bash
# Linux 系统监控启动脚本

echo "=========================================="
echo "  Linux 系统监控工具"
echo "=========================================="
echo ""
echo "选择运行模式:"
echo "1) 简单模式 - 过滤 snap 等挂载点 (推荐)"
echo "2) 简单模式 - 显示所有挂载点"
echo "3) 完整模式 - 过滤 snap 等挂载点 (推荐)"
echo "4) 完整模式 - 显示所有挂载点"
echo "5) 显示帮助信息"
echo ""
read -p "请输入选择 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "启动简单模式（过滤 snap）..."
        python3 linux_monitor.py --simple
        ;;
    2)
        echo ""
        echo "启动简单模式（显示所有挂载点）..."
        python3 linux_monitor.py --simple --all-disks
        ;;
    3)
        echo ""
        echo "启动完整模式（过滤 snap）..."
        python3 linux_monitor.py
        ;;
    4)
        echo ""
        echo "启动完整模式（显示所有挂载点）..."
        python3 linux_monitor.py --all-disks
        ;;
    5)
        echo ""
        python3 linux_monitor.py --help
        ;;
    *)
        echo ""
        echo "无效选择，默认使用简单模式（过滤 snap）"
        python3 linux_monitor.py --simple
        ;;
esac
