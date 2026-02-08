"""
多 Agent 协作示例 2：代码生成（迭代协作）

演示如何使用迭代协作模式完成代码生成和优化任务。
流程：Coder（生成代码）→ Reviewer（审查）→ Coder（改进）→ Reviewer（确认）
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
from agents.base_agent import BaseAgent
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List


class CodeGeneratorAgent(BaseAgent):
    """代码生成 Agent"""

    def __init__(self, name: str):
        super().__init__(name, "代码生成器")
        self.llm = ChatOpenAI(model="glm-4", temperature=0.3)

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成代码"""
        prompt = f"请为以下需求生成 Python 代码：\n{task}\n\n"

        # 如果有反馈，根据反馈改进
        if "feedback" in context and context["feedback"]:
            prompt += f"\n请根据以下反馈改进代码：\n{context['feedback']}\n"
            prompt += "\n请直接输出改进后的完整代码，不要重复说明。"

        # 添加代码质量要求
        prompt += "\n\n要求：\n"
        prompt += "- 代码要简洁高效\n"
        prompt += "- 添加必要的注释\n"
        prompt += "- 包含简单的使用示例\n"

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm.invoke(prompt)
            )

            code = response.content

            return {
                "code": code,
                "context": {**context, "code": code},
                "done": False  # 需要审查后才能确认完成
            }
        except Exception as e:
            return {
                "error": str(e),
                "context": context,
                "done": False
            }

    def get_capabilities(self) -> List[str]:
        return ["代码生成", "代码改进", "添加注释"]


class CodeReviewAgent(BaseAgent):
    """代码审查 Agent"""

    def __init__(self, name: str):
        super().__init__(name, "代码审查员")
        self.llm = ChatOpenAI(model="glm-4", temperature=0.1)

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """审查代码"""
        # 如果没有代码，无法审查
        if "code" not in context:
            return {
                "feedback": "等待代码生成...",
                "context": context,
                "done": False
            }

        code = context["code"]

        prompt = f"""请审查以下 Python 代码，评估其质量。

代码：
{code}

请按以下格式回复：

如果代码质量良好，无明显问题，请只回复一行：
DONE: 代码质量合格

如果需要改进，请简要说明问题（不超过80字）：
TODO: [问题描述]
"""

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm.invoke(prompt)
            )

            feedback_text = response.content.strip()
            is_done = "DONE" in feedback_text or "代码质量合格" in feedback_text

            if is_done:
                print(f"✅ 审查通过：代码质量合格")
                return {
                    "feedback": "",
                    "context": context,
                    "done": True,
                    "final_code": code
                }
            else:
                # 提取反馈信息
                if "TODO:" in feedback_text:
                    feedback = feedback_text.split("TODO:")[1].strip()
                else:
                    feedback = feedback_text

                print(f"⚠️ 需要改进：{feedback}")

                return {
                    "feedback": feedback,
                    "context": {**context, "feedback": feedback},
                    "done": False
                }

        except Exception as e:
            return {
                "error": str(e),
                "context": context,
                "done": False
            }

    def get_capabilities(self) -> List[str]:
        return ["代码审查", "质量评估", "改进建议"]


async def code_generation_demo():
    """代码生成演示 - 迭代协作"""

    print("=" * 70)
    print("💻 多 Agent 协作演示：代码生成（迭代协作模式）")
    print("=" * 70)

    orchestrator = AgentOrchestrator(session_id="code_gen_demo")

    # 注册代码生成器和审查器
    print("\n📝 注册 Agent...")

    coder = CodeGeneratorAgent(name="coder")
    reviewer = CodeReviewAgent(name="reviewer")

    orchestrator.register_agent(coder)
    orchestrator.register_agent(reviewer)

    print(f"\n{orchestrator.get_status()}\n")

    # 迭代生成代码
    task_options = {
        "1": "实现一个快速排序算法，要求包含注释和示例",
        "2": "实现一个二叉树遍历函数（前序、中序、后序）",
        "3": "实现一个简单的装饰器，用于测量函数执行时间",
        "4": "自定义任务"
    }

    print("📋 可选任务：")
    for key, value in task_options.items():
        print(f"{key}. {value}")

    choice = input("\n请选择任务 (1-4，默认 1): ").strip() or "1"

    if choice == "4":
        task = input("请输入您的任务描述: ").strip()
    else:
        task = task_options.get(choice, task_options["1"])

    print(f"\n🚀 开始任务: {task}\n")

    result = await orchestrator.execute_iterative(
        agents=["coder", "reviewer"],
        task=task,
        max_iterations=3
    )

    # 显示结果
    print("\n" + "=" * 70)
    if result["status"] == "completed":
        print("✅ 代码生成完成！")
        print(f"📈 迭代次数: {result['iterations']}")
        print("=" * 70)

        # 显示最终代码
        if "final_code" in result["results"]:
            print("\n📄 最终代码：")
            print("─" * 70)
            print(result["results"]["final_code"])
            print("─" * 70)
    else:
        print("⚠️ 达到最大迭代次数")
        print(f"📈 迭代次数: {result['iterations']}")
        print("=" * 70)

        print("\n📄 当前代码（可能需要进一步优化）：")
        print("─" * 70)
        if "final_context" in result and "code" in result["final_context"]:
            print(result["final_context"]["code"])
        print("─" * 70)

    print("\n" + "=" * 70)
    print("🎉 协作完成！")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(code_generation_demo())
