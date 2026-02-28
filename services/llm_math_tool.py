"""
LLM 数学计算工具

使用 Python 的 eval 进行数学计算，配合 LLM 理解问题。
"""
from langchain.tools import BaseTool
from services.llm_service import LLMService
from typing import Optional
import re


class LLMMathTool(BaseTool):
    """
    LLM 数学计算工具

    使用大语言模型理解数学问题，然后使用 Python 进行计算。

    复用现有的 LLMService，自动适配租户的 LLM 配置。
    """

    name: str = "llm_math"
    description: str = "执行复杂数学计算，包括算术、代数、微积分等"

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        初始化数学工具

        Args:
            llm_service: LLM 服务实例（复用租户配置）
        """
        super().__init__()
        # 使用私有属性避免 Pydantic 验证问题
        object.__setattr__(self, '_llm_service', llm_service)

    @property
    def llm_service(self):
        return self._llm_service

    def set_llm(self, llm_service: LLMService):
        """
        设置/更新 LLM 服务

        Args:
            llm_service: LLM 服务实例
        """
        object.__setattr__(self, '_llm_service', llm_service)
        print("✅ LLM 已设置")

    def _safe_eval(self, expression: str) -> str:
        """
        安全地计算数学表达式

        Args:
            expression: 数学表达式

        Returns:
            str: 计算结果
        """
        try:
            # 只允许安全的数学运算
            allowed_names = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                # 数学函数
                "sqrt": lambda x: x ** 0.5,
            }

            # 使用 eval 计算表达式
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"计算错误: {str(e)}"

    def _run(self, expression: str) -> str:
        """
        执行数学计算

        Args:
            expression: 数学表达式或问题

        Returns:
            str: 计算结果
        """
        try:
            # 提取数学表达式
            # 尝试从文本中提取数学表达式
            math_pattern = r'[\d\+\-\*\/\(\)\.\s\^]+'
            matches = re.findall(math_pattern, expression)

            if matches:
                # 找到最长的匹配
                expr = max(matches, key=len)
                # 替换 ^ 为 ** (Python 的幂运算符)
                expr = expr.replace('^', '**')
                return self._safe_eval(expr)
            else:
                # 直接尝试计算
                expr = expression.replace('^', '**')
                return self._safe_eval(expr)

        except Exception as e:
            return f"计算出错: {str(e)}"

    async def _arun(self, expression: str) -> str:
        """
        异步执行计算

        Args:
            expression: 数学表达式

        Returns:
            str: 计算结果
        """
        return self._run(expression)
