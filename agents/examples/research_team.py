"""
多 Agent 协作示例 1：研究助手（顺序协作）

演示如何使用顺序协作模式完成研究任务。
流程：Researcher（信息检索）→ Analyst（数据分析）→ Summary（结果汇总）
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import AgentOrchestrator
from agents.wrappers import RAGAgentWrapper, ToolAgentWrapper, ChatAgentWrapper


async def research_assistant_demo():
    """研究助手演示 - 顺序协作"""

    print("=" * 70)
    print("🔍 多 Agent 协作演示：研究助手（顺序协作模式）")
    print("=" * 70)

    # 1. 创建编排器
    orchestrator = AgentOrchestrator(session_id="research_demo")

    # 2. 创建并注册 Agent
    print("\n📝 注册 Agent...")

    researcher = RAGAgentWrapper(
        name="researcher",
        role="信息研究员",
        knowledge_base="./knowledge_base"
    )

    analyst = ChatAgentWrapper(
        name="analyst",
        role="数据分析员",
        system_prompt="你是一个专业的数据分析师，擅长总结和提炼关键信息。"
    )

    summarizer = ChatAgentWrapper(
        name="summarizer",
        role="报告撰写人",
        system_prompt="你是一个专业的报告撰写人，擅长将信息整合成清晰的报告。"
    )

    orchestrator.register_agent(researcher)
    orchestrator.register_agent(analyst)
    orchestrator.register_agent(summarizer)

    # 3. 显示注册状态
    print(f"\n{orchestrator.get_status()}\n")

    # 4. 执行顺序协作任务
    task = "请介绍 LangChain 的核心概念和应用"

    print(f"📋 研究任务: {task}\n")
    print("开始顺序协作...\n")

    result = await orchestrator.execute_sequential(
        agents=["researcher", "analyst", "summarizer"],
        task=task,
        context={"domain": "AI框架", "target": "LangChain"}
    )

    # 5. 显示结果
    print("\n" + "=" * 70)
    print("📊 研究报告（协作结果）")
    print("=" * 70)

    for agent_name, agent_result in result["results"].items():
        print(f"\n{'─'*70}")
        print(f"🤖 [{agent_name.upper()}] 的贡献:")
        print(f"{'─'*70}")

        if "answer" in agent_result:
            print(agent_result["answer"][:300] + "...")
        elif "response" in agent_result:
            print(agent_result["response"][:300] + "...")
        elif "error" in agent_result:
            print(f"❌ 错误: {agent_result['error']}")

    print("\n" + "=" * 70)
    print("✅ 研究任务完成！")
    print(f"📈 参与 Agent: {', '.join(result['results'].keys())}")
    print("=" * 70)


async def simple_research_demo():
    """简化版研究助手演示（仅使用 RAG + Tool）"""

    print("\n\n" + "=" * 70)
    print("🔍 简化版演示：信息检索 + 数据分析")
    print("=" * 70)

    orchestrator = AgentOrchestrator(session_id="simple_research")

    # 创建并注册 Agent
    researcher = RAGAgentWrapper(
        name="researcher",
        role="信息检索专家",
        knowledge_base="./knowledge_base"
    )

    analyst = ToolAgentWrapper(
        name="analyst",
        role="数据分析员"
    )

    orchestrator.register_agent(researcher)
    orchestrator.register_agent(analyst)

    # 执行协作任务
    task = "Python 的主要特性有哪些？请统计字数"

    print(f"\n📋 任务: {task}\n")

    result = await orchestrator.execute_sequential(
        agents=["researcher", "analyst"],
        task=task,
        context={"topic": "Python编程"}
    )

    # 显示结果
    print("\n" + "=" * 70)
    print("📊 执行结果:")
    print("=" * 70)

    for agent_name, agent_result in result["results"].items():
        print(f"\n[{agent_name}]:")
        if "answer" in agent_result:
            print(agent_result["answer"][:200] + "...")
        elif "response" in agent_result:
            print(agent_result["response"])

    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\n选择演示模式：")
    print("1. 完整版研究助手（RAG → 分析 → 总结）")
    print("2. 简化版演示（RAG → 工具）")

    choice = input("\n请输入选择 (1 或 2，默认 1): ").strip() or "1"

    if choice == "1":
        asyncio.run(research_assistant_demo())
    else:
        asyncio.run(simple_research_demo())
