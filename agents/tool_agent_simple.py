#!/usr/bin/env python3
"""
简化的工具调用 Agent - 直接演示工具使用
"""

from tool_agent import (
    calculator,
    get_current_time,
    word_counter,
    ascii_art_generator
)


def interactive_demo():
    """交互式工具演示"""

    print("=" * 70)
    print(" 🛠️  工具调用演示 - 直接调用模式")
    print("=" * 70)
    print("\n可用工具:")
    print("  1. 计算器 - 执行数学计算")
    print("  2. 时间 - 获取当前时间")
    print("  3. 字数统计 - 统计文本信息")
    print("  4. ASCII 艺术 - 生成艺术字")
    print("  0. 退出")
    print("-" * 70)

    while True:
        try:
            choice = input("\n选择功能 (0-4): ").strip()

            if choice == "0":
                print("\n👋 再见！")
                break

            elif choice == "1":
                # 计算器
                expr = input("请输入数学表达式 (如: 123 * 456): ").strip()
                if expr:
                    result = calculator.invoke({"expression": expr})
                    print(f"\n📊 {result}\n")

            elif choice == "2":
                # 时间
                fmt = input("格式 (full/date/time，默认 full): ").strip() or "full"
                result = get_current_time.invoke({"format": fmt})
                print(f"\n⏰ {result}\n")

            elif choice == "3":
                # 字数统计
                text = input("请输入要统计的文本: ").strip()
                if text:
                    result = word_counter.invoke({"text": text})
                    print(f"\n{result}\n")

            elif choice == "4":
                # ASCII 艺术
                text = input("请输入文本 (英文/数字，如: HELLO): ").strip()
                if text:
                    result = ascii_art_generator.invoke({"text": text, "style": "banner"})
                    print(f"\n{result}\n")

            else:
                print("\n❌ 无效选择，请重试\n")

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}\n")


if __name__ == "__main__":
    interactive_demo()
