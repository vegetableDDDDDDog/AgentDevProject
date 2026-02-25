# Agent 开发学习总结

> 📅 创建时间：2026-02-02
> 🎯 目标：从零开始学习 LangChain Agent 开发

---

## 📚 项目结构

```
AgentDevProject/
├── .env                      # API 配置文件（环境变量）
├── my_first_agent.py         # 单轮对话 Agent
├── chat_agent.py             # 多轮对话 Agent（记忆 + 持久化）
├── tool_agent.py             # 工具调用 Agent（计算、时间、统计等）
├── tool_agent_simple.py      # 工具调用简化版（直接调用工具）
├── rag_agent.py              # RAG 知识库 Agent
├── test_setup.py             # 环境检测脚本
├── test_persistence.py       # 持久化测试脚本
├── test_tools.py             # 工具功能测试脚本
├── test_rag.py               # RAG 功能测试脚本
├── knowledge_base/           # 示例知识库目录
│   ├── python_intro.txt
│   ├── langchain_guide.txt
│   └── ai_concepts.txt
├── chat_history.db           # SQLite 数据库（自动创建）
├── chroma_db/                # 向量数据库（自动创建）
├── TOOL_AGENT_README.md      # 工具调用 Agent 文档
├── requirements.txt          # 依赖清单
└── summary.md                # 本文档
```

---

## ✅ 已完成功能

### 1. 环境配置 (.env)
```env
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4/
OPENAI_MODEL=glm-4
```

### 2. 单轮对话 Agent (my_first_agent.py)
- 基础 LLM 调用、系统提示词设置
- 适用：一次性问答、快速原型

### 3. 多轮对话 Agent (chat_agent.py)
- **记忆管理**：SQLite 持久化 + 自动裁剪（保留最近 10 条）
- **流式输出**：打字机效果
- **会话隔离**：通过 session_id 支持多用户
- **内置命令**：`clear` 清空历史 | `status` 查看状态

### 4. 工具调用 Agent (tool_agent.py)
- **工具定义**：使用 @tool 装饰器定义工具
- **内置工具**：
  - `calculator` - 数学计算
  - `get_current_time` - 获取时间
  - `get_current_timestamp` - 获取时间戳
  - `word_counter` - 文本统计
  - `ascii_art_generator` - ASCII 艺术字
- **工具绑定**：通过 `llm.bind_tools()` 绑定工具到模型
- **简化版本**：`tool_agent_simple.py` 直接调用工具

### 5. RAG 知识库 Agent (rag_agent.py)
- **文档加载**：支持文本、Markdown、PDF 等格式
- **文本分割**：使用 `RecursiveCharacterTextSplitter` 智能分块
- **向量化存储**：使用 Chroma 持久化向量数据库
- **相似度检索**：基于 Embedding 的语义搜索
- **增强回答**：结合检索内容生成准确答案
- **交互模式**：支持 `load`、`add`、`status` 等命令

---

## 🔧 核心实现

### SQLite 持久化存储

**数据库表结构：**
```sql
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    type TEXT NOT NULL,        -- human/ai/system
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**核心类：**
```python
class SQLiteChatMessageHistory:
    @property
    def messages(self) -> list[BaseMessage]:
        """从数据库读取所有消息"""

    def add_messages(self, messages: list[BaseMessage]):
        """批量添加消息"""

    def clear(self):
        """清空当前会话"""
```

### 历史裁剪机制

```python
MAX_HISTORY_MESSAGES = 10  # 保留最近 10 条（约 5 轮对话）

# 裁剪逻辑：保留系统消息 + 最近 N 条对话
if len(messages) > MAX_HISTORY_MESSAGES:
    system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
    other_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
    trimmed_messages = other_messages[-MAX_HISTORY_MESSAGES:]
    # 重新组装
```

---

## 📊 Agent 对比

| 特性 | my_first_agent.py | chat_agent.py |
|------|-------------------|---------------|
| 对话轮次 | 单轮 | 多轮 |
| 历史管理 | 无 | SQLite 持久化 + 自动裁剪 |
| 输出方式 | 一次性 | 流式 |
| 用户隔离 | 无 | 支持 session_id |

---

## 🚀 使用指南

```bash
# 运行单轮对话 Agent
python agents/my_first_agent.py

# 运行多轮对话 Agent
python agents/chat_agent.py

# 运行工具调用 Agent（简化版）
python agents/tool_agent_simple.py

# 运行 RAG 知识库 Agent
python agents/rag_agent.py

# 加载文档并运行 RAG Agent
python agents/rag_agent.py --load knowledge_base

# 单次查询模式
python agents/rag_agent.py --query "你的问题"

# 运行持久化测试
python tests/test_persistence.py

# 运行工具功能测试
python tests/test_tools.py

# 运行 RAG 功能测试
python tests/test_rag.py
```

**交互命令：**
- `exit` / `quit` / `q` - 退出
- `clear` / `cls` - 清空当前会话历史
- `status` / `info` - 查看会话状态
- `load <路径>` - 加载文档目录（RAG 专用）
- `add <文本>` - 直接添加文本到知识库（RAG 专用）

---

## 🔍 常见问题

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `null value for 'choices'` | API_BASE 错误 | 改为 `https://open.bigmodel.cn/api/paas/v4/` |
| `Error code: 429` | 速率限制 | 等待 2-3 分钟后重试 |
| Token 溢出 | 历史过长 | 已通过自动裁剪解决 |

---

## 📝 代码速查

### 创建 LLM
```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="glm-4", temperature=0.7)
```

### 提示词模板
```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是 AI 助手"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])
```

### 添加记忆
```python
from langchain_core.runnables.history import RunnableWithMessageHistory

with_message_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)
```

### 创建工具
```python
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """工具描述（AI 会看到）"""
    result = do_something(param)
    return f"结果: {result}"
```

### 绑定工具到 LLM
```python
# 创建工具列表
tools = [calculator, get_current_time, word_counter]

# 绑定工具
llm_with_tools = llm.bind_tools(tools)

# 创建 Chain
chain = prompt | llm_with_tools
```

### 检查工具调用
```python
response = chain.invoke({"input": user_input})

# 检查是否有工具调用
if hasattr(response, 'tool_calls') and response.tool_calls:
    for tool_call in response.tool_calls:
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        # 执行工具...
```

### RAG 知识库
```python
from rag_agent import RAGAgent

# 创建 RAG Agent
agent = RAGAgent()

# 加载文档目录
agent.load_documents("./knowledge_base")

# 或直接加载文本
agent.load_text("这是一段文本内容", metadata={"source": "manual"})

# 查询
answer = agent.query("你的问题")
```

### 文档加载器
```python
from langchain_community.document_loaders import TextLoader, DirectoryLoader, PyPDFLoader

# 加载单个文本文件
loader = TextLoader("file.txt", autodetect_encoding=True)
documents = loader.load()

# 加载整个目录
loader = DirectoryLoader(
    "./docs",
    glob="**/*.txt",
    loader_cls=TextLoader,
    show_progress=True,
)
```

### 文本分割
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,           # 块大小
    chunk_overlap=50,         # 重叠大小
    length_function=len,
    separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
)
splits = text_splitter.split_documents(documents)
```

### 向量存储
```python
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# 创建 Embedding
embeddings = OpenAIEmbeddings(
    model="embedding-3",
    api_key="your_key",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

# 创建向量数据库
vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory="./chroma_db",
)

# 相似度搜索
docs = vectorstore.similarity_search("问题", k=3)
```

---

## 🎯 开发计划

- [x] 环境配置
- [x] 单轮对话 Agent
- [x] 多轮对话 Agent
- [x] 历史记录管理 + 裁剪
- [x] **SQLite 持久化存储**
- [x] **工具调用（计算器、时间、统计等）**
- [x] **RAG 知识库（向量存储、相似度检索）**
- [ ] 多 Agent 协作

---

## 💡 踩坑记录

| 问题 | 解决方案 |
|------|----------|
| 错误的 API_BASE (`/api/anthropic`) | 改为 `/api/paas/v4/` |
| 历史过长导致 token 溢出 | 添加自动裁剪机制 |
| 导入模块时执行主循环 | 用 `if __name__ == "__main__":` 包裹 |
| LangChain 需要 `add_messages` | 添加批量方法 |
| `create_tool_calling_agent` 导入错误 | 使用 `llm.bind_tools()` 代替 |
| 工具未被调用 | 提示词中明确说明工具用途和使用场景 |
| `tool_calls` 属性不存在 | 使用 `hasattr()` 检查属性是否存在 |
| Embedding 模型错误（400） | 智谱 AI 使用 `embedding-3` 而非 `text-embedding-v3` |
| `DirectoryLoader` 参数错误 | 使用 `loader_kwargs` 传递加载器参数 |
| Chroma 警告（已弃用） | 可安装 `langchain-chroma` 替代（不影响使用） |

---

## 🔐 安全最佳实践

1. **Git 忽略 `.env`** - 永远不提交敏感信息
2. **定期轮换 API Key** - 每 30-90 天更换
3. **最小权限原则** - 为不同环境使用不同的 Key
4. **监控使用量** - 设置预算警报

---

## 📖 学习资源

- [LangChain 官方文档](https://python.langchain.com/)
- [智谱 AI 开放平台](https://open.bigmodel.cn/)

**核心概念：**
- **LLM** - 大语言模型
- **Chain** - 链式调用
- **Agent** - 智能体（能自主决策和调用工具）
- **Memory** - 记忆机制
- **Tool Calling** - 工具调用（让 AI 能执行实际操作）
- **RAG** - 检索增强生成

---

**祝开发顺利！加油！💪**
