"""
多 Agent 协作示例 3：文档协作写作（并行协作）

演示如何使用并行协作模式完成文档创作任务。
流程：Writer1 + Writer2 + Writer3 同时写作不同章节 → 聚合结果
"""

import asyncio
import sys
import os
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import AgentOrchestrator
from agents.base_agent import BaseAgent
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List


class DocumentWriterAgent(BaseAgent):
    """文档写作 Agent"""

    def __init__(self, name: str, topic: str, style: str = "专业"):
        """
        初始化文档写作 Agent

        Args:
            name: Agent 名称
            topic: 写作主题
            style: 写作风格（专业、轻松、学术）
        """
        super().__init__(name, f"文档作者 ({topic})")
        self.topic = topic
        self.style = style
        self.llm = ChatOpenAI(model="glm-4", temperature=0.7)

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """写作内容"""
        # 构建提示词
        prompt = f"""请撰写关于'{self.topic}'的文档内容。

写作要求：
{task}

写作风格：{self.style}
字数要求：150-250 字

请直接输出文档内容，不要添加标题或说明文字。
"""

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm.invoke(prompt)
            )

            content = response.content.strip()

            return {
                "content": content,
                "topic": self.topic,
                "style": self.style,
                "context": context,
                "word_count": len(content)
            }
        except Exception as e:
            return {
                "error": str(e),
                "topic": self.topic,
                "context": context,
                "word_count": 0
            }

    def get_capabilities(self) -> List[str]:
        return ["文档写作", "内容创作", "技术写作"]


async def document_writing_demo():
    """文档协作写作演示 - 并行协作"""

    print("=" * 70)
    print("📝 多 Agent 协作演示：文档协作写作（并行协作模式）")
    print("=" * 70)

    orchestrator = AgentOrchestrator(session_id="doc_writing_demo")

    # 创建多个写作 Agent
    print("\n📝 创建写作 Agent...")

    writers = [
        DocumentWriterAgent(
            name="writer_1",
            topic="LangChain 简介",
            style="轻松入门"
        ),
        DocumentWriterAgent(
            name="writer_2",
            topic="Agent 核心概念",
            style="专业技术"
        ),
        DocumentWriterAgent(
            name="writer_3",
            topic="实战应用案例",
            style="实例驱动"
        )
    ]

    for writer in writers:
        orchestrator.register_agent(writer)
        await asyncio.sleep(0.2)  # 避免注册信息重叠

    print(f"\n{orchestrator.get_status()}\n")

    # 定义写作任务
    tasks = [
        "介绍 LangChain 的基本概念、主要特点和核心组件",
        "解释 LangChain Agent 的工作原理、类型和最佳实践",
        "提供 2-3 个实际应用案例，说明如何使用 LangChain 解决问题"
    ]

    print("📋 写作任务：三个章节并行创作")
    print("─" * 70)
    for i, (writer, task) in enumerate(zip(writers, tasks), 1):
        print(f"{i}. [{writer.name}] {writer.topic}")
        print(f"   要求: {task}")
    print("─" * 70)

    print(f"\n🚀 开始并行执行...\n")

    # 记录开始时间
    start_time = time.time()

    # 并行写作
    result = await orchestrator.execute_parallel(
        agents=["writer_1", "writer_2", "writer_3"],
        tasks=tasks,
        context={"document": "LangChain 入门指南", "target_audience": "开发者"}
    )

    # 计算耗时
    elapsed = time.time() - start_time

    # 聚合结果
    print("\n" + "=" * 70)
    print("📄 完整文档（协作成果）")
    print("=" * 70)

    total_words = 0

    for agent_name, agent_result in result["results"].items():
        if isinstance(agent_result, dict) and "content" in agent_result:
            print(f"\n## {agent_result['topic']}")
            print(f"{'─'*70}")
            print(agent_result['content'])
            print(f"{'─'*70}")
            print(f"✍️ 作者: {agent_name} | 风格: {agent_result.get('style', 'N/A')} | 字数: {agent_result.get('word_count', 0)}")
            total_words += agent_result.get('word_count', 0)

        elif isinstance(agent_result, dict) and "error" in agent_result:
            print(f"\n## ❌ [{agent_name}] 执行失败")
            print(f"错误: {agent_result['error']}")

    # 显示统计信息
    print(f"\n{'='*70}")
    print("📊 写作统计:")
    print(f"{'='*70}")
    print(f"✅ 并行完成！")
    print(f"⏱️ 总耗时: {elapsed:.2f} 秒")
    print(f"📝 总字数: {total_words} 字")
    print(f"👥 参与作者: {len(result['results'])} 人")
    print(f"📈 效率提升: 约 {len(result['results'])}x（相比顺序写作）")
    print(f"{'='*70}")


async def custom_document_demo():
    """自定义文档协作演示"""

    print("\n" + "=" * 70)
    print("📝 自定义文档协作（并行协作）")
    print("=" * 70)

    orchestrator = AgentOrchestrator(session_id="custom_doc_demo")

    # 让用户自定义主题
    print("\n请输入要协作撰写的文档主题（3个部分）：")

    topic1 = input("第 1 章主题: ").strip() or "项目背景"
    topic2 = input("第 2 章主题: ").strip() or "技术方案"
    topic3 = input("第 3 章主题: ").strip() or "实施计划"

    writers = [
        DocumentWriterAgent(name="author_1", topic=topic1),
        DocumentWriterAgent(name="author_2", topic=topic2),
        DocumentWriterAgent(name="author_3", topic=topic3)
    ]

    for writer in writers:
        orchestrator.register_agent(writer)

    tasks = [
        "详细介绍背景和现状",
        "说明技术方案和架构",
        "列出实施步骤和时间计划"
    ]

    print(f"\n🚀 开始并行写作...\n")

    start_time = time.time()
    result = await orchestrator.execute_parallel(
        agents=["author_1", "author_2", "author_3"],
        tasks=tasks
    )
    elapsed = time.time() - start_time

    # 显示结果
    print("\n" + "=" * 70)
    print("📄 协作成果")
    print("=" * 70)

    for agent_name, agent_result in result["results"].items():
        if isinstance(agent_result, dict) and "content" in agent_result:
            print(f"\n## {agent_result['topic']}")
            print(f"{'─'*70}")
            print(agent_result['content'])
            print(f"{'─'*70}")

    print(f"\n✅ 完成！耗时: {elapsed:.2f} 秒")
    print("=" * 70)


if __name__ == "__main__":
    print("选择演示模式：")
    print("1. 预设主题：LangChain 入门指南")
    print("2. 自定义主题：输入您自己的主题")

    choice = input("\n请输入选择 (1 或 2，默认 1): ").strip() or "1"

    if choice == "2":
        asyncio.run(custom_document_demo())
    else:
        asyncio.run(document_writing_demo())
