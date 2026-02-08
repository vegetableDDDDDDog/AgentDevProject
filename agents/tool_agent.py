#!/usr/bin/env python3
"""
工具调用 Agent
演示如何给 Agent 添加工具使用能力
"""

import os
import operator
from datetime import datetime
from typing import Annotated, Literal

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from chat_agent import SQLiteChatMessageHistory

# ==================== 工具定义 ====================

@tool
def calculator(expression: str) -> str:
    """
    执行数学计算

    支持的运算符：+, -, *, /, **, % 等
    示例：
        - "2 + 2" 返回 "4"
        - "10 ** 2" 返回 "100"
        - "100 / 4" 返回 "25.0"

    Args:
        expression: 数学表达式字符串

    Returns:
        计算结果的字符串表示
    """
    try:
        # 使用 eval 进行计算，但限制可用的函数
        allowed_names = {
            "__builtins__": {},
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
        }
        result = eval(expression, allowed_names, {})
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


@tool
def get_current_time(format: Literal["full", "date", "time"] = "full") -> str:
    """
    获取当前时间

    Args:
        format: 时间格式
            - "full": 完整日期时间 (默认)
            - "date": 仅日期
            - "time": 仅时间

    Returns:
        格式化的时间字符串
    """
    now = datetime.now()

    if format == "date":
        return now.strftime("%Y-%m-%d")
    elif format == "time":
        return now.strftime("%H:%M:%S")
    else:
        return now.strftime("%Y-%m-%d %H:%M:%S")


@tool
def get_current_timestamp() -> str:
    """
    获取当前时间戳（Unix 时间戳）

    Returns:
        Unix 时间戳字符串
    """
    timestamp = int(datetime.now().timestamp())
    return f"当前时间戳: {timestamp}"


@tool
def word_counter(text: str) -> str:
    """
    统计文本的字数、字符数和行数

    Args:
        text: 要统计的文本内容

    Returns:
        包含统计信息的字符串
    """
    char_count = len(text)
    word_count = len(text.split())
    line_count = len(text.split('\n'))

    result = f"""
📊 文本统计结果:
━━━━━━━━━━━━━━━━━━
字符数: {char_count}
单词数: {word_count}
行数: {line_count}
━━━━━━━━━━━━━━━━━━
"""
    return result.strip()


@tool
def ascii_art_generator(text: str, style: Literal["banner", "standard"] = "standard") -> str:
    """
    生成简单的 ASCII 艺术字（仅支持英文和数字）

    Args:
        text: 要转换的文本（建议 1-10 个字符）
        style: 风格（banner 或 standard）

    Returns:
        ASCII 艺术字字符串
    """
    # 简化的 ASCII 艺术字映射（只支持几个示例字符）
    art_dict = {
        'A': [
            "  A  ",
            " A A ",
            "AAAAA",
            "A   A",
            "A   A"
        ],
        'H': [
            "H   H",
            "H   H",
            "HHHHH",
            "H   H",
            "H   H"
        ],
        'I': [
            " III ",
            "  I  ",
            "  I  ",
            "  I  ",
            " III "
        ],
        'LOVE': [
            "L    O   V   E",
            "L   O O  V   E",
            "L  O   O V   E",
            "L O     O V V",
            "LL       O  V"
        ]
    }

    # 简单实现：返回装饰性文本
    if style == "banner":
        separator = "═" * (len(text) + 4)
        return f"""
╔{separator}╗
║  {text}  ║
╚{separator}╝
""".strip()
    else:
        separator = "=" * (len(text) + 4)
        return f"""
[{separator}]
[  {text}  ]
[{separator}]
""".strip()


# ==================== Agent 配置 ====================

def create_tool_agent():
    """创建带工具的 Agent"""

    # 1. 定义工具列表
    tools = [
        calculator,
        get_current_time,
        get_current_timestamp,
        word_counter,
        ascii_art_generator,
    ]

    # 2. 创建 LLM
    llm = ChatOpenAI(
        model="glm-4",
        temperature=0.7,
    )

    # 3. 绑定工具到 LLM
    llm_with_tools = llm.bind_tools(tools)

    # 4. 创建提示词模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个智能助手，可以使用多种工具来帮助用户。

你可以使用以下工具：
- calculator: 执行数学计算（表达式字符串）
- get_current_time: 获取当前时间（格式参数：full/date/time）
- get_current_timestamp: 获取 Unix 时间戳
- word_counter: 统计文本的字数、字符数和行数
- ascii_art_generator: 生成 ASCII 艺术字

使用工具时，请：
1. 理解用户的需求
2. 选择合适的工具
3. 调用工具获取结果
4. 用自然语言向用户解释结果

如果不需要使用工具，就直接回答用户的问题。"""),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
    ])

    # 5. 创建 Chain
    chain = prompt | llm_with_tools

    return chain, tools


def get_session_history(session_id: str) -> SQLiteChatMessageHistory:
    """获取会话历史"""
    return SQLiteChatMessageHistory(session_id=session_id)


# ==================== 主程序 ====================

def main():
    """主交互循环"""
    print("=" * 60)
    print(" 🛠️  工具调用 Agent")
    print(" 支持: 计算、时间、统计、ASCII 艺术字等工具")
    print("=" * 60)
    print("\n💡 提示:")
    print("  - '计算 123 * 456'")
    print("  - '现在几点了？'")
    print("  - '统计这段话的字数：...'")
    print("  - '生成 ASCII 艺术字：HELLO'")
    print("\n命令: clear (清空历史) | status (状态) | exit (退出)")
    print("-" * 60)

    # 创建 Agent
    chain, tools = create_tool_agent()

    # 创建工具映射（名称 -> 工具函数）
    tools_map = {tool.name: tool for tool in tools}

    # 会话 ID
    session_id = "tool_agent_session"

    # 历史记录管理
    history = get_session_history(session_id)

    while True:
        try:
            # 获取用户输入
            user_input = input("\n🤖 你: ").strip()

            # 处理空输入
            if not user_input:
                continue

            # 处理内置命令
            if user_input.lower() in ["exit", "quit", "q"]:
                print("\n👋 再见！")
                break

            if user_input.lower() in ["clear", "cls"]:
                history.clear()
                print("✅ 会话历史已清空")
                continue

            if user_input.lower() in ["status", "info"]:
                msgs = history.messages
                print(f"\n📊 会话状态:")
                print(f"  会话 ID: {session_id}")
                print(f"  消息数: {len(msgs)}")
                print(f"  可用工具: {', '.join(tools_map.keys())}")
                continue

            # 调用 Chain
            print("\n🤖 助手正在思考...\n")

            response = chain.invoke({
                "input": user_input,
                "chat_history": history.messages,
            })

            # 检查是否有工具调用
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # 执行工具调用
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']

                    print(f"🔧 调用工具: {tool_name}")
                    print(f"   参数: {tool_args}")

                    # 执行工具
                    if tool_name in tools_map:
                        tool_result = tools_map[tool_name].invoke(tool_args)
                        print(f"   结果: {tool_result}\n")

                        # 添加到历史（工具调用）
                        history.add_messages([
                            HumanMessage(content=user_input),
                            response,  # 包含工具调用信息的消息
                            AIMessage(content=tool_result)
                        ])
            else:
                # 如果没有工具调用，直接显示回复
                print(f"\n🤖 助手: {response.content}\n")

                # 保存到历史
                history.add_messages([
                    HumanMessage(content=user_input),
                    AIMessage(content=response.content)
                ])

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            print("提示: 检查输入或重试")


if __name__ == "__main__":
    from langchain_core.messages import HumanMessage, AIMessage

    main()
