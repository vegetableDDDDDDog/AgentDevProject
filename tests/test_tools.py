#!/usr/bin/env python3
"""
工具调用功能测试脚本
演示各个工具的使用方法
"""

from tool_agent import (
    calculator,
    get_current_time,
    get_current_timestamp,
    word_counter,
    ascii_art_generator
)


def test_all_tools():
    """测试所有工具"""

    print("=" * 70)
    print(" 🛠️  工具调用功能测试")
    print("=" * 70)

    # 1. 测试计算器
    print("\n📊 测试 1: 计算器")
    print("-" * 70)
    math_problems = [
        "2 + 2",
        "10 * 25",
        "100 / 4",
        "2 ** 10",
        "sqrt(144)",  # 这个会报错，用于演示错误处理
    ]

    for problem in math_problems:
        print(f"\n问题: {problem}")
        result = calculator.invoke({"expression": problem})
        print(f"结果: {result}")

    # 2. 测试时间工具
    print("\n\n⏰ 测试 2: 时间工具")
    print("-" * 70)

    print("\n完整时间:")
    result = get_current_time.invoke({"format": "full"})
    print(result)

    print("\n仅日期:")
    result = get_current_time.invoke({"format": "date"})
    print(result)

    print("\n仅时间:")
    result = get_current_time.invoke({"format": "time"})
    print(result)

    print("\n时间戳:")
    result = get_current_timestamp.invoke({})
    print(result)

    # 3. 测试字数统计
    print("\n\n📝 测试 3: 字数统计")
    print("-" * 70)

    test_text = """
    工具调用 Agent 是一个强大的功能。
    它可以让 AI 不仅会聊天，还能实际执行操作！
    """

    print(f"\n原文:\n{test_text}")
    result = word_counter.invoke({"text": test_text})
    print(f"\n{result}")

    # 4. 测试 ASCII 艺术字
    print("\n\n🎨 测试 4: ASCII 艺术字")
    print("-" * 70)

    words = ["HI", "LOVE", "CODE"]
    for word in words:
        print(f"\n生成: {word}")
        result = ascii_art_generator.invoke({"text": word, "style": "banner"})
        print(result)

    # 5. 复杂计算示例
    print("\n\n🔬 测试 5: 复杂计算")
    print("-" * 70)

    complex_calc = """
    假设你买了 10 件商品，每件 25 元，运费 15 元，
    如果打 8 折，最终需要支付多少钱？
    """

    print(f"问题: {complex_calc}")
    print("\n分步计算:")
    print("1. 商品总价: 10 * 25 = 250")
    print("2. 加上运费: 250 + 15 = 265")
    print("3. 打 8 折: 265 * 0.8 = 212")

    result = calculator.invoke({"expression": "(10 * 25 + 15) * 0.8"})
    print(f"\n最终结果: {result}")

    print("\n" + "=" * 70)
    print(" ✅ 所有测试完成！")
    print("=" * 70)


def demo_agent_usage():
    """演示 Agent 如何使用这些工具"""

    print("\n\n" + "=" * 70)
    print(" 🤖 Agent 使用示例")
    print("=" * 70)

    examples = [
        ("计算", "帮我算一下 123 乘以 456 等于多少？"),
        ("时间", "现在几点了？"),
        ("时间", "今天的日期是什么？"),
        ("统计", "统计这句话有多少字：人工智能正在改变世界"),
        ("艺术", "帮我生成一个 HELLO 的 ASCII 艺术字"),
        ("复杂", "我买了 5 本书，每本 48 元，运费 10 元，打 9 折后多少钱？"),
    ]

    print("\n💡 你可以向 Agent 这样提问：\n")

    for category, question in examples:
        print(f"【{category}】{question}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_all_tools()
    demo_agent_usage()
