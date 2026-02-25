"""
LLM 数学计算工具集成

使用 LangChain 的 LLMMathChain 进行复杂数学计算。
"""
from langchain.chains import LLMMathChain
from langchain.tools import BaseTool, StructuredTool


class LLMMathTool(BaseTool):
    """
    LLM 数学计算工具

    使用大语言模型进行精确的数学计算，
    解决 LLM 常见的计算错误问题。
    """

    name = "llm_math"
    description = "执行复杂数学计算，包括算术、代数、微积分等"

    def __init__(self, llm=None):
        """
        初始化数学工具

        Args:
            llm: 语言模型实例
        """
        self.llm = llm
        self.chain = None

        if llm:
            self.chain = LLMMathChain.from_llm(llm=llm)

    def set_llm(self, llm):
        """
        设置语言模型

        Args:
            llm: 语言模型实例
        """
        self.llm = llm
        self.chain = LLMMathChain.from_llm(llm=llm)

    def _run(self, expression: str) -> str:
        """
        执行数学计算

        Args:
            expression: 数学表达式

        Returns:
            str: 计算结果
        """
        if not self.chain:
            return "错误: 未设置语言模型"

        try:
            result = self.chain.run(expression)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算失败: {str(e)}"

    async def _arun(self, expression: str) -> str:
        """
        异步执行计算

        Args:
            expression: 数学表达式

        Returns:
            str: 计算结果
        """
        return self._run(expression)
