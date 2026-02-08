import sys
import os

print("Running checks...")
print("-" * 30)

# 1. 检查 Python 解释器位置
# 如果输出里包含 'agent_env'，说明你成功连上了 Conda 环境
print(f"[1] Python 路径: \n    {sys.executable}")

# 2. 检查核心库是否安装
try:
    import langchain
    import openai
    import chromadb
    print(f"\n[2] 依赖库检查:\n    LangChain 版本: {langchain.__version__}\n    OpenAI 库已安装\n    ChromaDB 库已安装")
    print("\n✅ 环境配置完美！可以开始开发 Agent 了！")
except ImportError as e:
    print(f"\n❌ 缺少依赖: {e}")
    print("请在 PyCharm 下方的 Terminal 中运行: pip install langchain openai chromadb")
