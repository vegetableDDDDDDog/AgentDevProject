"""
RAG (检索增强生成) Agent
支持基于本地知识库的问答系统
"""

import os
from typing import List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import (
    TextLoader,
    DirectoryLoader,
    PyPDFLoader,
)
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 加载环境变量
load_dotenv()

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 配置
PERSIST_DIRECTORY = os.path.join(PROJECT_ROOT, "data", "chroma_db")  # 向量数据库持久化目录
CHUNK_SIZE = 500  # 文档分块大小
CHUNK_OVERLAP = 50  # 分块重叠大小
TOP_K = 3  # 检索最相关的 K 个文档块


class RAGAgent:
    """RAG 知识库问答 Agent"""

    def __init__(
        self,
        model_name: str = None,
        persist_directory: str = PERSIST_DIRECTORY,
    ):
        """初始化 RAG Agent

        Args:
            model_name: 模型名称，默认从环境变量读取
            persist_directory: 向量数据库持久化目录
        """
        # 从环境变量获取配置
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_base = os.getenv("OPENAI_API_BASE")
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "glm-4")
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-v3")

        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.api_base,
            temperature=0.7,
        )

        # 初始化 Embedding 模型（智谱 AI 支持的 embedding 模型）
        self.embeddings = OpenAIEmbeddings(
            model=self.embedding_model,
            api_key=self.api_key,
            base_url=self.api_base,
        )

        # 持久化目录
        self.persist_directory = persist_directory

        # 向量数据库（懒加载）
        self.vectorstore = None

        # RAG 提示词模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能助手，擅长基于提供的知识库回答问题。

知识库内容：
{context}

请根据以上知识库内容回答用户的问题。如果知识库中没有相关信息，请明确告知用户，不要编造答案。

回答要求：
1. 优先使用知识库中的信息
2. 如果知识库信息不足，可以结合你的知识补充说明，但要明确区分
3. 回答要准确、清晰、有条理"""),
            ("human", "{question}"),
        ])

        # 创建 RAG Chain
        self.rag_chain = (
            {
                "context": self._retrieve_context,
                "question": lambda x: x["question"],
            }
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def _retrieve_context(self, inputs: dict) -> str:
        """检索相关文档上下文

        Args:
            inputs: 包含 question 的字典

        Returns:
            检索到的文档内容拼接字符串
        """
        if self.vectorstore is None:
            return "（知识库未加载，请先加载文档）"

        question = inputs["question"]

        # 相似度搜索
        docs = self.vectorstore.similarity_search(question, k=TOP_K)

        # 拼接文档内容
        context_parts = []
        for i, doc in enumerate(docs, 1):
            context_parts.append(f"[文档片段 {i}]\n{doc.page_content}\n")

        return "\n".join(context_parts) if context_parts else "（未找到相关文档）"

    def load_documents(self, path: str, glob: str = "**/*.txt") -> int:
        """从目录加载文档

        Args:
            path: 文档目录路径
            glob: 文件匹配模式，支持 *.txt, *.md, *.pdf 等

        Returns:
            加载的文档数量
        """
        print(f"📂 正在加载文档: {path}")

        # 根据文件类型选择加载器
        if glob.endswith(".pdf"):
            loader = DirectoryLoader(
                path,
                glob=glob,
                loader_cls=PyPDFLoader,
                show_progress=True,
            )
        else:
            loader = DirectoryLoader(
                path,
                glob=glob,
                loader_cls=TextLoader,
                loader_kwargs={"autodetect_encoding": True},
                show_progress=True,
            )

        # 加载文档
        documents = loader.load()
        print(f"✅ 加载了 {len(documents)} 个文档")

        # 分割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
        )

        print("✂️  正在分割文档...")
        splits = text_splitter.split_documents(documents)
        print(f"✅ 分割成 {len(splits)} 个文本块")

        # 创建或更新向量数据库
        print(f"💾 正在创建向量数据库...")

        if self.vectorstore is None:
            # 创建新的向量数据库
            self.vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
            )
        else:
            # 添加到现有向量数据库
            self.vectorstore.add_documents(splits)

        print(f"✅ 向量数据库已保存到: {self.persist_directory}")
        return len(documents)

    def load_text(self, text: str, metadata: dict = None) -> int:
        """直接加载文本内容

        Args:
            text: 文本内容
            metadata: 文档元数据

        Returns:
            文本块数量
        """
        # 创建文档
        doc = Document(page_content=text, metadata=metadata or {})

        # 分割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )

        splits = text_splitter.split_documents([doc])

        # 创建或更新向量数据库
        if self.vectorstore is None:
            self.vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
            )
        else:
            self.vectorstore.add_documents(splits)

        return len(splits)

    def load_existing_vectorstore(self):
        """加载已存在的向量数据库"""
        if os.path.exists(self.persist_directory):
            print(f"📂 正在加载向量数据库: {self.persist_directory}")
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
            )
            print(f"✅ 向量数据库已加载")
            return True
        else:
            print(f"❌ 向量数据库不存在: {self.persist_directory}")
            print(f"💡 提示：请先使用 load_documents() 或 load_text() 加载文档")
            return False

    def query(self, question: str, stream: bool = False) -> str:
        """查询知识库

        Args:
            question: 用户问题
            stream: 是否使用流式输出

        Returns:
            AI 回答
        """
        if self.vectorstore is None:
            # 尝试加载已存在的向量数据库
            if not self.load_existing_vectorstore():
                return "❌ 知识库未初始化。请先使用 load_documents() 或 load_text() 加载文档。"

        print(f"\n🤖 正在思考...")
        print(f"📚 检索相关文档...")

        if stream:
            # 流式输出
            print("\n💬 回答：")
            for chunk in self.rag_chain.stream({"question": question}):
                print(chunk, end="", flush=True)
            print()  # 换行
            return ""
        else:
            # 一次性输出
            answer = self.rag_chain.invoke({"question": question})
            return answer

    def chat(self):
        """交互式问答模式"""
        print("=" * 50)
        print("🤖 RAG 知识库问答系统")
        print("=" * 50)

        # 尝试加载已存在的向量数据库
        if self.vectorstore is None:
            self.load_existing_vectorstore()

        print("\n💡 提示：")
        print("  - 直接输入问题进行查询")
        print("  - 输入 'load <路径>' 加载文档目录")
        print("  - 输入 'add <文本>' 直接添加文本")
        print("  - 输入 'clear' 清除当前会话")
        print("  - 输入 'status' 查看知识库状态")
        print("  - 输入 'exit' 或 'quit' 退出")

        while True:
            try:
                user_input = input("\n👤 你: ").strip()

                if not user_input:
                    continue

                # 处理命令
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("\n👋 再见！")
                    break

                elif user_input.lower() in ["clear", "cls"]:
                    print("\n✅ 已清除当前会话")
                    continue

                elif user_input.lower() in ["status", "info"]:
                    self._print_status()
                    continue

                elif user_input.lower().startswith("load "):
                    # 加载文档目录
                    path = user_input[5:].strip()
                    if os.path.isdir(path):
                        self.load_documents(path)
                    else:
                        print(f"❌ 目录不存在: {path}")
                    continue

                elif user_input.lower().startswith("add "):
                    # 添加文本
                    text = user_input[4:].strip()
                    chunks = self.load_text(text, metadata={"source": "user_input"})
                    print(f"✅ 已添加 {chunks} 个文本块")
                    continue

                # 普通查询
                answer = self.query(user_input, stream=True)

            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")

    def _print_status(self):
        """打印知识库状态"""
        print("\n📊 知识库状态：")
        print(f"  模型: {self.model_name}")
        print(f"  Embedding: {self.embedding_model}")

        if self.vectorstore is None:
            print(f"  状态: 未初始化")
            print(f"  持久化目录: {self.persist_directory}")
        else:
            # 获取向量数据库中的文档数量
            collection = self.vectorstore._collection
            count = collection.count()
            print(f"  状态: 已加载")
            print(f"  文本块数量: {count}")
            print(f"  持久化目录: {self.persist_directory}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG 知识库问答系统")
    parser.add_argument(
        "--load", "-l",
        type=str,
        help="加载文档目录"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="查询问题（单次模式）"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="进入交互模式"
    )

    args = parser.parse_args()

    # 创建 RAG Agent
    agent = RAGAgent()

    # 加载文档
    if args.load:
        agent.load_documents(args.load)

    # 单次查询
    if args.query:
        answer = agent.query(args.query)
        print(f"\n💬 回答：\n{answer}")
        return

    # 交互模式或默认模式
    if args.interactive or not (args.load or args.query):
        agent.chat()


if __name__ == "__main__":
    main()
