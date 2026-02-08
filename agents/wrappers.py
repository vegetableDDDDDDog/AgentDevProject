"""
多 Agent 协作 - Agent 适配器

包装现有 Agent，使其符合 BaseAgent 接口。
"""

from agents.base_agent import BaseAgent
from agents.tool_agent import create_tool_agent
from agents.rag_agent import RAGAgent
from typing import Dict, Any, List
import asyncio


class ToolAgentWrapper(BaseAgent):
    """
    工具 Agent 包装器

    包装 tool_agent，使其符合多 Agent 协作接口。
    """

    def __init__(self, name: str, role: str = "工具专家"):
        """
        初始化工具 Agent 包装器

        Args:
            name: Agent 名称
            role: Agent 角色
        """
        super().__init__(name, role)
        self.tool_chain = create_tool_agent()

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具调用

        Args:
            task: 任务描述
            context: 上下文

        Returns:
            执行结果
        """
        try:
            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.tool_chain.invoke({"input": task})
            )

            return {
                "response": response.content,
                "context": context,
                "done": True
            }
        except Exception as e:
            return {
                "error": str(e),
                "context": context,
                "done": True
            }

    def get_capabilities(self) -> List[str]:
        """返回能力列表"""
        return ["计算器", "时间查询", "字数统计", "ASCII艺术"]


class RAGAgentWrapper(BaseAgent):
    """
    RAG Agent 包装器

    包装 rag_agent，使其符合多 Agent 协作接口。
    """

    def __init__(
        self,
        name: str,
        role: str = "知识库专家",
        knowledge_base: str = "./knowledge_base"
    ):
        """
        初始化 RAG Agent 包装器

        Args:
            name: Agent 名称
            role: Agent 角色
            knowledge_base: 知识库路径
        """
        super().__init__(name, role)
        self.rag_agent = RAGAgent()

        # 加载知识库
        try:
            self.rag_agent.load_documents(knowledge_base)
            print(f"✅ {name} 知识库加载成功")
        except Exception as e:
            print(f"⚠️ {name} 知识库加载失败: {e}")
            print(f"   将使用默认知识库或重新加载")

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行知识库查询

        Args:
            task: 查询任务
            context: 上下文

        Returns:
            查询结果
        """
        try:
            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(
                None,
                lambda: self.rag_agent.query(task)
            )

            return {
                "answer": answer,
                "context": context,
                "done": True
            }
        except Exception as e:
            return {
                "error": str(e),
                "context": context,
                "done": True
            }

    def get_capabilities(self) -> List[str]:
        """返回能力列表"""
        return ["文档检索", "知识问答", "语义搜索"]

    def reload_knowledge_base(self, path: str) -> bool:
        """
        重新加载知识库

        Args:
            path: 知识库路径

        Returns:
            是否成功
        """
        try:
            self.rag_agent.load_documents(path)
            print(f"✅ {self.name} 重新加载知识库成功")
            return True
        except Exception as e:
            print(f"❌ 重新加载失败: {e}")
            return False


class ChatAgentWrapper(BaseAgent):
    """
    聊天 Agent 包装器

    包装 chat_agent，使其符合多 Agent 协作接口。
    """

    def __init__(self, name: str, role: str = "对话助手", system_prompt: str = None):
        """
        初始化聊天 Agent 包装器

        Args:
            name: Agent 名称
            role: Agent 角色
            system_prompt: 系统提示词
        """
        super().__init__(name, role)

        # 导入必要的模块
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        self.llm = ChatOpenAI(model="glm-4", temperature=0.7)

        if system_prompt:
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}")
            ])
        else:
            self.prompt = ChatPromptTemplate.from_template("{input}")

        self.chain = self.prompt | self.llm | StrOutputParser()

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行对话

        Args:
            task: 对话输入
            context: 上下文

        Returns:
            对话响应
        """
        try:
            # 构建输入，包含上下文
            input_text = task
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items() if k != "response"])
                if context_str:
                    input_text = f"上下文信息：\n{context_str}\n\n任务：\n{task}"

            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.chain.invoke({"input": input_text})
            )

            return {
                "response": response,
                "context": {**context, "response": response},
                "done": True
            }
        except Exception as e:
            return {
                "error": str(e),
                "context": context,
                "done": True
            }

    def get_capabilities(self) -> List[str]:
        """返回能力列表"""
        return ["多轮对话", "文本生成", "问题回答"]
