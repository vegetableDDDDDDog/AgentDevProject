# 工具完整实现设计文档

**日期**: 2026-02-28
**作者**: Claude Sonnet 4.5
**状态**: 已批准
**版本**: 1.0

---

## 📋 概述

本文档描述了 Agent PaaS 平台中工具功能的完整实现方案，包括：

1. **DuckDuckGoSearchTool** - 免费的实时网络搜索工具
2. **LLMMathTool** - 基于大语言模型的数学计算工具

**目标**: 替换现有的占位实现，提供完整可用的工具能力。

---

## 🎯 设计目标

1. **零成本** - 使用免费的 DuckDuckGo 搜索，无需 API Key
2. **复用现有架构** - 数学工具复用现有的 LLMService
3. **优雅降级** - 错误时返回友好提示，不中断系统
4. **易于扩展** - 预留多租户配置接口

---

## 🏗️ 架构设计

### 1. DuckDuckGoSearchTool

```
DuckDuckGoSearchTool (继承 BaseTool)
│
├── 初始化
│   ├── 无需 API Key ✅
│   ├── max_results: 5（默认）
│   ├── time_range: 'w'（默认，最近一周）
│   └── backend: 'news'（新闻搜索）
│
├── _run(query)
│   ├── 调用 DuckDuckGoSearchResults.run(query)
│   ├── 返回格式化结果
│   └── 错误处理：超时、限流、解析失败
│
└── 返回格式
    ├── title: 网页标题
    ├── link: 网页链接
    └── snippet: 内容摘要
```

**核心依赖**:
- `langchain-community.tools.DuckDuckGoSearchResults`
- 无需额外 API Key

---

### 2. LLMMathTool

```
LLMMathTool (继承 BaseTool)
│
├── 初始化
│   ├── 接收 LLMService 实例（复用租户配置）
│   ├── 创建 LLMMathChain
│   │   └── from_llm(llm=llm_service.provider.client)
│   └── 验证 LLM 配置
│
├── set_llm(llm_service)
│   └── 动态设置/更新 LLM 服务
│
├── _run(expression)
│   ├── 调用 chain.run(expression)
│   ├── LLM 生成 Python 代码
│   ├── Python REPL 执行计算
│   └── 返回结果
│
└── 错误处理
    ├── LLM 未配置 → 返回配置提示
    └── 计算错误 → LLM 自动处理
```

**核心依赖**:
- `langchain.chains.LLMMathChain`
- `services.llm_service.LLMService`（复用）

---

## 📊 数据流

### 场景1: 网络搜索

```
用户: "今天最新的 AI 新闻"
  ↓
Agent 分析意图 → 选择 duckduckgo_search
  ↓
DuckDuckGoSearchTool._run("今天最新的 AI 新闻")
  ↓
DuckDuckGoSearchResults.run(query)
  ↓
返回搜索结果 (JSON 格式)
  ↓
Agent 生成回答 → 流式返回用户
```

### 场景2: 数学计算

```
用户: "计算 123 * 456 + 789"
  ↓
Agent 分析意图 → 选择 llm_math
  ↓
LLMMathTool._run("123 * 456 + 789")
  ↓
LLMMathChain.run(expression)
  ↓
LLM (glm-4.7) 生成 Python 代码
  ↓
Python REPL 执行代码
  ↓
返回结果: 56367
  ↓
Agent 生成回答 → 返回用户
```

---

## 🔧 实现细节

### DuckDuckGoSearchTool 实现

**文件**: `services/duckduckgo_tool.py`（新建）

```python
from langchain_community.tools import DuckDuckGoSearchResults
from langchain.tools import BaseTool

class DuckDuckGoSearchTool(BaseTool):
    """
    DuckDuckGo 搜索工具

    提供免费的实时网络搜索能力，无需 API Key。
    """

    name = "duckduckgo_search"
    description = "搜索实时网络信息，获取最新数据和答案"

    def __init__(
        self,
        max_results: int = 5,
        time_range: str = "w",
        backend: str = "news"
    ):
        self.max_results = max_results
        self.time_range = time_range
        self.backend = backend

        self.searcher = DuckDuckGoSearchResults(
            max_results=max_results,
            time_range=time_range,
            backend=backend
        )

    def _run(self, query: str) -> str:
        """执行搜索"""
        try:
            results = self.searcher.run(query)
            return results
        except Exception as e:
            return self._handle_error(e)

    def _handle_error(self, error: Exception) -> str:
        """优雅的错误处理"""
        error_msg = str(error)

        if "timeout" in error_msg.lower():
            return "搜索超时，请稍后重试"
        elif "rate limit" in error_msg.lower():
            return "搜索频率过高，请稍后再试"
        else:
            return f"搜索出错: {error_msg}"

    async def _arun(self, query: str) -> str:
        """异步执行搜索"""
        return self._run(query)
```

---

### LLMMathTool 实现

**文件**: `services/llm_math_tool.py`（修改）

```python
from langchain.tools import BaseTool
from langchain.chains import LLMMathChain
from services.llm_service import LLMService
from typing import Optional

class LLMMathTool(BaseTool):
    """
    LLM 数学计算工具

    使用大语言模型进行精确的数学计算。
    """

    name = "llm_math"
    description = "执行复杂数学计算，包括算术、代数、微积分等"

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service
        self.chain = None

        if llm_service:
            self._initialize_chain()

    def _initialize_chain(self):
        """初始化 LLMMathChain"""
        try:
            self.chain = LLMMathChain.from_llm(
                llm=self.llm_service.provider.client,
                verbose=False
            )
        except Exception as e:
            print(f"⚠️  初始化 LLMMathChain 失败: {e}")

    def set_llm(self, llm_service: LLMService):
        """设置/更新 LLM 服务"""
        self.llm_service = llm_service
        self._initialize_chain()
        print("✅ LLM 已设置")

    def _run(self, expression: str) -> str:
        """执行数学计算"""
        if not self.chain:
            return "错误: 数学工具未初始化，请先配置 LLM"

        try:
            result = self.chain.run(expression)
            return result
        except Exception as e:
            return f"计算出错: {str(e)}"

    async def _arun(self, expression: str) -> str:
        """异步执行计算"""
        return self._run(expression)
```

---

## 🔌 集成点

### 需要修改的文件

1. **`services/tavily_tool.py`** → 删除或重命名
2. **`services/duckduckgo_tool.py`** → 新建
3. **`services/llm_math_tool.py`** → 修改
4. **`agents/factory.py`** → 更新工具导入
5. **`requirements.txt`** → 添加依赖

### 依赖安装

```bash
pip install langchain-community>=0.0.10
```

---

## ✅ 测试策略

### 单元测试

**DuckDuckGoSearchTool**:
- 工具初始化
- 基本搜索功能
- 时间范围过滤
- 错误处理

**LLMMathTool**:
- 工具初始化
- LLM 设置
- 基本计算
- 复杂计算

### 集成测试

```bash
# 测试搜索工具
curl -X POST http://localhost:8000/api/chat/sse \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "搜索今天的科技新闻"}'

# 测试数学工具
curl -X POST http://localhost:8000/api/chat/sse \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "计算 3.14 * 100"}'
```

### 验证清单

- [ ] DuckDuckGo 搜索返回准确结果
- [ ] 数学计算返回正确答案
- [ ] 错误处理友好且清晰
- [ ] Agent 正确调用工具
- [ ] 性能符合预期（搜索 < 5s，计算 < 10s）

---

## 📝 实施步骤

1. 安装依赖 (`pip install langchain-community`)
2. 创建 `services/duckduckgo_tool.py`
3. 修改 `services/llm_math_tool.py`
4. 更新 `agents/factory.py`（工具导入）
5. 编写单元测试
6. 手动验证功能
7. 更新文档和进度文件

---

## 🚀 后续扩展

### Phase 4: 高级能力增强

- **Scrapling 集成**: 深度网页爬取
  - DuckDuckGo 搜索获取 URLs
  - Scrapling 抓取网页全文
  - 组合提供更强大的搜索能力

- **多租户 API Key**: 支持租户级别的搜索配置
  - 数据库字段: `tavily_api_key`
  - 支持切换: DuckDuckGo / Tavily

---

## 📚 参考资料

- [DuckDuckGo Search - LangChain](https://python.langchain.com/docs/integrations/tools/ddg/)
- [LLMMathChain - LangChain](https://python.langchain.com/docs/chains/llm_math_chain/)
- [项目文档索引](../INDEX.md)

---

**审批记录**:
- 2026-02-28: 设计文档创建并批准
- 下一步: 调用 writing-plans skill 创建实施计划
