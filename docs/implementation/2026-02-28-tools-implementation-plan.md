# 工具功能完整实现 - 实施计划

**创建日期**: 2026-02-28
**作者**: Claude Sonnet 4.5
**状态**: 待执行
**预计时间**: 2-3小时

---

## 📋 总览

本实施计划描述了如何完整实现两个核心工具：

1. **DuckDuckGoSearchTool** - 免费的实时网络搜索（无需API Key）
2. **LLMMathTool** - 基于LLM的数学计算（复用现有LLMService）

**设计文档**: `docs/plans/2026-02-28-tools-implementation-design.md`

---

## Phase 0: 文档发现（已完成）

### 允许使用的API清单

#### DuckDuckGo搜索（已验证）

**正确的API签名**:
```python
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

# ✅ 正确的初始化方式
searcher = DuckDuckGoSearchResults(
    max_results=5,
    backend="news",
    api_wrapper=DuckDuckGoSearchAPIWrapper(
        time="w",  # ✅ time_range参数在api_wrapper中，不在外层
        max_results=5,
        source="news"
    )
)

# 调用方式
results = searcher.invoke(query)  # ✅ 使用invoke()，不是run()
```

**关键发现**:
- ❌ 设计文档中的错误：`time_range` 不能直接传给 `DuckDuckGoSearchResults`
- ✅ 必须通过 `DuckDuckGoSearchAPIWrapper(time="w")` 传入
- ✅ 调用方法：`invoke(query)` 而不是 `run(query)`

**必需依赖**:
```bash
pip install -U duckduckgo-search langchain-community>=0.0.10
```

#### LLMMathChain（已验证）

**正确的API签名**:
```python
from langchain.chains import LLMMathChain

# ✅ 正确的初始化方式
chain = LLMMathChain.from_llm(
    llm=llm_service.provider.client,  # ✅ 访问ChatOpenAI实例
    verbose=False
)

# 调用方式
result = chain.run(expression)  # ✅ 使用run()
```

**LLMService访问路径**:
```python
# 架构层次
LLMService
  └── provider: OpenAICompatibleProvider
      └── client: ChatOpenAI (来自langchain_openai)

# 访问代码
langchain_llm = llm_service.provider.client
```

#### BaseTool模式（已验证）

**项目中的标准模式**（来自 `services/tavily_tool.py`）:
```python
from langchain.tools import BaseTool

class MyTool(BaseTool):
    name = "tool_name"  # 必需：snake_case
    description = "工具描述"  # 必需

    def __init__(self, config=None):
        # 初始化逻辑
        pass

    def _run(self, input: str) -> str:
        # 同步实现
        pass

    async def _arun(self, input: str) -> str:
        # 异步实现
        return self._run(input)
```

**必需属性**:
- `name`: str（工具名称，snake_case）
- `description`: str（工具描述，给LLM看）
- `_run()`: 同步执行方法
- `_arun()`: 异步执行方法

### 反模式（避免使用）

❌ **错误1**: 直接传 `time_range` 给 `DuckDuckGoSearchResults`
```python
# ❌ 错误（设计文档中的bug）
searcher = DuckDuckGoSearchResults(
    max_results=5,
    time_range="w",  # ❌ 这个参数不存在
    backend="news"
)
```

❌ **错误2**: 使用不存在的 `run()` 方法
```python
# ❌ 错误
results = searcher.run(query)

# ✅ 正确
results = searcher.invoke(query)
```

❌ **错误3**: 依赖不完整
```bash
# ❌ 不完整
pip install langchain-community

# ✅ 完整
pip install -U duckduckgo-search langchain-community>=0.0.10
```

### 参考文档来源

| 来源 | 路径 | 用途 |
|------|------|------|
| LangChain源码 | `.venv/lib/python3.12/site-packages/langchain_community/tools/ddg_search/tool.py` | API签名验证 |
| LangChain源码 | `.venv/lib/python3.12/site-packages/langchain_community/utilities/duckduckgo_search.py` | APIWrapper参数 |
| 现有工具 | `services/tavily_tool.py` | BaseTool模式 |
| 现有服务 | `services/llm_service.py` | LLMService架构 |
| 设计文档 | `docs/plans/2026-02-28-tools-implementation-design.md` | 实现规范 |

---

## Phase 1: 安装依赖

### 目标
安装 `duckduckgo-search` 和验证 `langchain-community` 版本

### 任务清单

**Task 1.1**: 安装 duckduckgo-search
```bash
pip install -U duckduckgo-search
```

**Task 1.2**: 验证 langchain-community 版本
```bash
pip show langchain-community
# 确保版本 >= 0.0.10
```

**Task 1.3**: 更新 requirements.txt
```txt
# 在文件末尾添加：
duckduckgo-search>=5.3.0
```

**文件**: `requirements.txt`

### 验证清单

- [ ] `pip list | grep duckduckgo` 显示 `duckduckgo-search 5.x.x`
- [ ] `pip show langchain-community` 显示版本 >= 0.4.1
- [ ] `requirements.txt` 包含 `duckduckgo-search>=5.3.0`

### 文档参考

- 无特殊参考，标准pip安装流程

---

## Phase 2: 创建 DuckDuckGoSearchTool

### 目标
创建 `services/duckduckgo_tool.py`，实现完整的搜索功能

### 任务清单

**Task 2.1**: 创建文件 `services/duckduckgo_tool.py`

**内容来源**: 复制以下代码（基于已验证的API）

```python
"""
DuckDuckGo 搜索工具集成

使用 DuckDuckGo API 进行实时网络搜索，无需 API Key。
"""
import os
from typing import Optional
from langchain.tools import BaseTool
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper


class DuckDuckGoSearchTool(BaseTool):
    """
    DuckDuckGo 搜索工具

    提供免费的实时网络搜索能力，无需 API Key。

    参考:
    - https://python.langchain.com/docs/integrations/tools/ddg/
    """

    name = "duckduckgo_search"
    description = "搜索实时网络信息，获取最新数据和答案"

    def __init__(
        self,
        max_results: int = 5,
        time_range: str = "w",
        backend: str = "news"
    ):
        """
        初始化 DuckDuckGo 搜索工具

        Args:
            max_results: 最大结果数（默认5）
            time_range: 时间范围（d/day, w/week, m/month, y/year）
            backend: 搜索类型（news, text）
        """
        self.max_results = max_results
        self.time_range = time_range
        self.backend = backend

        # ✅ 正确的初始化方式（来自Phase 0文档发现）
        self.searcher = DuckDuckGoSearchResults(
            max_results=max_results,
            backend=backend,
            api_wrapper=DuckDuckGoSearchAPIWrapper(
                time=time_range,  # ✅ time参数在api_wrapper中
                max_results=max_results,
                source=backend
            )
        )

    def _run(self, query: str) -> str:
        """
        执行搜索

        Args:
            query: 搜索查询

        Returns:
            str: 搜索结果（格式化字符串）
        """
        try:
            # ✅ 使用invoke()，不是run()
            results = self.searcher.invoke(query)

            # invoke()返回tuple: (formatted_results, raw_results)
            if isinstance(results, tuple):
                formatted_results, _ = results
                return formatted_results
            else:
                return results

        except Exception as e:
            return self._handle_error(e)

    def _handle_error(self, error: Exception) -> str:
        """
        优雅的错误处理

        Args:
            error: 异常对象

        Returns:
            str: 友好的错误信息
        """
        error_msg = str(error).lower()

        if "timeout" in error_msg or "timed out" in error_msg:
            return "搜索超时，请稍后重试"
        elif "rate limit" in error_msg:
            return "搜索频率过高，请稍后再试"
        elif "no results" in error_msg or "0 results" in error_msg:
            return "未找到相关结果"
        else:
            return f"搜索出错: {str(error)}"

    async def _arun(self, query: str) -> str:
        """
        异步执行搜索

        Args:
            query: 搜索查询

        Returns:
            str: 搜索结果
        """
        return self._run(query)
```

**Task 2.2**: 验证文件创建成功
```bash
ls -la services/duckduckgo_tool.py
```

### 文档参考

- API签名验证: `.venv/lib/python3.12/site-packages/langchain_community/tools/ddg_search/tool.py:1-50`
- 设计文档: `docs/plans/2026-02-28-tools-implementation-design.md:161-218`
- BaseTool模式: `services/tavily_tool.py:11-61`

### 验证清单

- [ ] 文件 `services/duckduckgo_tool.py` 已创建
- [ ] 文件包含 `DuckDuckGoSearchTool` 类
- [ ] 类包含 `name` 和 `description` 属性
- [ ] 类包含 `_run()` 和 `_arun()` 方法
- [ ] 代码使用 `DuckDuckGoSearchAPIWrapper(time=...)` 而非直接传 `time_range`
- [ ] 代码使用 `invoke(query)` 而非 `run(query)`

### 反模式检查

```bash
# 确保没有使用错误的参数
grep -n "time_range=" services/duckduckgo_tool.py | grep -v "self.time_range"
# 应该返回空（除了类属性初始化）

# 确保使用了正确的方法
grep -n "\.run(" services/duckduckgo_tool.py | grep -v "_run"
# 应该返回空（除了定义_run方法）
```

---

## Phase 3: 更新 LLMMathTool

### 目标
修改 `services/llm_math_tool.py`，从占位实现改为完整的 LLMMathChain

### 任务清单

**Task 3.1**: 备份原文件
```bash
cp services/llm_math_tool.py services/llm_math_tool.py.backup
```

**Task 3.2**: 修改 `services/llm_math_tool.py`

**内容来源**: 复制以下代码（基于已验证的API）

```python
"""
LLM 数学计算工具

使用 LangChain 的 LLMMathChain 进行复杂数学计算。
"""
from langchain.tools import BaseTool
from langchain.chains import LLMMathChain
from services.llm_service import LLMService
from typing import Optional


class LLMMathTool(BaseTool):
    """
    LLM 数学计算工具

    使用大语言模型进行精确的数学计算。

    复用现有的 LLMService，自动适配租户的 LLM 配置。
    """

    name = "llm_math"
    description = "执行复杂数学计算，包括算术、代数、微积分等"

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        初始化数学工具

        Args:
            llm_service: LLM 服务实例（复用租户配置）
        """
        self.llm_service = llm_service
        self.chain = None

        if llm_service:
            self._initialize_chain()

    def _initialize_chain(self):
        """
        初始化 LLMMathChain

        ✅ 正确的访问路径（来自Phase 0文档发现）
        llm_service.provider.client → ChatOpenAI 实例
        """
        try:
            self.chain = LLMMathChain.from_llm(
                llm=self.llm_service.provider.client,  # ✅ 访问LangChain LLM
                verbose=False
            )
        except Exception as e:
            print(f"⚠️  初始化 LLMMathChain 失败: {e}")

    def set_llm(self, llm_service: LLMService):
        """
        设置/更新 LLM 服务

        Args:
            llm_service: LLM 服务实例
        """
        self.llm_service = llm_service
        self._initialize_chain()
        print("✅ LLM 已设置")

    def _run(self, expression: str) -> str:
        """
        执行数学计算

        Args:
            expression: 数学表达式或问题

        Returns:
            str: 计算结果
        """
        if not self.chain:
            return "错误: 数学工具未初始化，请先配置 LLM"

        try:
            result = self.chain.run(expression)
            return result
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
```

**Task 3.3**: 验证文件修改成功
```bash
diff services/llm_math_tool.py.backup services/llm_math_tool.py
```

### 文档参考

- LLMService架构: `services/llm_service.py:117-124`
- LLMMathChain用法: `docs/plans/2026-02-28-tools-implementation-design.md:223-226`
- 原始占位实现: `services/llm_math_tool.py.backup:1-70`

### 验证清单

- [ ] 备份文件 `services/llm_math_tool.py.backup` 存在
- [ ] 新文件导入 `LLMMathChain` 和 `LLMService`
- [ ] `_initialize_chain()` 使用 `self.llm_service.provider.client`
- [ ] `set_llm()` 方法保持兼容性
- [ ] `_run()` 方法调用 `self.chain.run(expression)`
- [ ] 错误处理返回友好提示

### 反模式检查

```bash
# 确保没有使用错误的LLM访问路径
grep -n "llm_service.llm" services/llm_math_tool.py
# 应该返回空

# 确保使用了正确的访问路径
grep -n "provider.client" services/llm_math_tool.py
# 应该返回: self.llm_service.provider.client
```

---

## Phase 4: 更新工具注册

### 目标
在工具注册处添加 `DuckDuckGoSearchTool`，移除或更新 `TavilySearchTool`

### 任务清单

**Task 4.1**: 检查 `services/tool_registry.py`

查看当前工具注册逻辑，确认是否需要更新。

```bash
grep -n "tavily\|duckduckgo" services/tool_registry.py
```

**Task 4.2**: 更新导入（如需要）

如果有硬编码的工具导入，更新为新的工具。

**Task 4.3**: 检查 `agents/factory.py`

确认工具是否在Agent工厂中注册。

```bash
grep -n "TavilySearchTool\|LLMMathTool" agents/factory.py
```

### 文档参考

- 工具注册: `services/tool_registry.py:1-90`
- Agent工厂: `services/agent_factory.py:1-192`

### 验证清单

- [ ] 旧的 `TavilySearchTool` 导入已移除或注释
- [ ] 新的 `DuckDuckGoSearchTool` 导入已添加（如需要）
- [ ] `LLMMathTool` 导入保持不变

---

## Phase 5: 编写单元测试

### 目标
创建单元测试验证工具功能

### 任务清单

**Task 5.1**: 创建 `tests/test_duckduckgo_tool.py`

**内容来源**: 新建测试文件

```python
import pytest
from services.duckduckgo_tool import DuckDuckGoSearchTool


class TestDuckDuckGoSearchTool:
    """DuckDuckGo 搜索工具测试"""

    def test_tool_initialization(self):
        """测试工具初始化"""
        tool = DuckDuckGoSearchTool()
        assert tool.name == "duckduckgo_search"
        assert tool.max_results == 5
        assert tool.backend == "news"

    def test_basic_search(self):
        """测试基本搜索功能"""
        tool = DuckDuckGoSearchTool(max_results=3)
        result = tool._run("Python programming")

        # 验证返回结果
        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_with_time_range(self):
        """测试带时间范围的搜索"""
        tool = DuckDuckGoSearchTool(time_range="d")  # 最近一天
        result = tool._run("AI news")
        assert isinstance(result, str)

    def test_error_handling_empty_query(self):
        """测试空查询的错误处理"""
        tool = DuckDuckGoSearchTool()
        result = tool._run("")
        # 应该返回某种错误信息或空结果
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_async_search(self):
        """测试异步搜索"""
        tool = DuckDuckGoSearchTool()
        result = await tool._arun("Python")
        assert isinstance(result, str)
```

**Task 5.2**: 创建 `tests/test_llm_math_tool.py`

**内容来源**: 新建测试文件

```python
import pytest
from services.llm_math_tool import LLMMathTool
from services.llm_service import LLMService


class TestLLMMathTool:
    """LLM 数学计算工具测试"""

    def test_tool_initialization(self):
        """测试工具初始化（无 LLM）"""
        tool = LLMMathTool()
        assert tool.name == "llm_math"
        assert tool.chain is None

    def test_tool_with_llm(self):
        """测试带LLM的初始化"""
        # 需要mock LLMService或使用真实实例
        # 这里先跳过，需要数据库连接
        pytest.skip("需要租户上下文")

    def test_error_handling_no_llm(self):
        """测试无LLM时的错误处理"""
        tool = LLMMathTool()
        result = tool._run("2 + 2")
        assert "错误" in result or "未初始化" in result
```

**Task 5.3**: 运行测试
```bash
pytest tests/test_duckduckgo_tool.py -v
pytest tests/test_llm_math_tool.py -v
```

### 文档参考

- 测试模式: `tests/test_tool_adapter.py:1-200`
- 测试模式: `tests/test_tool_using_agent.py:1-79`

### 验证清单

- [ ] `tests/test_duckduckgo_tool.py` 已创建
- [ ] `tests/test_llm_math_tool.py` 已创建
- [ ] DuckDuckGo测试至少通过3个测试用例
- [ ] LLMMath测试至少通过2个测试用例

---

## Phase 6: 手动功能验证

### 目标
通过实际API调用验证工具功能

### 任务清单

**Task 6.1**: 启动后端服务
```bash
cd backend
python -m uvicorn api.main:app --reload --port 8000
```

**Task 6.2**: 获取认证Token
```bash
# 登录获取token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

**Task 6.3**: 测试DuckDuckGo搜索

```bash
# 保存以下为 test_search.sh
curl -X POST http://localhost:8000/api/chat/sse \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "搜索今天的科技新闻",
    "agent_type": "react_agent",
    "session_id": "test-search-001"
  }'
```

**Task 6.4**: 测试LLM数学计算

```bash
# 保存以下为 test_math.sh
curl -X POST http://localhost:8000/api/chat/sse \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "计算 123 * 456 + 789",
    "agent_type": "react_agent",
    "session_id": "test-math-001"
  }'
```

### 验证清单

**DuckDuckGo搜索**:
- [ ] 返回搜索结果（包含标题、链接、摘要）
- [ ] 响应时间 < 5秒
- [ ] 无异常错误

**LLM数学计算**:
- [ ] 返回正确答案（56367）
- [ ] 响应时间 < 10秒
- [ ] 无异常错误

---

## Phase 7: 文档更新

### 目标
更新项目文档，记录实施结果

### 任务清单

**Task 7.1**: 更新进度文件
```bash
vim docs/progress/phase3-progress.md
```

添加内容：
```markdown
### ✅ Task #N: 实现完整的工具功能 (2026-02-28)

#### 完成内容
- 创建 DuckDuckGoSearchTool（免费网络搜索）
- 更新 LLMMathTool（完整数学计算）
- 编写单元测试
- 手动验证功能

#### 技术特性
- DuckDuckGo: 无需API Key，支持时间范围过滤
- LLMMath: 复用现有LLMService，自动适配租户配置
- 优雅降级: 错误时返回友好提示

#### 验证结果
- DuckDuckGo搜索: ✅ 返回准确结果
- LLMMath计算: ✅ 返回正确答案
- 性能: 搜索 < 5s, 计算 < 10s

#### 文件清单
| 文件 | 状态 | 说明 |
|------|------|------|
| services/duckduckgo_tool.py | 新建 | DuckDuckGo搜索工具 |
| services/llm_math_tool.py | 修改 | 数学计算工具（完整实现） |
| services/llm_math_tool.py.backup | 备份 | 原占位实现 |
| tests/test_duckduckgo_tool.py | 新建 | 搜索工具测试 |
| tests/test_llm_math_tool.py | 新建 | 数学工具测试 |
| requirements.txt | 修改 | 添加 duckduckgo-search |
```

**Task 7.2**: 记录开发者日志
```bash
# 创建今日日志（如果还没有）
cp docs/DEVELOPER_LOGS/TEMPLATE.md docs/DEVELOPER_LOGS/2026/$(date +%Y-%m-%d).md
vim docs/DEVELOPER_LOGS/2026/$(date +%Y-%m-%d).md
```

添加内容：
```markdown
## 🎯 完成的工作

### 实现完整的工具功能
- 创建 DuckDuckGoSearchTool（免费搜索，无需API Key）
- 更新 LLMMathTool（完整的LLMMathChain集成）
- 编写单元测试并通过验证
- 手动测试API功能正常

## 📁 修改的文件

### 新建文件
- `services/duckduckgo_tool.py` - DuckDuckGo搜索工具（60行）
- `tests/test_duckduckgo_tool.py` - 搜索工具单元测试
- `tests/test_llm_math_tool.py` - 数学工具单元测试

### 修改文件
- `services/llm_math_tool.py` - 从占位实现改为完整实现（70行 → 90行）
- `requirements.txt` - 添加 duckduckgo-search>=5.3.0

## 💡 技术要点

### DuckDuckGo集成
- 使用 `DuckDuckGoSearchAPIWrapper(time="w")` 设置时间范围
- 调用方法：`invoke(query)` 而非 `run(query)`
- 返回格式：tuple (formatted_results, raw_results)

### LLMMathChain集成
- LLM访问路径：`llm_service.provider.client`
- 初始化：`LLMMathChain.from_llm(llm=...)`
- 保持 `set_llm()` 方法兼容性
```

**Task 7.3**: 更新 INDEX.md（如需要）
```bash
vim docs/INDEX.md
```

在"实施计划"部分添加：
```markdown
- [工具功能完整实现](implementation/2026-02-28-tools-implementation-plan.md) - DuckDuckGo搜索 + LLMMath计算
```

### 验证清单

- [ ] `docs/progress/phase3-progress.md` 已更新
- [ ] `docs/DEVELOPER_LOGS/2026/2026-02-28.md` 已更新
- [ ] `docs/INDEX.md` 已更新（可选）

---

## Phase 8: 代码提交

### 目标
提交所有更改到Git仓库

### 任务清单

**Task 8.1**: 查看变更
```bash
git status
git diff --stat
```

**Task 8.2**: 添加所有文件
```bash
git add services/duckduckgo_tool.py
git add services/llm_math_tool.py
git add tests/test_duckduckgo_tool.py
git add tests/test_llm_math_tool.py
git add requirements.txt
git add docs/
```

**Task 8.3**: 提交代码
```bash
git commit -m "feat(phase3): implement complete tool functionality

- Add DuckDuckGoSearchTool (free web search, no API key required)
  - Use DuckDuckGoSearchAPIWrapper for time range filtering
  - Support max_results, backend (news/text) configuration
  - Graceful error handling (timeout, rate limit)

- Update LLMMathTool (full LLMMathChain integration)
  - Integrate with existing LLMService
  - Access LangChain LLM via llm_service.provider.client
  - Maintain set_llm() method for backward compatibility

- Add unit tests for both tools
- Update requirements.txt with duckduckgo-search>=5.3.0
- Update documentation (progress, developer logs)

Testing:
- DuckDuckGo search: returns accurate results, < 5s response
- LLMMath calculation: returns correct answers, < 10s response

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Task 8.4**: 推送到远程（可选）
```bash
git push origin main
```

### 验证清单

- [ ] 所有文件已添加到Git
- [ ] Commit message 符合规范（feat, 清晰描述）
- [ ] 包含 Co-Authored-By
- [ ] 代码已推送到远程（可选）

---

## Phase 9: 最终验证

### 目标
确认所有实施步骤正确完成，无反模式

### 任务清单

**Task 9.1**: 检查反模式

```bash
# 检查1: 确保没有使用错误的time_range参数
grep -rn "time_range=" services/duckduckgo_tool.py | grep -v "self.time_range" | grep DuckDuckGoSearchResults
# 应该返回空

# 检查2: 确保使用了正确的invoke方法
grep -n "\.run(" services/duckduckgo_tool.py | grep -v "_run\|_arun"
# 应该返回空

# 检查3: 确保使用了正确的LLM访问路径
grep -n "llm_service.llm" services/llm_math_tool.py
# 应该返回空

# 检查4: 确保使用了provider.client
grep -n "provider\.client" services/llm_math_tool.py
# 应该返回: self.llm_service.provider.client
```

**Task 9.2**: 运行所有测试
```bash
pytest tests/test_duckduckgo_tool.py -v
pytest tests/test_llm_math_tool.py -v
```

**Task 9.3**: 文档完整性检查

```bash
# 确保设计文档存在
ls -la docs/plans/2026-02-28-tools-implementation-design.md

# 确保实施计划存在
ls -la docs/implementation/2026-02-28-tools-implementation-plan.md

# 确保进度文件已更新
grep -n "DuckDuckGoSearchTool\|LLMMathTool" docs/progress/phase3-progress.md
```

**Task 9.4**: 依赖检查

```bash
# 确保duckduckgo-search已安装
pip list | grep duckduckgo

# 确保langchain-community版本正确
pip show langchain-community | grep Version
```

### 验证清单

**反模式检查**:
- [ ] 没有使用错误的 `time_range=` 参数
- [ ] 使用了正确的 `invoke()` 方法
- [ ] 使用了正确的 LLM 访问路径 `provider.client`
- [ ] 没有使用 `llm_service.llm`

**功能验证**:
- [ ] DuckDuckGo搜索测试通过
- [ ] LLMMath计算测试通过
- [ ] 手动API测试成功

**文档完整性**:
- [ ] 设计文档已保存
- [ ] 实施计划已保存
- [ ] 进度文件已更新
- [ ] 开发者日志已更新

**代码质量**:
- [ ] 所有文件已提交
- [ ] Commit message 符合规范
- [ ] 代码已推送到远程（可选）

---

## 📊 总结

### 预计时间
- Phase 1: 5分钟（安装依赖）
- Phase 2: 15分钟（创建DuckDuckGo工具）
- Phase 3: 10分钟（更新LLMMath工具）
- Phase 4: 5分钟（更新工具注册）
- Phase 5: 20分钟（编写单元测试）
- Phase 6: 15分钟（手动验证）
- Phase 7: 10分钟（文档更新）
- Phase 8: 5分钟（代码提交）
- Phase 9: 10分钟（最终验证）

**总计**: 约 1.5-2小时

### 关键成功因素

1. **✅ 遵循Phase 0文档发现** - 使用正确的API签名
2. **✅ 避免反模式** - 不使用设计文档中的错误参数
3. **✅ 复用现有架构** - LLMService、BaseTool模式
4. **✅ 完整测试** - 单元测试 + 手动验证
5. **✅ 文档更新** - 进度文件、开发者日志

### 后续步骤（Phase 4高级能力）

- **Scrapling集成**: 深度网页爬取
  - DuckDuckGo搜索获取URLs
  - Scrapling抓取全文内容
  - 组合提供更强大的搜索能力

- **多租户API Key**: 支持租户级别的搜索配置
  - 数据库字段: `tavily_api_key`
  - 支持切换: DuckDuckGo / Tavily

---

**实施计划版本**: 1.0
**最后更新**: 2026-02-28
**状态**: 待执行
