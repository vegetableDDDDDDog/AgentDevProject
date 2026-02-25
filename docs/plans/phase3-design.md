# Agent PaaS 平台 - Phase 3 设计方案

> **目标**: 为 Agent PaaS 平台增加工具调用能力，让 Agent 从"聊天机器人"进化为"生产力平台"
> **日期**: 2026-02-25
> **阶段**: Phase 3 - 工具调用能力增强 (Tool Calling Enhancement)

---

## 1. 背景与目标

### 1.1 当前状态

**Phase 2 已完成**：
- ✅ 多租户架构（PostgreSQL + 行级隔离）
- ✅ JWT 认证授权
- ✅ 真实 LLM 集成（智谱AI）
- ✅ 前端 UI（React + TypeScript）
- ✅ 监控体系（Prometheus + OpenTelemetry）

**现有 Agent 能力**：
- 多轮对话（LLMChatAgent）
- 单轮对话（LLMSingleTurnAgent）
- 多 Agent 编排（AgentOrchestrator）

**当前局限性**：
- Agent 只能"聊天"，无法执行实际任务
- 无法访问实时信息（受限于 LLM 训练数据截止日期）
- 无法处理用户上传的文件
- 无法调用第三方 API

### 1.2 Phase 3 目标

**核心目标**：通过工具调用能力，让 Agent 成为真正的生产力工具

**关键价值**：
1. **从"虚"到"实"**：Agent 可以操作实际数据，而不仅仅是生成文本
2. **验证多租户隔离**：工具调用是测试隔离机制的"深水区"
3. **差异化竞争力**：Function Calling 是 PaaS 平台的核心能力

### 1.3 设计原则

- 🛡️ **多租户隔离**：所有工具调用必须受租户隔离约束
- 📊 **可观测性**：工具调用必须被监控、计费、审计
- 🔌 **可扩展性**：支持标准工具和自定义工具
- ⚡ **渐进式开发**：先快速落地核心能力

---

## 2. 技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────┐
│           Frontend Layer                    │
│  - 工具调用状态展示                          │
│  - 工具配置页面                              │
│  - SSE 事件流                                │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│           API Layer                         │
│  - GET /api/v1/tools - 工具列表             │
│  - GET /api/v1/tools/usage - 使用统计       │
│  - POST /api/v1/chat/completions - 对话     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Tool Adapter Layer (NEW)            │
│  - ToolAdapter - 多租户适配器               │
│  - ToolRegistry - 工具注册表                │
│  - ToolExecutionContext - 执行上下文        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         LangChain Tools                     │
│  - TavilySearchResults                      │
│  - LLMMathChain                             │
│  - FileProcessingToolkit                    │
│  - RequestsToolkit                          │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Infrastructure                      │
│  - PostgreSQL - 工具调用日志                │
│  - Redis - 配额缓存                         │
│  - Prometheus - 监控指标                    │
└─────────────────────────────────────────────┘
```

### 2.2 核心组件设计

#### 2.2.1 ToolAdapter - 多租户适配器

```python
# services/tool_adapter.py
from langchain.tools import BaseTool
from tenants import get_tenant_context

class ToolAdapter(BaseTool):
    """
    为 LangChain 工具注入多租户能力的适配器

    核心职责：
    1. 配额检查 - 调用前检查租户配额
    2. 执行工具 - 调用底层工具
    3. 记录指标 - 记录成功/失败、执行时间
    4. 审计日志 - 记录工具调用日志
    """

    def __init__(
        self,
        tool: BaseTool,
        tenant_context: TenantContext,
        db: Session
    ):
        self.tool = tool
        self.tenant_context = tenant_context
        self.db = db
        self.name = tool.name
        self.description = tool.description

    async def _arun(self, *args, **kwargs) -> str:
        """执行工具调用（带多租户保护）"""

        # 1. 配额检查
        await self._check_quota()

        # 2. 记录开始时间
        start_time = time.time()

        # 3. 执行工具
        try:
            result = await self.tool._arun(*args, **kwargs)

            # 4. 记录成功指标
            execution_time = time.time() - start_time
            await self._record_metrics(
                success=True,
                execution_time=execution_time
            )

            # 5. 写入审计日志
            await self._write_audit_log(
                input=kwargs,
                output=result,
                status='success',
                execution_time_ms=int(execution_time * 1000)
            )

            return result

        except Exception as e:
            # 记录失败指标
            execution_time = time.time() - start_time
            await self._record_metrics(
                success=False,
                error=str(e),
                execution_time=execution_time
            )

            # 写入错误日志
            await self._write_audit_log(
                input=kwargs,
                output=None,
                status='error',
                error_message=str(e),
                execution_time_ms=int(execution_time * 1000)
            )

            raise

    async def _check_quota(self):
        """检查工具调用配额"""
        quota_service = QuotaService(self.db)
        await quota_service.check_tool_quota(
            tenant_id=self.tenant_context.tenant_id,
            tool_name=self.tool.name
        )

    async def _record_metrics(
        self,
        success: bool,
        error: str = None,
        execution_time: float = 0
    ):
        """记录工具调用指标"""
        metrics = get_metrics_store()

        # 计数器
        metrics.tool_calls_total.labels(
            tenant_id=self.tenant_context.tenant_id,
            tool_name=self.tool.name,
            status='success' if success else 'error'
        ).inc()

        # 直方图
        metrics.tool_execution_duration.labels(
            tenant_id=self.tenant_context.tenant_id,
            tool_name=self.tool.name
        ).observe(execution_time)

    async def _write_audit_log(self, **kwargs):
        """写入审计日志到数据库"""
        log = ToolCallLog(
            tenant_id=self.tenant_context.tenant_id,
            tool_name=self.tool.name,
            **kwargs
        )
        self.db.add(log)
        await self.db.commit()
```

#### 2.2.2 ToolRegistry - 工具注册表

```python
# services/tool_registry.py
from typing import List, Dict
from langchain.tools import TavilySearchResults, LLMMathChain
from tools.file_toolkit import FileProcessingToolkit
from tools.requests_toolkit import RequestsToolkit

class ToolRegistry:
    """
    租户级别的工具注册表

    核心职责：
    1. 管理内置标准工具
    2. 根据租户配置返回可用工具列表
    3. 为每个工具创建多租户适配器
    """

    def __init__(self):
        self._builtin_tools: Dict[str, BaseTool] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """注册内置标准工具"""
        self._builtin_tools = {
            'tavily_search': TavilySearchResults,
            'llm_math': LLMMathChain,
            'file_processor': FileProcessingToolkit,
            'requests_get': RequestsToolkit.Get,
            'requests_post': RequestsToolkit.Post,
        }

    def get_tools_for_tenant(
        self,
        tenant_context: TenantContext,
        db: Session
    ) -> List[ToolAdapter]:
        """
        根据租户配置返回可用工具列表

        租户配置示例：
        {
          "enable_search": true,
          "enable_math": true,
          "enable_file_processing": true,
          "enable_api_calls": true,
          "tavily_api_key": "tvly-xxx",
          "max_file_size_mb": 10
        }
        """
        tools = []
        settings = tenant_context.settings

        # 网络搜索（默认开启）
        if settings.get('enable_search', True):
            tavily_tool = self._builtin_tools['tavily_search'](
                api_key=settings.get('tavily_api_key', get_default_tavily_key())
            )
            tools.append(ToolAdapter(tavily_tool, tenant_context, db))

        # 数学计算（默认开启）
        if settings.get('enable_math', True):
            math_tool = self._builtin_tools['llm_math']()
            tools.append(ToolAdapter(math_tool, tenant_context, db))

        # 文件处理
        if settings.get('enable_file_processing', True):
            file_tool = self._builtin_tools['file_processor'](
                max_size_mb=settings.get('max_file_size_mb', 10)
            )
            tools.append(ToolAdapter(file_tool, tenant_context, db))

        # API 调用
        if settings.get('enable_api_calls', True):
            get_tool = self._builtin_tools['requests_get'](
                allowed_domains=settings.get('allowed_domains', [])
            )
            post_tool = self._builtin_tools['requests_post'](
                allowed_domains=settings.get('allowed_domains', [])
            )
            tools.extend([
                ToolAdapter(get_tool, tenant_context, db),
                ToolAdapter(post_tool, tenant_context, db)
            ])

        return tools

    def get_tool_info(self, tool_name: str) -> Dict:
        """获取工具信息"""
        if tool_name in self._builtin_tools:
            tool_class = self._builtin_tools[tool_name]
            return {
                'name': tool_name,
                'class': tool_class.__name__,
                'description': tool_class.__doc__
            }
        return None
```

#### 2.2.3 ToolUsingAgent - 工具使用 Agent

```python
# agents/tool_using_agent.py
from agents.base_agent import BaseAgent
from services.tool_registry import ToolRegistry
from services.llm_service import LLMService

class ToolUsingAgent(BaseAgent):
    """
    支持工具调用的 Agent

    能力：
    1. 自动选择合适的工具
    2. 规划多步任务
    3. 整合工具结果
    """

    def __init__(
        self,
        name: str,
        role: str,
        tenant_context: TenantContext,
        db: Session
    ):
        super().__init__(name, role)
        self.tenant_context = tenant_context
        self.db = db
        self.tool_registry = ToolRegistry()

    async def execute(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行任务（可调用工具）"""

        # 1. 获取租户可用工具
        tools = self.tool_registry.get_tools_for_tenant(
            self.tenant_context,
            self.db
        )

        # 2. 创建 LLM 实例
        llm_service = LLMService(self.tenant_context)
        llm = llm_service.get_llm()

        # 3. 创建 LangChain Agent（带工具）
        from langchain.agents import initialize_agent, AgentType

        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS,  # Function Calling
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            early_stopping_method='generate'
        )

        # 4. 执行任务
        result = await agent.arun(
            task,
            callbacks=[self._get_tool_callback()]
        )

        return {
            'context': context,
            'done': True,
            'result': result
        }

    def _get_tool_callback(self):
        """获取工具调用回调（用于 SSE 推送）"""
        from langchain.callbacks import BaseCallbackHandler

        class ToolCallbackHandler(BaseCallbackHandler):
            def __init__(self, tenant_id: str):
                self.tenant_id = tenant_id

            def on_tool_start(
                self,
                serialized: Dict,
                input_str: str,
                **kwargs
            ):
                """工具开始调用"""
                # 发送 SSE 事件
                send_sse_event(self.tenant_id, {
                    'type': 'tool_start',
                    'tool_name': serialized.get('name'),
                    'input': input_str,
                    'timestamp': time.time()
                })

            def on_tool_end(
                self,
                serialized: Dict,
                output_str: str,
                **kwargs
            ):
                """工具调用结束"""
                send_sse_event(self.tenant_id, {
                    'type': 'tool_end',
                    'tool_name': serialized.get('name'),
                    'output': output_str,
                    'timestamp': time.time()
                })

        return ToolCallbackHandler(self.tenant_context.tenant_id)

    def get_capabilities(self) -> List[str]:
        """返回能力列表"""
        tools = self.tool_registry.get_tools_for_tenant(
            self.tenant_context,
            self.db
        )
        return [
            f"可以使用工具: {', '.join([t.name for t in tools])}",
            "支持自动规划多步任务",
            "支持整合多个工具的结果"
        ]
```

---

## 3. 标准工具集成

### 3.1 Tavily 搜索工具

**用途**：实时网络搜索，解决 LLM 知识时效性问题

**LangChain 集成**：
```python
from langchain.tools import TavilySearchResults

tavily_tool = TavilySearchResults(
    api_key=os.getenv('TAVILY_API_KEY'),
    max_results=5,
    search_depth='basic',
    include_domains=[],
    exclude_domains=[]
)
```

**租户配置**：
```json
{
  "enable_search": true,
  "tavily_api_key": "tvly-xxx"  // 可选，使用平台默认
}
```

**隔离性**：
- ✅ 每次搜索都记录到租户指标
- ✅ API 调用计入租户配额
- ✅ 搜索日志审计

### 3.2 LLM 数学工具

**用途**：复杂数学计算，解决大模型计算不准问题

**LangChain 集成**：
```python
from langchain.chains import LLMMathChain

math_tool = LLMMathChain(
    llm=llm,
    verbose=True
)
```

**租户配置**：
```json
{
  "enable_math": true
}
```

**隔离性**：
- ✅ 计算过程记录到日志
- ✅ 复杂度计入租户配额

### 3.3 文件处理工具集

**用途**：CSV、PDF、TXT 文件读取和处理

**自定义实现**：
```python
# tools/file_toolkit.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class FileProcessingToolkit(BaseTool):
    """文件处理工具集"""

    name = "file_processor"
    description = """
    用于处理用户上传的文件。
    支持格式：CSV, PDF, TXT, Markdown
    操作：读取内容、提取数据、统计信息
    """

    def _run(
        self,
        file_path: str,
        operation: str = "read"
    ) -> str:
        """执行文件处理"""

        # 1. 验证文件路径（租户隔离）
        self._validate_file_path(file_path)

        # 2. 根据操作类型处理
        if operation == "read":
            return self._read_file(file_path)
        elif operation == "csv_stats":
            return self._csv_stats(file_path)
        elif operation == "pdf_extract":
            return self._pdf_extract(file_path)

    def _validate_file_path(self, file_path: str):
        """验证文件路径在租户目录内"""
        tenant_dir = get_tenant_upload_dir()
        if not file_path.startswith(tenant_dir):
            raise SecurityError("文件路径不在租户目录内")
```

**租户配置**：
```json
{
  "enable_file_processing": true,
  "max_file_size_mb": 10
}
```

**隔离性**：
- ✅ 文件存储在租户隔离目录：`/uploads/{tenant_id}/`
- ✅ 文件大小限制
- ✅ 文件类型白名单

### 3.4 HTTP API 调用工具

**用途**：调用第三方 REST API

**自定义实现**：
```python
# tools/requests_toolkit.py
import requests
from langchain.tools import BaseTool

class RequestsGetTool(BaseTool):
    """HTTP GET 请求工具"""

    name = "requests_get"
    description = """
    向指定的 URL 发送 HTTP GET 请求。
    用于获取实时数据（天气、股票、新闻等）
    """

    def _run(
        self,
        url: str,
        params: dict = None,
        headers: dict = None
    ) -> str:
        """执行 HTTP GET"""

        # 1. 验证域名白名单
        self._check_domain_allowed(url)

        # 2. 发送请求
        response = requests.get(url, params=params, headers=headers)

        # 3. 记录调用
        self._log_api_call(url, response.status_code)

        return response.text

    def _check_domain_allowed(self, url: str):
        """检查域名是否在白名单"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        allowed = self.tenant_context.settings.get('allowed_domains', [])
        if allowed and domain not in allowed:
            raise SecurityError(f"域名 {domain} 不在白名单中")
```

**租户配置**：
```json
{
  "enable_api_calls": true,
  "allowed_domains": ["api.weather.com", "api.finance.com"]
}
```

**隔离性**：
- ✅ 域名白名单限制
- ✅ 请求频率限制
- ✅ 请求日志审计

---

## 4. API 设计

### 4.1 工具列表端点

**获取租户可用工具列表**

```http
GET /api/v1/tools
Authorization: Bearer <access_token>
```

**响应**：
```json
{
  "tools": [
    {
      "name": "tavily_search",
      "display_name": "网络搜索",
      "description": "搜索实时网络信息",
      "enabled": true,
      "quota_limit": 1000,
      "quota_used": 45,
      "quota_remaining": 955
    },
    {
      "name": "llm_math",
      "display_name": "数学计算",
      "description": "复杂数学计算",
      "enabled": true,
      "quota_limit": null,
      "quota_used": null
    },
    {
      "name": "file_processor",
      "display_name": "文件处理",
      "description": "处理 CSV、PDF、TXT 文件",
      "enabled": true,
      "max_file_size_mb": 10
    },
    {
      "name": "requests_get",
      "display_name": "API 调用",
      "description": "调用第三方 REST API",
      "enabled": true,
      "allowed_domains": ["api.weather.com"]
    }
  ]
}
```

### 4.2 工具使用统计

**获取工具调用统计**

```http
GET /api/v1/tools/usage
Authorization: Bearer <access_token>
```

**响应**：
```json
{
  "total_calls": 1234,
  "by_tool": {
    "tavily_search": 856,
    "llm_math": 378,
    "file_processor": 145,
    "requests_get": 201
  },
  "by_date": {
    "2026-02-25": 45,
    "2026-02-24": 67,
    "2026-02-23": 89
  },
  "success_rate": 0.98,
  "avg_execution_time_ms": 1234
}
```

### 4.3 工具调用日志

**查询工具调用日志**

```http
GET /api/v1/tools/logs?tool_name=tavily_search&limit=10
Authorization: Bearer <access_token>
```

**响应**：
```json
{
  "logs": [
    {
      "id": "uuid",
      "tool_name": "tavily_search",
      "input": {"query": "今天的天气"},
      "output": "北京今天晴...",
      "status": "success",
      "execution_time_ms": 1234,
      "created_at": "2026-02-25T10:30:00Z"
    }
  ],
  "total": 123,
  "page": 1
}
```

---

## 5. 数据模型

### 5.1 工具调用日志表

```sql
CREATE TABLE tool_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    tool_name VARCHAR(100) NOT NULL,
    tool_input JSONB,
    tool_output TEXT,
    status VARCHAR(20) NOT NULL,  -- 'success', 'error'
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 索引
    INDEX idx_tenant_tool (tenant_id, tool_name),
    INDEX idx_session (session_id),
    INDEX idx_user (user_id),
    INDEX idx_created_at (created_at)
);

COMMENT ON TABLE tool_call_logs IS '工具调用审计日志';
```

### 5.2 租户工具配额表

```sql
CREATE TABLE tenant_tool_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    max_calls_per_day INTEGER,
    max_calls_per_month INTEGER,
    current_day_calls INTEGER DEFAULT 0,
    current_month_calls INTEGER DEFAULT 0,
    last_reset_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    UNIQUE(tenant_id, tool_name),
    INDEX idx_tenant (tenant_id)
);

COMMENT ON TABLE tenant_tool_quotas IS '租户工具调用配额';
```

---

## 6. 前端增强

### 6.1 工具调用状态展示

```typescript
// services/sse.ts
export interface ToolEvent {
  type: 'tool_start' | 'tool_end' | 'tool_error';
  tool_name: string;
  input?: any;
  output?: any;
  error?: string;
  timestamp: number;
}

// components/ToolEventList.tsx
export function ToolEventList({ events }: { events: ToolEvent[] }) {
  return (
    <div className="tool-event-list">
      {events.map((event, index) => (
        <div key={index} className="tool-event">
          <span className="tool-icon">🔧</span>
          <span className="tool-name">{event.tool_name}</span>
          <span className="tool-status">
            {event.type === 'tool_start' && '正在调用...'}
            {event.type === 'tool_end' && '✓ 完成'}
            {event.type === 'tool_error' && '✗ 失败'}
          </span>
          {event.output && (
            <div className="tool-output">
              {JSON.stringify(event.output)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

### 6.2 工具配置页面

```typescript
// pages/Tools.tsx
export function ToolsPage() {
  const { data: tools } = useQuery({
    queryKey: ['tools'],
    queryFn: () => api.get('/api/v1/tools')
  });

  return (
    <div className="tools-page">
      <h1>工具配置</h1>
      <div className="tools-list">
        {tools?.map(tool => (
          <ToolCard key={tool.name} tool={tool} />
        ))}
      </div>
    </div>
  );
}

function ToolCard({ tool }: { tool: Tool }) {
  return (
    <div className="tool-card">
      <h3>{tool.display_name}</h3>
      <p>{tool.description}</p>
      <Switch
        checked={tool.enabled}
        onChange={(checked) => toggleTool(tool.name, checked)}
      />
      {tool.quota_limit && (
        <div className="quota-info">
          <Progress
            value={tool.quota_used}
            max={tool.quota_limit}
          />
          <span>{tool.quota_used} / {tool.quota_limit}</span>
        </div>
      )}
    </div>
  );
}
```

---

## 7. 监控指标

### 7.1 Prometheus 指标

```python
# api/metrics/tool_metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 工具调用总次数
tool_calls_total = Counter(
    'tool_calls_total',
    'Total tool calls',
    ['tenant_id', 'tool_name', 'status']
)

# 工具执行时间
tool_execution_duration = Histogram(
    'tool_execution_duration_seconds',
    'Tool execution duration in seconds',
    ['tenant_id', 'tool_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# 当前活跃工具调用
active_tool_calls = Gauge(
    'active_tool_calls',
    'Number of active tool calls',
    ['tenant_id', 'tool_name']
)

# 工具配额使用率
tool_quota_usage = Gauge(
    'tool_quota_usage',
    'Tool quota usage rate',
    ['tenant_id', 'tool_name', 'period']  # period: day/month
)
```

### 7.2 Grafana Dashboard

**关键指标**：
- 工具调用总次数（按租户、工具名称）
- 工具执行时间分布
- 工具调用成功率
- 活跃工具调用数
- 配额使用率

---

## 8. 安全考虑

### 8.1 工具调用安全

**配额限制**：
- 每个租户每天/每月的调用次数限制
- 防止滥用和意外的高额费用

**域名白名单**：
- API 调用工具必须遵守域名白名单
- 防止调用恶意或未授权的 API

**文件隔离**：
- 文件操作限制在租户目录内
- 防止跨租户文件访问

### 8.2 审计日志

**记录内容**：
- 工具名称
- 调用参数
- 返回结果
- 执行时间
- 调用状态（成功/失败）
- 错误信息

**用途**：
- 安全审计
- 问题排查
- 成本分析
- 使用优化

---

## 9. 实施计划（4周）

### Week 1: 基础设施
- [ ] Day 1-2: 创建 `ToolAdapter` 多租户适配器
- [ ] Day 3-4: 创建 `ToolRegistry` 工具注册表
- [ ] Day 5: 实现工具调用配额检查（`QuotaService` 扩展）
- [ ] Day 6-7: 数据库迁移（`tool_call_logs`、`tenant_tool_quotas`）

### Week 2: 标准工具集成
- [ ] Day 1-2: 集成 Tavily 搜索工具
- [ ] Day 3: 集成 LLM 数学工具
- [ ] Day 4-5: 实现文件处理工具集（CSV/PDF/TXT）
- [ ] Day 6-7: 实现 HTTP API 调用工具（GET/POST）

### Week 3: API 和前端
- [ ] Day 1: 工具列表 API（`GET /api/v1/tools`）
- [ ] Day 2: 工具统计 API（`GET /api/v1/tools/usage`）
- [ ] Day 3: 工具日志 API（`GET /api/v1/tools/logs`）
- [ ] Day 4-5: 前端工具调用状态展示（SSE 集成）
- [ ] Day 6-7: 前端工具配置页面

### Week 4: 测试和优化
- [ ] Day 1-2: 单元测试（`tests/test_tool_adapter.py`）
- [ ] Day 3: 集成测试（`tests/test_tool_integration.py`）
- [ ] Day 4: 性能测试（工具调用延迟）
- [ ] Day 5: 多租户隔离测试
- [ ] Day 6: 文档编写
- [ ] Day 7: Code Review 和优化

---

## 10. 成功标准

### 10.1 功能完整性
- ✅ 4 个标准工具全部可用（搜索、计算、文件、API）
- ✅ 工具调用通过 LangChain Agent 自动触发
- ✅ 前端实时展示工具调用状态

### 10.2 多租户隔离
- ✅ 所有工具调用都受租户隔离保护
- ✅ 工具调用日志记录到租户
- ✅ 工具配额按租户独立计算

### 10.3 可观测性
- ✅ 工具调用被正确监控（Prometheus 指标）
- ✅ 工具调用被正确计费（配额系统）
- ✅ 工具调用日志可审计

### 10.4 质量保证
- ✅ 所有测试通过（单元测试、集成测试）
- ✅ 代码覆盖率 > 80%
- ✅ 文档完整

---

## 11. 后续扩展（Phase 3+）

### 11.1 自定义工具
- 允许租户通过管理后台定义自己的 API 接口
- 支持 OpenAPI (Swagger) 格式导入
- 支持自定义参数验证

### 11.2 工作流编排
- 支持多步骤工具调用序列
- 支持条件分支和循环
- 可视化工作流编辑器

### 11.3 工具市场
- 预构建的工具模板库
- 工具分享和订阅
- 社区贡献工具

---

## 附录

### A. 环境变量

```bash
# Tavily API Key
TAVILY_API_KEY=tvly-xxx

# 默认工具配置
DEFAULT_MAX_FILE_SIZE_MB=10
DEFAULT_TOOL_QUOTA_PER_DAY=1000

# 工具执行超时
TOOL_EXECUTION_TIMEOUT_SECONDS=30
```

### B. 数据库迁移脚本

```python
# migrations/add_tool_calling_support.py
def upgrade():
    op.create_table(
        'tool_call_logs',
        sa.Column('id', UUID, primary_key=True),
        sa.Column('tenant_id', UUID, nullable=False),
        sa.Column('session_id', UUID),
        sa.Column('user_id', UUID),
        sa.Column('tool_name', sa.String(100), nullable=False),
        sa.Column('tool_input', JSONB),
        sa.Column('tool_output', sa.Text),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text),
        sa.Column('execution_time_ms', sa.Integer),
        sa.Column('created_at', TIMESTAMP, default=current_timestamp)
    )

    op.create_table(
        'tenant_tool_quotas',
        sa.Column('id', UUID, primary_key=True),
        sa.Column('tenant_id', UUID, nullable=False),
        sa.Column('tool_name', sa.String(100), nullable=False),
        sa.Column('max_calls_per_day', sa.Integer),
        sa.Column('max_calls_per_month', sa.Integer),
        sa.Column('current_day_calls', sa.Integer, default=0),
        sa.Column('current_month_calls', sa.Integer, default=0),
        sa.Column('last_reset_date', DATE, default=current_date)
    )
```

### C. 相关文档

- Phase 1 设计文档：`docs/plans/2026-02-14-agent-paas-phase2-design.md`
- Phase 2 进度：`PROGRESS.md`
- LangChain Tools 文档：https://python.langchain.com/docs/modules/tools/
- Tavily API 文档：https://docs.tavily.com/docs/tavily-api

---

**文档版本**: 1.0
**最后更新**: 2026-02-25
**状态**: 待审核
