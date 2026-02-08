# Agent PaaS 平台 - 第一阶段设计方案

> **目标**: 构建企业级Agent平台API服务
> **日期**: 2025-02-08
> **阶段**: Phase 1 - API First (构建"无头"引擎)

---

## 1. 总体架构

### 1.1 架构层次

```
┌─────────────────────────────────────────────┐
│           API Layer (FastAPI)               │
│  - RESTful endpoints                         │
│  - SSE StreamingResponse (打字机效果)        │
│  - Request validation                        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Agent Service Layer                 │
│  - Agent Factory (动态加载Agent)             │
│  - Session Manager (会话管理)                │
│  - BackgroundTasks (异步任务)                │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Agent Execution Engine               │
│  - 现有的agents/目录下的所有Agent            │
│  - BaseAgent统一接口                         │
│  - Orchestrator (多Agent编排)                │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Infrastructure Layer                │
│  - SQLite (存储)                             │
│  - ChromaDB (向量数据库)                     │
└─────────────────────────────────────────────┘
```

### 1.2 核心技术决策

| 组件 | 技术方案 | 原因 |
|------|----------|------|
| 流式输出 | **SSE (StreamingResponse)** | 单向流，基于HTTP，FastAPI原生支持，防火墙友好 |
| Agent加载 | **Agent Factory模式（注册表）** | 支持动态配置，便于插件化扩展 |
| 异步任务 | **FastAPI BackgroundTasks** | MVP阶段减少依赖，后续可演进 |
| 数据库 | **SQLite + SQLAlchemy** | 轻量级，无需额外服务 |
| 生产部署 | **Gunicorn + Uvicorn Worker** | 进程管理，生产级稳定性 |

---

## 2. 核心技术实践

### 2.1 Agent Factory - 注册表模式

```python
# services/agent_factory.py
agent_registry = {}

def register_agent(name: str):
    """装饰器：自动注册Agent到注册表"""
    def decorator(cls):
        agent_registry[name] = cls
        return cls
    return decorator

def get_agent(agent_type: str, config: dict = None):
    """根据类型动态创建Agent实例"""
    agent_class = agent_registry.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return agent_class(config or {})

# 使用示例
@register_agent("chat_basic")
class ChatAgent(BaseAgent):
    """基础对话Agent"""
    pass
```

### 2.2 SSE事件协议

```python
# api/sse_protocol.py
from enum import Enum
from pydantic import BaseModel

class SSEEventType(str, Enum):
    MESSAGE = "message"   # 正常文本输出
    THOUGHT = "thought"   # 中间思考步骤
    ERROR = "error"       # 错误信息
    DONE = "done"         # 流结束标记

class SSEEvent(BaseModel):
    event: SSEEventType
    data: dict

    def to_sse_format(self) -> str:
        return f"event: {self.event.value}\ndata: {self.data.json()}\n\n"
```

### 2.3 数据库Schema

```sql
-- 会话表
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    agent_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    config JSON,
    metadata JSON
);

-- 消息历史表
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Agent执行日志表
CREATE TABLE agent_logs (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    agent_type VARCHAR(50),
    task TEXT,
    status VARCHAR(20),
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. API端点设计

### 3.1 核心端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/completions` | SSE流式对话 |
| GET | `/api/v1/chat/history` | 获取会话历史 |
| GET | `/api/v1/agents` | 列出可用Agent |
| GET | `/api/v1/agents/{id}` | 获取Agent详情 |
| POST | `/api/v1/agents/{id}/execute` | 执行Agent任务 |
| GET | `/api/v1/health` | 健康检查 |

### 3.2 SSE流式对话示例

**请求：**
```json
POST /api/v1/chat/completions
{
  "agent_type": "chat_basic",
  "session_id": "optional-uuid",
  "message": "帮我分析这段代码",
  "config": {
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

**响应（SSE流）：**
```
event: thought
data: {"content": "正在使用 chat_basic 处理..."}

event: message
data: {"content": "这", "type": "text"}

event: message
data: {"content": "段", "type": "text"}

event: done
data: {"session_id": "uuid"}
```

---

## 4. 测试策略

### 4.1 核心原则

1. **Mock LLM** - 测试不消耗Token
2. **数据库隔离** - 每个测试独立内存数据库
3. **集成测试** - 覆盖关键业务流程

### 4.2 Mock Agent示例

```python
# tests/fixtures/mock_agents.py
from unittest.mock import AsyncMock, MagicMock

def create_mock_agent():
    mock_agent = MagicMock(spec=BaseAgent)
    mock_agent.name = "mock_chat_agent"
    mock_agent.execute = AsyncMock(return_value={
        "response": "这是Mock的回复，不消耗Token"
    })
    return mock_agent
```

### 4.3 数据库隔离

```python
# tests/fixtures/db_fixture.py
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
```

---

## 5. 项目结构

```
AgentDevProject/
├── api/                          # 新增
│   ├── main.py                   # FastAPI应用入口
│   ├── config.py                 # 配置管理
│   ├── sse_protocol.py           # SSE事件协议
│   ├── routers/
│   │   ├── chat.py
│   │   ├── agents.py
│   │   └── health.py
│   ├── schemas/
│   │   ├── chat.py
│   │   └── agents.py
│   └── middleware/
│       └── logging.py
│
├── services/                     # 新增
│   ├── agent_factory.py          # Agent工厂
│   ├── session_service.py        # 会话管理
│   └── database.py               # 数据库ORM
│
├── agents/                       # 保留（添加装饰器）
│   ├── base_agent.py
│   ├── chat_agent.py            # @register_agent("chat_basic")
│   ├── tool_agent.py
│   └── rag_agent.py
│
├── tests/                        # 扩展
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       ├── mock_agents.py
│       └── db_fixture.py
│
├── data/
│   └── agent_platform.db
│
├── logs/
│   └── agent_platform.log        # RotatingFileHandler切割
│
├── requirements.txt              # 更新依赖
├── Dockerfile
└── .env
```

---

## 6. 部署方案

### 6.1 开发环境

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 6.2 生产环境

```dockerfile
CMD ["gunicorn", "api.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

### 6.3 依赖更新

```txt
# requirements.txt 新增
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
pytest>=7.4.0
pytest-mock>=3.12.0
gunicorn>=21.0.0
httpx>=0.25.0
```

---

## 7. MVP功能范围

### ✅ 会做的（Phase 1）

- [ ] API基础框架（FastAPI）
- [ ] Agent工厂模式（注册表）
- [ ] SSE流式输出
- [ ] 会话管理（SQLite）
- [ ] 消息历史记录
- [ ] 健康检查端点
- [ ] 错误处理和日志
- [ ] 单元测试 + 集成测试
- [ ] Mock LLM测试

### ❌ 暂不做（后续阶段）

- 用户认证系统（第一阶段只用API Key）
- 前端UI（第二阶段）
- Agent可视化编排（第三阶段）
- 多租户隔离（第二阶段）
- Redis缓存（够用即可）
- Celery任务队列（后续高并发再考虑）
- 监控和可观测性（第二阶段）

---

## 8. 实施计划

### Week 1: 核心基础
- Day 1-2: 数据库Schema + ORM模型
- Day 3-4: Agent Factory + 现有Agent注册
- Day 5-7: 基础API端点（非流式）

### Week 2: 流式输出
- Day 1-3: SSE协议实现
- Day 4-5: 会话管理 + 历史记录
- Day 6-7: 错误处理 + 日志系统

### Week 3: 测试与优化
- Day 1-3: 单元测试 + 集成测试
- Day 4-5: 性能优化（连接池、缓存）
- Day 6-7: 文档编写

### Week 4: 部署与验证
- Day 1-3: Docker配置（可选）
- Day 4-5: 端到端测试
- Day 6-7: Bug修复 + 发布

---

## 9. 前端对接提示

**问题：** EventSource只支持GET请求

**解决方案：** 使用 `@microsoft/fetch-event-source`

```typescript
import { fetchEventSource } from '@microsoft/fetch-event-source';

await fetchEventSource('/api/v1/chat/completions', {
  method: 'POST',
  body: JSON.stringify({ agent_type: 'chat_basic', message: '你好' }),
  onmessage(msg) { console.log(JSON.parse(msg.data)); }
});
```

---

## 10. 关键注意事项

### 10.1 异步陷阱
⚠️ Service层使用同步方法（`def`），FastAPI会自动放到线程池
❌ 不要用 `async def` + 同步 `db.query()`（会阻塞Event Loop）

### 10.2 日志切割
✅ 使用 `RotatingFileHandler(maxBytes=10MB, backupCount=5)`
❌ 不要用 `FileHandler`（日志文件无限增长）

### 10.3 测试Mock
✅ 测试时Mock Agent，避免消耗Token
❌ 不要在测试中调用真实LLM API

---

**设计状态**: ✅ 已通过验证
**下一步**: 准备实施
