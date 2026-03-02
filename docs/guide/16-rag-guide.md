# RAG 知识库使用技巧指南

> 📚 基于 `rag_agent.py` 的实战经验总结
> 🎯 帮助你快速上手并优化 RAG 应用

---

## 📖 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [使用技巧](#使用技巧)
4. [最佳实践](#最佳实践)
5. [性能优化](#性能优化)
6. [常见问题](#常见问题)
7. [实战案例](#实战案例)

---

## 🚀 快速开始

### 基础用法

```python
from agents.rag_agent import RAGAgent

# 创建 Agent
agent = RAGAgent()

# 加载文档
agent.load_documents("./knowledge_base")

# 查询
answer = agent.query("你的问题")
```

### 交互模式

```bash
# 直接运行（自动加载已存在的向量库）
python agents/rag_agent.py

# 加载新文档
python agents/rag_agent.py --load ./docs

# 单次查询
python agents/rag_agent.py --query "问题"
```

---

## 🧠 核心概念

### RAG 工作流程

```
用户提问
   ↓
向量化问题
   ↓
相似度检索 (Top-K)
   ↓
拼接上下文
   ↓
LLM 生成回答
```

### 关键参数

| 参数 | 默认值 | 说明 | 调优建议 |
|------|--------|------|----------|
| `CHUNK_SIZE` | 500 | 文档分块大小 | 小文档→300，大文档→800 |
| `CHUNK_OVERLAP` | 50 | 分块重叠大小 | 保持 10-15% 的块大小 |
| `TOP_K` | 3 | 检索文档数量 | 3-5 个最佳，过多会增加 token |
| `embedding_model` | embedding-3 | 向量化模型 | 智谱 AI 使用 `embedding-3` |

---

## 💡 使用技巧

### 1. 文档准备技巧

#### ✅ 好的文档结构

```
knowledge_base/
├── python_basics/
│   ├── 01_intro.txt      # 有编号，逻辑清晰
│   ├── 02_syntax.txt
│   └── 03_oop.txt
├── langchain/
│   ├── chains.md
│   └── agents.md
└── faq/
    └── common_questions.txt
```

#### ❌ 避免的做法

- 文件名全是中文或特殊字符（可能编码问题）
- 单个文件过大（>10MB），建议拆分
- 文档格式混乱（混杂 Markdown、纯文本、HTML）

### 2. 文本分割优化

#### 针对不同内容调整分割器

```python
# 代码文档 - 使用更小的块
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=30,
    separators=["\n\n", "\n", "    ", " "],  # 保留代码缩进
)

# 长篇文档 - 使用更大的块
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=80,
    separators=["\n\n##", "\n\n", "\n", "。", " "],
)

# FAQ 文档 - 按问题分割
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=0,  # FAQ 不需要重叠
    separators=["\n问:", "\nQ:", "\n---", "\n\n"],
)
```

### 3. 元数据增强

为文档添加结构化元数据，提高检索精度：

```python
from langchain_core.documents import Document

doc = Document(
    page_content="Python 是一种编程语言...",
    metadata={
        "source": "python_intro.txt",
        "category": "编程语言",
        "difficulty": "入门",
        "tags": ["python", "基础"],
        "date": "2024-01-01",
    }
)
```

### 4. 检索策略

#### 单轮检索（默认）

```python
docs = vectorstore.similarity_search("问题", k=3)
```

#### 带分数的检索

```python
docs_with_scores = vectorstore.similarity_search_with_score("问题", k=3)
for doc, score in docs_with_scores:
    print(f"相似度: {score:.4f} | {doc.page_content[:50]}...")
```

#### 多查询检索（提高召回率）

```python
# 将复杂问题拆解为多个子问题
questions = [
    "Python 的数据类型有哪些？",
    "Python 变量如何声明？",
]

all_docs = []
for q in questions:
    docs = vectorstore.similarity_search(q, k=2)
    all_docs.extend(docs)

# 去重（基于内容）
unique_docs = list({doc.page_content: doc for doc in all_docs}.values())
```

### 5. 提示词工程

#### 基础提示词模板

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", """你是知识助手，基于以下内容回答：

{context}

如果不知道答案，请明确告知，不要编造。"""),
    ("human", "{question}"),
])
```

#### 进阶提示词技巧

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", """你是专业的技术顾问。

**参考文档：**
{context}

**回答要求：**
1. 必须基于参考文档回答
2. 如果文档信息不足，先说明文档内容，再补充通用知识
3. 引用具体文档来源（如 [文档片段 1]）
4. 对于技术问题，提供代码示例
5. 使用分点陈述，结构清晰

**当前时间：**{current_time}"""),
    ("human", "{question}"),
])
```

---

## 🏆 最佳实践

### 1. 知识库组织

```
project_knowledge/
├── product_docs/          # 产品文档
├── api_reference/         # API 参考
├── troubleshooting/       # 故障排除
├── tutorials/             # 教程
└── faq/                   # 常见问题
```

**好处：**
- 便于管理和更新
- 可以针对不同类别调整检索策略
- 支持增量更新（只需重新加载修改的目录）

### 2. 增量更新策略

```python
# 不要每次都重建整个向量库

# ❌ 低效做法
agent.load_documents("./knowledge_base")  # 重新加载所有文档

# ✅ 高效做法
# 只加载新增或修改的文档
agent.load_documents("./knowledge_base/new_docs")
agent.vectorstore.persist()  # 持久化
```

### 3. 混合检索策略

```python
# 结合关键词检索和语义检索
from langchain.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

# 关键词检索器
bm25_retriever = BM25Retriever.from_documents(splits)

# 语义检索器
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 混合检索器
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.3, 0.7],  # 调整权重
)
```

### 4. 上下文窗口管理

```python
# 避免上下文过长导致 token 超限

def smart_retrieval(question, max_tokens=2000):
    docs = vectorstore.similarity_search(question, k=5)

    selected_docs = []
    total_tokens = 0

    for doc in docs:
        doc_tokens = len(doc.page_content)
        if total_tokens + doc_tokens <= max_tokens:
            selected_docs.append(doc)
            total_tokens += doc_tokens
        else:
            break

    return selected_docs
```

---

## ⚡ 性能优化

### 1. 缓存 Embedding 结果

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_embed(text):
    return embeddings.embed_query(text)
```

### 2. 批量处理

```python
# ✅ 批量 Embedding（更快）
embeddings.embed_documents([
    "文本1",
    "文本2",
    "文本3",
])

# ❌ 逐个 Embedding（慢）
for text in texts:
    embeddings.embed_query(text)
```

### 3. 并行加载

```python
from concurrent.futures import ThreadPoolExecutor

def load_multiple_directories(paths):
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(agent.load_documents, path)
            for path in paths
        ]
        results = [f.result() for f in futures]
    return sum(results)
```

### 4. 硬件加速

```bash
# 安装 GPU 版本的依赖（如果有 GPU）
pip install faiss-gpu  # 使用 Faiss-GPU 加速检索
```

---

## 🔍 常见问题

### Q1: 检索结果不相关？

**原因：**
- 文档分块不合理（上下文被切断）
- 问题表述不清楚
- 相似度阈值设置不当

**解决：**
```python
# 1. 调整分块大小
CHUNK_SIZE = 300  # 减小块大小，提高精度

# 2. 增加重叠
CHUNK_OVERLAP = 100  # 增加上下文连贯性

# 3. 使用更好的分割符
separators=["\n\n##", "\n\n", "\n", "。", " ", ""]
```

### Q2: 回答太简略或太冗长？

**调整提示词：**
```python
# 简略回答
prompt = """用一句话简要回答：{context}\n\n问题：{question}"""

# 详细回答
prompt = """请详细回答，提供完整信息和示例：{context}\n\n问题：{question}"""
```

### Q3: 向量数据库占用空间太大？

**优化方案：**
```python
# 1. 减小向量维度
embeddings = OpenAIEmbeddings(model="embedding-2")  # 更小

# 2. 定期清理
if os.path.exists("./chroma_db"):
    shutil.rmtree("./chroma_db")

# 3. 使用更高效的向量存储
pip install faiss-cpu  # 比 Chroma 更节省空间
```

### Q4: API 调用费用太高？

**省钱技巧：**
```python
# 1. 减少检索数量
TOP_K = 2  # 从 3 降到 2

# 2. 使用更便宜的模型
llm = ChatOpenAI(model="glm-3-turbo")  # 比 glm-4 便宜

# 3. 缓存常见问题答案
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(question):
    return agent.query(question)
```

---

## 📚 实战案例

### 案例 1：技术文档问答系统

```python
# tech_support_agent.py
from agents.rag_agent import RAGAgent

agent = RAGAgent()
agent.load_documents("./tech_docs")

def tech_support_query(question):
    # 添加上下文信息
    enhanced_question = f"""
    作为技术支持工程师，请回答以下问题：
    {question}

    请提供：
    1. 问题原因
    2. 解决步骤
    3. 预防措施
    """
    return agent.query(enhanced_question)
```

### 案例 2：产品知识库

```python
# product_agent.py
from agents.rag_agent import RAGAgent

agent = RAGAgent()

# 分别加载不同产品线
agent.load_documents("./products/series_a")
agent.load_documents("./products/series_b")

def product_query(product_line, question):
    # 在提示词中指定产品线
    enhanced_prompt = f"""
    基于 {product_line} 产品的文档回答：
    {question}
    """
    return agent.query(enhanced_prompt)
```

### 案例 3：学习助手

```python
# study_agent.py
from agents.rag_agent import RAGAgent
import datetime

agent = RAGAgent()
agent.load_documents("./study_materials")

def study_tutor(question, user_level="初级"):
    prompt = f"""
    你是一位{user_level}水平的编程导师。

    学生问题：{question}

    请用适合{user_level}学习者的语言解释，
    并提供相关示例代码。
    """
    return agent.query(prompt)
```

---

## 🎓 进阶技巧

### 1. 重排序（Reranking）

```python
# 检索更多文档，然后重排序
docs = vectorstore.similarity_search(question, k=10)

# 使用交叉编码器重排序
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

reranked_docs = reranker.rank(question, [d.page_content for d in docs])
top_3 = [docs[i] for i, _ in sorted(reranked_docs, key=lambda x: -x[1])[:3]]
```

### 2. 查询扩展

```python
def query_expansion(question):
    # 使用 LLM 生成相似问题
    expansion_prompt = f"""
    生成 3 个与以下问题相关的等价问题：
    {question}

    只输出问题，每行一个。
    """
    related_questions = llm.invoke(expansion_prompt).content.split("\n")

    # 合并检索结果
    all_docs = []
    for q in [question] + related_questions:
        all_docs.extend(vectorstore.similarity_search(q, k=2))

    # 去重
    return list({d.page_content: d for d in all_docs}.values())
```

### 3. 自定义检索器

```python
from langchain_core.retrievers import BaseRetriever

class CustomRetriever(BaseRetriever):
    def _get_relevant_documents(self, query, run_manager):
        # 自定义检索逻辑
        docs = vectorstore.similarity_search(query, k=5)

        # 过滤条件
        filtered = [d for d in docs if self._is_relevant(d, query)]

        return filtered[:3]

    def _is_relevant(self, doc, query):
        # 自定义相关性判断
        score = self._calculate_score(doc, query)
        return score > 0.7
```

---

## 📊 评估指标

### 检索质量评估

```python
def evaluate_retrieval(questions, ground_truth_docs):
    precision_scores = []
    recall_scores = []

    for q, true_docs in zip(questions, ground_truth_docs):
        retrieved = vectorstore.similarity_search(q, k=3)

        # 精确率
        precision = len(set(retrieved) & set(true_docs)) / len(retrieved)
        precision_scores.append(precision)

        # 召回率
        recall = len(set(retrieved) & set(true_docs)) / len(true_docs)
        recall_scores.append(recall)

    return {
        "avg_precision": sum(precision_scores) / len(precision_scores),
        "avg_recall": sum(recall_scores) / len(recall_scores),
    }
```

---

## 🛠️ 调试技巧

### 查看检索结果

```python
# 临时修改 agent.query() 方法
def debug_query(question):
    # 获取检索的文档
    docs = agent.vectorstore.similarity_search(question, k=3)

    print("=" * 50)
    print("检索到的文档：")
    for i, doc in enumerate(docs, 1):
        print(f"\n[文档 {i}]")
        print(f"内容: {doc.page_content[:100]}...")
        print(f"元数据: {doc.metadata}")
    print("=" * 50)

    # 正常查询
    return agent.query(question)
```

### 相似度分数分析

```python
# 查看每个检索文档的相似度分数
docs_with_scores = agent.vectorstore.similarity_search_with_score(
    "你的问题", k=5
)

for doc, score in docs_with_scores:
    print(f"分数: {score:.4f} | {doc.page_content[:50]}")

# 如果所有分数都很高（>0.9），可能需要调整查询
# 如果分数都很低（<0.5），可能知识库中没有相关内容
```

---

## 🎯 总结

### RAG 成功的关键要素

1. **高质量的知识库** - 内容准确、结构清晰
2. **合理的分块策略** - 根据文档类型调整
3. **精准的检索** - 使用合适的 K 值和相似度阈值
4. **优化的提示词** - 引导 AI 生成更好的回答
5. **持续的迭代** - 根据用户反馈调整参数

### 学习路径

```
基础（当前） → 进阶 → 专家
   ↓           ↓        ↓
使用 RAG     重排序    多模态 RAG
调整参数     查询扩展   分布式 RAG
测试效果     混合检索   实时更新
```

---

**祝你成为 RAG 专家！🎉**
