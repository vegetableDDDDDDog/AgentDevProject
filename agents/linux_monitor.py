#!/usr/bin/env python3
"""
Linux 系统资源监控工具
实时监控 CPU、内存、磁盘和网络使用情况
"""

import psutil
import time
import curses
import sys
import os
import argparse
from functools import partial
from datetime import datetime


class SystemMonitor:
    def __init__(self):
        self.last_network_stats = None
        self.network_stats = {'sent': 0, 'recv': 0}

    def get_cpu_info(self):
        """获取 CPU 信息"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        return {
            'total_percent': cpu_percent,
            'per_core': cpu_per_core,
            'count': cpu_count,
            'frequency': cpu_freq
        }

    def get_memory_info(self):
        """获取内存信息"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            'total': memory.total,
            'used': memory.used,
            'free': memory.available,
            'percent': memory.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_percent': swap.percent
        }

    def get_disk_info(self, show_all=False):
        """获取磁盘信息

        Args:
            show_all: 是否显示所有挂载点，默认 False（过滤 snap 和特殊挂载点）
        """
        partitions = psutil.disk_partitions()
        disk_info = []

        # 定义要过滤的挂载点前缀
        filtered_prefixes = [
            '/snap',
            '/media',
            '/mnt',
            '/run/media',
            '/boot/efi'
        ]

        # 定义要过滤的文件系统类型
        filtered_fstypes = [
            'squashfs',  # snap 使用的文件系统
            'tmpfs',
            'devtmpfs',
            'proc',
            'sysfs',
            'cgroup',
            'debugfs'
        ]

        for partition in partitions:
            if partition.fstype:
                # 过滤逻辑
                should_filter = False

                if not show_all:
                    # 检查挂载点前缀
                    for prefix in filtered_prefixes:
                        if partition.mountpoint.startswith(prefix):
                            should_filter = True
                            break

                    # 检查文件系统类型
                    if partition.fstype in filtered_fstypes:
                        should_filter = True

                    # 过滤太小的分区（小于 100MB）
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        if usage.total < 100 * 1024 * 1024:  # 小于 100MB
                            should_filter = True
                    except:
                        should_filter = True

                if not should_filter:
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disk_info.append({
                            'device': partition.device,
                            'mountpoint': partition.mountpoint,
                            'fstype': partition.fstype,
                            'total': usage.total,
                            'used': usage.used,
                            'free': usage.free,
                            'percent': usage.percent
                        })
                    except (PermissionError, OSError):
                        # 跳过无权限访问的挂载点
                        pass

        return disk_info

    def get_network_info(self):
        """获取网络信息"""
        net_io = psutil.net_io_counters()
        current_stats = {'sent': net_io.bytes_sent, 'recv': net_io.bytes_recv}

        if self.last_network_stats:
            sent_speed = (current_stats['sent'] - self.last_network_stats['sent']) / 1024  # KB/s
            recv_speed = (current_stats['recv'] - self.last_network_stats['recv']) / 1024  # KB/s
        else:
            sent_speed = 0
            recv_speed = 0

        self.last_network_stats = current_stats

        return {
            'bytes_sent': current_stats['sent'],
            'bytes_recv': current_stats['recv'],
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'sent_speed': sent_speed,
            'recv_speed': recv_speed
        }

    def get_load_average(self):
        """获取系统负载"""
        try:
            return psutil.getloadavg()
        except AttributeError:
            # Windows 不支持 getloadavg
            return (0, 0, 0)

    def get_process_count(self):
        """获取进程数量"""
        return len(psutil.pids())

    def format_bytes(self, bytes_value):
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"


def draw_bar(stdscr, y, x, width, percent, label):
    """绘制进度条"""
    # 绘制标签
    stdscr.addstr(y, x, label)

    # 计算进度条宽度
    bar_width = width - len(label) - 10
    filled = int(bar_width * percent / 100)

    # 绘制进度条
    stdscr.addstr(y, x + len(label), "[")

    for i in range(bar_width):
        if i < filled:
            if percent < 50:
                stdscr.addstr(y, x + len(label) + 1 + i, "=", curses.color_pair(1))
            elif percent < 80:
                stdscr.addstr(y, x + len(label) + 1 + i, "=", curses.color_pair(2))
            else:
                stdscr.addstr(y, x + len(label) + 1 + i, "=", curses.color_pair(3))
        else:
            stdscr.addstr(y, x + len(label) + 1 + i, " ")

    stdscr.addstr(y, x + len(label) + 1 + bar_width, "]")
    stdscr.addstr(y, x + len(label) + 2 + bar_width, f"{percent:.1f}%")


def draw_progress_bar(percent, width=30):
    """绘制 ASCII 进度条"""
    filled = int(width * percent / 100)
    bar = "=" * filled + " " * (width - filled)

    # 根据使用率选择颜色（ANSI 颜色代码）
    if percent < 50:
        color_code = "\033[92m"  # 绿色
    elif percent < 80:
        color_code = "\033[93m"  # 黄色
    else:
        color_code = "\033[91m"  # 红色

    reset_code = "\033[0m"
    return f"[{color_code}{bar}{reset_code}] {percent:.1f}%"


def simple_monitor(show_all_disks=False):
    """简单终端模式（适用于 IDE 和不支持 curses 的环境）

    Args:
        show_all_disks: 是否显示所有磁盘挂载点（包括 snap 等）
    """
    global iteration
    monitor = SystemMonitor()

    # ANSI 颜色代码
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    mode_str = "简单模式" + (" (显示所有挂载点)" if show_all_disks else " (过滤 snap 等挂载点)")
    print(f"\n{CYAN}{BOLD}{'='*70}")
    print(f" Linux 系统监控 - {mode_str}")
    print(f" 按 Ctrl+C 退出{RESET}")
    print(f"{CYAN}{BOLD}{'='*70}{RESET}\n")

    try:
        iteration = 0
        while True:
            # 清屏（使用多个换行符）
            print("\n" * 2)

            # 获取当前时间
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{CYAN}{BOLD}时间: {current_time}{RESET}")
            print(f"{CYAN}{BOLD}{'='*70}{RESET}\n")

            # 获取系统信息
            cpu_info = monitor.get_cpu_info()
            memory_info = monitor.get_memory_info()
            disk_info = monitor.get_disk_info(show_all=show_all_disks)
            network_info = monitor.get_network_info()
            load_avg = monitor.get_load_average()
            process_count = monitor.get_process_count()

            # CPU 信息
            print(f"{MAGENTA}{BOLD}CPU 使用率:{RESET}")
            print(f"  总使用率: {cpu_info['total_percent']:.1f}% | "
                  f"核心数: {cpu_info['count']} | "
                  f"频率: {cpu_info['frequency'].current:.0f} MHz")

            # 每个核心的使用率
            cores_line = "  每个核心: "
            for i, core_percent in enumerate(cpu_info['per_core'][:8]):  # 最多显示8个核心
                cores_line += f"Core{i+1}:{core_percent:5.1f}% "
            print(cores_line)

            # CPU 进度条
            print(f"  {draw_progress_bar(cpu_info['total_percent'])}\n")

            # 系统负载
            print(f"{MAGENTA}{BOLD}系统负载:{RESET}")
            print(f"  1分钟: {load_avg[0]:.2f} | "
                  f"5分钟: {load_avg[1]:.2f} | "
                  f"15分钟: {load_avg[2]:.2f}\n")

            # 内存信息
            print(f"{MAGENTA}{BOLD}内存使用:{RESET}")
            print(f"  物理内存: {monitor.format_bytes(memory_info['used'])} / "
                  f"{monitor.format_bytes(memory_info['total'])} "
                  f"({memory_info['percent']:.1f}%)")
            print(f"  {draw_progress_bar(memory_info['percent'])}")
            print(f"  交换分区: {monitor.format_bytes(memory_info['swap_used'])} / "
                  f"{monitor.format_bytes(memory_info['swap_total'])} "
                  f"({memory_info['swap_percent']:.1f}%)\n")

            # 磁盘信息
            print(f"{MAGENTA}{BOLD}磁盘使用:{RESET}")
            for disk in disk_info:
                print(f"  {disk['mountpoint']:10s} - "
                      f"{monitor.format_bytes(disk['used'])} / "
                      f"{monitor.format_bytes(disk['total'])} "
                      f"({disk['percent']:.1f}%)")
            print()

            # 网络信息
            print(f"{MAGENTA}{BOLD}网络统计:{RESET}")
            print(f"  上传: {monitor.format_bytes(network_info['bytes_sent'])} "
                  f"({network_info['sent_speed']:.2f} KB/s) | "
                  f"下载: {monitor.format_bytes(network_info['bytes_recv'])} "
                  f"({network_info['recv_speed']:.2f} KB/s)")
            print(f"  数据包: 发送 {network_info['packets_sent']:,} | "
                  f"接收 {network_info['packets_recv']:,}\n")

            # 进程数量
            print(f"{MAGENTA}{BOLD}系统信息:{RESET}")
            print(f"  运行中的进程数: {process_count}\n")

            print(f"{CYAN}{BOLD}{'='*70}{RESET}")
            print(f"刷新次数: {iteration + 1} | 等待下次刷新...")

            iteration += 1
            time.sleep(2)  # 每2秒刷新一次

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}监控已停止{RESET}")
        print(f"总刷新次数: {iteration}")


def main(stack, show_all_disks=False):
    # 设置 curses
    curses.curs_set(0)  # 隐藏光标
    stack.nodelay(1)   # 非阻塞输入
    stack.timeout(1000)  # 1秒刷新

    # 定义颜色
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # 绿色 - 正常
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # 黄色 - 警告
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)     # 红色 - 危险
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)    # 青色 - 标题
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # 紫色 - 高亮

    monitor = SystemMonitor()
    line = 0

    while True:
        # 清屏
        stack.clear()

        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 标题
        mode_str = " (显示所有挂载点)" if show_all_disks else " (过滤 snap 等挂载点)"
        title = f" Linux 系统监控{mode_str} - {current_time} "
        stack.addstr(line, 2, title, curses.color_pair(4) | curses.A_BOLD)
        line += 2

        # 按 'q' 退出提示
        stack.addstr(line, 2, " 按 'q' 退出 ", curses.color_pair(3))
        line += 2

        # 获取系统信息
        cpu_info = monitor.get_cpu_info()
        memory_info = monitor.get_memory_info()
        disk_info = monitor.get_disk_info(show_all=show_all_disks)
        network_info = monitor.get_network_info()
        load_avg = monitor.get_load_average()
        process_count = monitor.get_process_count()

        # CPU 信息
        stack.addstr(line, 2, "CPU 使用率:", curses.color_pair(5) | curses.A_BOLD)
        line += 1
        stack.addstr(line, 4, f"总使用率: {cpu_info['total_percent']:.1f}% | "
                               f"核心数: {cpu_info['count']} | "
                               f"频率: {cpu_info['frequency'].current:.0f} MHz")
        line += 1

        # 每个核心的使用率
        cores_line = "每个核心: "
        for i, core_percent in enumerate(cpu_info['per_core']):
            cores_line += f"Core{i+1}:{core_percent:5.1f}% "
        stack.addstr(line, 4, cores_line)
        line += 2

        # CPU 进度条
        draw_bar(stack, line, 4, 60, cpu_info['total_percent'], "CPU 总体: ")
        line += 2

        # 系统负载
        stack.addstr(line, 2, "系统负载:", curses.color_pair(5) | curses.A_BOLD)
        line += 1
        stack.addstr(line, 4, f"1分钟: {load_avg[0]:.2f} | "
                               f"5分钟: {load_avg[1]:.2f} | "
                               f"15分钟: {load_avg[2]:.2f}")
        line += 2

        # 内存信息
        stack.addstr(line, 2, "内存使用:", curses.color_pair(5) | curses.A_BOLD)
        line += 1
        stack.addstr(line, 4, f"物理内存: {monitor.format_bytes(memory_info['used'])} / "
                               f"{monitor.format_bytes(memory_info['total'])} "
                               f"({memory_info['percent']:.1f}%)")
        line += 1
        stack.addstr(line, 4, f"交换分区: {monitor.format_bytes(memory_info['swap_used'])} / "
                               f"{monitor.format_bytes(memory_info['swap_total'])} "
                               f"({memory_info['swap_percent']:.1f}%)")
        line += 2

        # 内存进度条
        draw_bar(stack, line, 4, 60, memory_info['percent'], "内存使用: ")
        line += 2

        # 磁盘信息
        stack.addstr(line, 2, "磁盘使用:", curses.color_pair(5) | curses.A_BOLD)
        line += 1
        for disk in disk_info:
            stack.addstr(line, 4, f"{disk['mountpoint']:10s} - "
                                   f"{monitor.format_bytes(disk['used'])} / "
                                   f"{monitor.format_bytes(disk['total'])} "
                                   f"({disk['percent']:.1f}%)")
            line += 1
        line += 1

        # 网络信息
        stack.addstr(line, 2, "网络统计:", curses.color_pair(5) | curses.A_BOLD)
        line += 1
        stack.addstr(line, 4, f"上传: {monitor.format_bytes(network_info['bytes_sent'])} "
                               f"({network_info['sent_speed']:.2f} KB/s) | "
                               f"下载: {monitor.format_bytes(network_info['bytes_recv'])} "
                               f"({network_info['recv_speed']:.2f} KB/s)")
        line += 2
        stack.addstr(line, 4, f"数据包: 发送 {network_info['packets_sent']:,} | "
                               f"接收 {network_info['packets_recv']:,}")
        line += 2

        # 进程数量
        stack.addstr(line, 2, "系统信息:", curses.color_pair(5) | curses.A_BOLD)
        line += 1
        stack.addstr(line, 4, f"运行中的进程数: {process_count}")

        # 刷新屏幕
        stack.refresh()

        # 重置行号
        line = 0

        # 检查是否按下 'q' 键退出
        key = stack.getch()
        if key == ord('q') or key == ord('Q'):
            break


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Linux 系统资源监控工具', add_help=False)
    parser.add_argument('--simple', action='store_true', help='使用简单模式（IDE 兼容）')
    parser.add_argument('--all-disks', action='store_true', help='显示所有磁盘挂载点（包括 snap 等）')
    parser.add_argument('-h', '--help', action='store_true', help='显示帮助信息')

    # 只解析已知参数，保留其他参数
    args, unknown = parser.parse_known_args()

    # 显示帮助信息
    if args.help:
        parser.print_help()
        print("\n示例:")
        print("  python3 linux_monitor.py              # 自动选择模式（默认过滤 snap）")
        print("  python3 linux_monitor.py --simple      # 强制使用简单模式")
        print("  python3 linux_monitor.py --all-disks   # 显示所有挂载点（包括 snap）")
        print("  python3 linux_monitor.py --simple --all-disks  # 简单模式 + 显示所有挂载点")
        sys.exit(0)

    # 检测运行环境
    # 如果在 IDE 中运行或缺少 TTY，使用简单模式
    use_simple_mode = args.simple or not sys.stdout.isatty()

    if use_simple_mode:
        # 简单模式（适用于 IDE）
        simple_monitor(show_all_disks=args.all_disks)
    else:
        # curses 模式（完整终端模式）
        try:
            # 使用 partial 传递参数给 main 函数
            curses.wrapper(partial(main, show_all_disks=args.all_disks))
        except KeyboardInterrupt:
            print("\n监控已停止")
        except Exception as e:
            print(f"错误: {e}")
            print("\n正在切换到简单模式...")
            time.sleep(1)
            simple_monitor(show_all_disks=args.all_disks)
