"""
RAG Agent 测试脚本
测试文档加载、向量存储、相似度检索等功能
"""

import os
import sys
import tempfile

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.rag_agent import RAGAgent


def test_basic_rag():
    """测试基本的 RAG 功能"""
    print("=" * 60)
    print("测试 1: 基础 RAG 功能")
    print("=" * 60)

    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文档
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
Python 是一种高级编程语言
Python 由 Guido van Rossum 于 1991 年创建
Python 以其简洁易读的语法而闻名
Python 广泛应用于 Web 开发、数据分析、人工智能等领域

LangChain 是一个用于开发大语言模型应用的框架
LangChain 提供了 Chain、Agent、Memory 等核心组件
LangChain 支持多种 LLM 提供商
LangChain 让构建 AI 应用变得更加简单
            """.strip())

        # 创建 RAG Agent
        agent = RAGAgent(persist_directory=os.path.join(tmpdir, "chroma_db"))

        # 加载文档
        print("\n1️⃣ 加载文档...")
        count = agent.load_documents(tmpdir)
        print(f"✅ 成功加载 {count} 个文档\n")

        # 测试查询
        questions = [
            "Python 是什么时候创建的？",
            "LangChain 有哪些核心组件？",
            "Python 有哪些应用领域？",
        ]

        print("2️⃣ 测试查询...")
        for i, question in enumerate(questions, 1):
            print(f"\n问题 {i}: {question}")
            answer = agent.query(question)
            print(f"回答: {answer}\n")
            print("-" * 40)

        print("\n✅ 基础 RAG 功能测试完成！\n")


def test_direct_text_loading():
    """测试直接加载文本"""
    print("=" * 60)
    print("测试 2: 直接加载文本")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = RAGAgent(persist_directory=os.path.join(tmpdir, "chroma_db"))

        # 添加知识
        print("\n1️⃣ 添加文本知识...")
        knowledge = """
人工智能（AI）是计算机科学的一个分支
人工智能致力于创建能够模拟人类智能的系统
机器学习是人工智能的一个重要子领域
深度学习是机器学习的一种方法
神经网络是深度学习的基础
        """.strip()

        chunks = agent.load_text(knowledge, metadata={"source": "test_knowledge"})
        print(f"✅ 成功添加 {chunks} 个文本块\n")

        # 测试查询
        print("2️⃣ 测试查询...")
        question = "什么是人工智能？"
        print(f"问题: {question}")
        answer = agent.query(question)
        print(f"回答: {answer}\n")

        print("✅ 直接加载文本测试完成！\n")


def test_persistence():
    """测试向量数据库持久化"""
    print("=" * 60)
    print("测试 3: 向量数据库持久化")
    print("=" * 60)

    persist_dir = "./test_chroma_db"

    # 第一次：创建并保存
    print("\n1️⃣ 创建新的向量数据库...")
    agent1 = RAGAgent(persist_directory=persist_dir)

    knowledge = """
测试持久化功能
这个知识应该被保存到磁盘
下次启动时应该能够加载
    """.strip()

    chunks = agent1.load_text(knowledge, metadata={"source": "persistence_test"})
    print(f"✅ 添加了 {chunks} 个文本块")
    print(f"✅ 向量数据库已保存到: {persist_dir}\n")

    # 第二次：加载已存在的
    print("2️⃣ 加载已存在的向量数据库...")
    agent2 = RAGAgent(persist_directory=persist_dir)

    if agent2.load_existing_vectorstore():
        print("✅ 成功加载向量数据库\n")

        # 测试查询
        question = "这个知识应该被保存到哪里？"
        print(f"问题: {question}")
        answer = agent2.query(question)
        print(f"回答: {answer}\n")
    else:
        print("❌ 加载失败\n")

    # 清理测试数据
    import shutil
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
        print(f"✅ 已清理测试数据: {persist_dir}\n")

    print("✅ 持久化测试完成！\n")


def test_multiple_documents():
    """测试加载多个文档"""
    print("=" * 60)
    print("测试 4: 多文档加载")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建多个测试文档
        documents = {
            "doc1.txt": """
第一章：Python 基础
Python 是一种解释型语言
Python 代码不需要编译即可运行
Python 支持面向对象编程
            """.strip(),
            "doc2.txt": """
第二章：Python 数据类型
Python 有多种内置数据类型
包括整数、浮点数、字符串、列表等
Python 是动态类型语言
            """.strip(),
            "doc3.txt": """
第三章：Python 控制流
Python 支持 if、for、while 等控制语句
Python 使用缩进来表示代码块
Python 没有传统的 switch 语句
            """.strip(),
        }

        for filename, content in documents.items():
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        # 创建 RAG Agent
        agent = RAGAgent(persist_directory=os.path.join(tmpdir, "chroma_db"))

        # 加载所有文档
        print("\n1️⃣ 加载多个文档...")
        count = agent.load_documents(tmpdir)
        print(f"✅ 成功加载 {count} 个文档\n")

        # 测试跨文档查询
        print("2️⃣ 测试跨文档查询...")
        questions = [
            "Python 的数据类型有哪些？",
            "Python 如何表示代码块？",
            "解释型语言有什么特点？",
        ]

        for i, question in enumerate(questions, 1):
            print(f"\n问题 {i}: {question}")
            answer = agent.query(question)
            print(f"回答: {answer}\n")
            print("-" * 40)

        print("\n✅ 多文档加载测试完成！\n")


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("🧪 RAG Agent 测试套件")
    print("=" * 60)

    try:
        test_basic_rag()
        test_direct_text_loading()
        test_persistence()
        test_multiple_documents()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG Agent 测试脚本")
    parser.add_argument(
        "--test", "-t",
        type=str,
        choices=["basic", "text", "persistence", "multi", "all"],
        default="all",
        help="指定要运行的测试"
    )

    args = parser.parse_args()

    if args.test == "basic":
        test_basic_rag()
    elif args.test == "text":
        test_direct_text_loading()
    elif args.test == "persistence":
        test_persistence()
    elif args.test == "multi":
        test_multiple_documents()
    else:
        run_all_tests()


if __name__ == "__main__":
    main()
