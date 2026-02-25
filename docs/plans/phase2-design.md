# Agent PaaS 平台 - 第二阶段设计方案

> **目标**: 构建生产级Agent平台 - 多租户与真实LLM集成
> **日期**: 2026-02-14
> **阶段**: Phase 2 - 多租户与生产化 (Production-Ready Multi-Tenant)

---

## 1. 阶段回顾

### 1.1 阶段一成果 ✅

**Phase 1 (已完成)**:
- ✅ 数据库持久化层 (SQLite + SQLAlchemy)
- ✅ Agent Factory (装饰器注册表模式)
- ✅ RESTful API (FastAPI)
- ✅ SSE流式输出
- ✅ 会话管理与消息历史
- ✅ 健康检查与监控
- ✅ 全面测试覆盖 (Mock LLM)

**未完成内容** (移至Phase 2):
- ❌ 真实LLM调用集成
- ❌ 用户认证与授权
- ❌ 多租户数据隔离
- ❌ 前端UI
- ❌ 监控与可观测性

---

## 2. 总体架构演进

### 2.1 新增架构层次

```
┌─────────────────────────────────────────────┐
│           Frontend Layer (NEW)             │
│  - Web UI (React/Vue)                     │
│  - 对话式界面                             │
│  - 管理后台                               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         API Gateway Layer (NEW)            │
│  - 认证中间件 (JWT/OAuth)                  │
│  - 租户隔离中间件                          │
│  - 速率限制                                │
│  - API版本管理                             │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│           API Layer (Phase 1)               │
│  - RESTful endpoints                        │
│  - SSE StreamingResponse                    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Agent Service Layer                 │
│  - Agent Factory (多租户注册表)             │
│  - Session Manager (租户隔离)               │
│  - LLM Service (真实LLM集成)                │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Agent Execution Engine               │
│  - LangChain Agents (NEW)                   │
│  - BaseAgent统一接口                        │
│  - Orchestrator (多Agent编排)               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Infrastructure Layer                │
│  - PostgreSQL (生产级数据库) (NEW)           │
│  - Redis (缓存/会话) (NEW)                  │
│  - ChromaDB (向量数据库)                    │
└─────────────────────────────────────────────┘
```

### 2.2 核心技术决策更新

| 组件 | Phase 1 | Phase 2 | 升级原因 |
|------|---------|---------|----------|
| 数据库 | SQLite | **SQLite (继续使用)** | 完全满足需求，零迁移成本，专注核心功能 |
| 缓存 | 无 | **Redis** (可选) | 会话存储，速率限制，分布式锁 |
| LLM | Mock | **真实LLM集成** | 支持智谱AI、OpenAI等多模型 |
| 认证 | API Key | **JWT + OAuth2** | 标准化认证，支持第三方登录 |
| 多租户 | 无 | **应用层隔离** | 企业级数据隔离（tenant_id字段） |
| 前端 | 无 | **React + TypeScript** | 现代化Web UI |
| 监控 | 基础日志 | **Prometheus + Grafana** | 可观测性，指标可视化 |
| 追踪 | 无 | **OpenTelemetry** | 分布式追踪 |

**数据库选型说明**:
- ✅ **Phase 2 继续使用 SQLite** - 详见 `docs/plans/2026-02-14-database-comparison.md`
- ✅ SQLite 完全满足多租户、认证、配额管理等所有功能需求
- ✅ 节省 3-5天迁移时间，专注核心功能开发
- ✅ 未来如需迁移，SQLAlchemy 抽象层保证低迁移成本

---

## 3. 核心功能设计

### 3.1 多租户架构

#### 3.1.1 租户模型

**数据库Schema设计**:

```sql
-- 租户表
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    plan VARCHAR(50) NOT NULL,  -- 'free', 'pro', 'enterprise'
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'suspended', 'deleted'
    settings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,  -- 'admin', 'user', 'viewer'
    status VARCHAR(20) DEFAULT 'active',
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, email)
);

-- 租户API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100),
    scopes JSONB,  -- ['chat:read', 'chat:write', 'agent:execute']
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 租户配额
CREATE TABLE tenant_quotas (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    max_users INTEGER DEFAULT 5,
    max_agents INTEGER DEFAULT 10,
    max_sessions_per_day INTEGER DEFAULT 100,
    max_tokens_per_month INTEGER DEFAULT 1000000,
    current_month_tokens INTEGER DEFAULT 0,
    reset_date DATE
);
```

#### 3.1.2 租户隔离策略

**行级安全 (Row-Level Security)**:

```python
# services/tenant_service.py
from sqlalchemy import and_
from sqlalchemy.orm import Session

def get_tenant_context(db: Session, tenant_id: str) -> TenantContext:
    """获取租户上下文"""
    tenant = db.query(Tenant).filter(
        and_(
            Tenant.id == tenant_id,
            Tenant.status == 'active'
        )
    ).first()

    if not tenant:
        raise TenantNotFoundException()

    return TenantContext(
        tenant_id=tenant.id,
        plan=tenant.plan,
        settings=tenant.settings,
        quotas=get_tenant_quotas(db, tenant_id)
    )

def check_tenant_quota(context: TenantContext, resource: str, increment: int = 1):
    """检查租户配额"""
    if resource == 'tokens':
        if context.quotas.current_month_tokens + increment > context.quotas.max_tokens_per_month:
            raise QuotaExceededException(f"Token quota exceeded")
    elif resource == 'sessions':
        # 检查每日会话数
        pass
```

**中间件集成**:

```python
# api/middleware/tenant_middleware.py
from fastapi import Request, HTTPException, status

async def tenant_middleware(request: Request, call_next):
    """租户隔离中间件"""
    # 1. 从JWT token或API key提取租户ID
    tenant_id = extract_tenant_id(request)

    # 2. 获取租户上下文
    context = get_tenant_context(db, tenant_id)

    # 3. 注入到请求状态
    request.state.tenant_context = context

    # 4. 继续处理请求
    response = await call_next(request)

    return response
```

---

### 3.2 认证与授权

#### 3.2.1 JWT认证流程

```python
# services/auth_service.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def create_access_token(self, user: User, expires_delta: timedelta = None) -> str:
        """创建JWT访问令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)

        to_encode = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role,
            "exp": expire
        }

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> TokenPayload:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return TokenPayload(**payload)
        except JWTError:
            raise AuthenticationException()

    def authenticate_user(self, db: Session, email: str, password: str) -> User:
        """用户认证"""
        user = db.query(User).filter(User.email == email).first()

        if not user or not pwd_context.verify(password, user.password_hash):
            raise AuthenticationException()

        return user
```

#### 3.2.2 OAuth2集成 (可选)

```python
# api/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/auth/login")
async def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    auth_service = AuthService()
    user = auth_service.authenticate_user(db, credentials.username, credentials.password)

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()

    # 创建访问令牌
    access_token = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/auth/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """刷新访问令牌"""
    auth_service = AuthService()
    user = auth_service.verify_refresh_token(refresh_token, db)
    access_token = auth_service.create_access_token(user)

    return {"access_token": access_token}
```

---

### 3.3 真实LLM集成

#### 3.3.1 LLM服务抽象

```python
# services/llm_service.py
from abc import ABC, abstractmethod
from langchain.llms.base import LLM
from langchain.chat_models import ChatGLM, ChatOpenAI

class LLMProvider(ABC):
    """LLM提供者抽象"""

    @abstractmethod
    def chat(self, messages: list, **kwargs) -> str:
        pass

    @abstractmethod
    def stream_chat(self, messages: list, **kwargs):
        """流式聊天"""
        pass

class GLMProvider(LLMProvider):
    """智谱AI提供者"""

    def __init__(self, api_key: str, model: str = "glm-4"):
        self.client = ChatGLM(
            api_key=api_key,
            model_name=model,
            temperature=0.7
        )

    def chat(self, messages: list, **kwargs) -> str:
        response = self.client(messages, **kwargs)
        return response.content

    def stream_chat(self, messages: list, **kwargs):
        """流式输出"""
        for chunk in self.client.stream(messages, **kwargs):
            yield chunk.content

class LLMService:
    """LLM服务工厂"""

    def __init__(self, tenant_context: TenantContext):
        self.tenant = tenant_context
        self.provider = self._create_provider()

    def _create_provider(self) -> LLMProvider:
        """根据租户配置创建LLM提供者"""
        provider_type = self.tenant.settings.get('llm_provider', 'glm')

        if provider_type == 'glm':
            api_key = self.tenant.settings.get('glm_api_key')
            return GLMProvider(api_key=api_key)
        elif provider_type == 'openai':
            api_key = self.tenant.settings.get('openai_api_key')
            return OpenAIProvider(api_key=api_key)
        else:
            raise UnsupportedProviderException()

    def chat(self, messages: list, **kwargs) -> str:
        """调用LLM"""
        # 检查Token配额
        self._check_token_quota(len(str(messages)))

        # 调用LLM
        response = self.provider.chat(messages, **kwargs)

        # 记录Token使用
        self._record_token_usage(response.usage.total_tokens)

        return response

    async def stream_chat(self, messages: list, **kwargs):
        """流式调用LLM"""
        async for chunk in self.provider.stream_chat(messages, **kwargs):
            yield chunk
```

#### 3.3.2 LangChain Agent集成

```python
# agents/langchain_agents.py
from services.agent_factory import register_agent
from langchain.agents import AgentExecutor, create_openai_agent
from langchain.tools import Tool

@register_agent("langchain_chat")
class LangChainChatAgent(BaseAgent):
    """基于LangChain的对话Agent"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.llm_service = LLMService(config['tenant_context'])
        self.tools = self._load_tools()

    def _load_tools(self) -> list[Tool]:
        """加载工具"""
        return [
            Tool(
                name="calculator",
                func=calculator_tool,
                description="用于数学计算"
            ),
            Tool(
                name="search",
                func=search_tool,
                description="搜索知识库"
            )
        ]

    async def execute(self, input_data: dict) -> dict:
        """执行Agent"""
        messages = input_data.get('messages', [])

        # 创建LangChain Agent
        agent = create_openai_agent(
            llm=self.llm_service.provider.client,
            tools=self.tools,
            prompt=self._get_prompt()
        )

        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True
        )

        # 执行
        result = await executor.ainvoke({
            "input": messages[-1]['content']
        })

        return {
            "response": result['output'],
            "intermediate_steps": result['intermediate_steps']
        }

    def stream_execute(self, input_data: dict):
        """流式执行"""
        messages = input_data.get('messages', [])

        async for chunk in self.llm_service.stream_chat(messages):
            yield {
                "type": "message",
                "content": chunk
            }
```

---

### 3.4 前端UI设计

#### 3.4.1 技术栈选择

**推荐方案**: React 18 + TypeScript + Vite

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.12.0",
    "axios": "^1.6.0",
    "zustand": "^4.4.0",
    "react-markdown": "^9.0.0",
    "@microsoft/fetch-event-source": "^2.0.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "eslint": "^8.55.0",
    "prettier": "^3.1.0"
  }
}
```

#### 3.4.2 页面结构

```
frontend/
├── src/
│   ├── pages/
│   │   ├── LoginPage.tsx           # 登录页
│   │   ├── DashboardPage.tsx        # 控制台
│   │   ├── ChatPage.tsx             # 对话界面
│   │   ├── AgentListPage.tsx        # Agent列表
│   │   ├── SessionListPage.tsx      # 会话历史
│   │   └── SettingsPage.tsx         # 设置
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatMessage.tsx      # 消息气泡
│   │   │   ├── ChatInput.tsx        # 输入框
│   │   │   └── SSEClient.tsx        # SSE客户端
│   │   ├── Agent/
│   │   │   ├── AgentCard.tsx        # Agent卡片
│   │   │   └── AgentConfig.tsx      # Agent配置
│   │   └── Layout/
│   │       ├── Sidebar.tsx           # 侧边栏
│   │       └── Header.tsx            # 顶部栏
│   ├── services/
│   │   ├── api.ts                   # API客户端
│   │   ├── auth.ts                  # 认证服务
│   │   └── sse.ts                   # SSE工具
│   ├── stores/
│   │   ├── authStore.ts             # 认证状态
│   │   ├── chatStore.ts             # 对话状态
│   │   └── tenantStore.ts           # 租户状态
│   └── utils/
│       ├── token.ts                 # Token工具
│       └── logger.ts                # 日志工具
├── index.html
├── vite.config.ts
└── tsconfig.json
```

#### 3.4.3 SSE客户端实现

```typescript
// services/sse.ts
import { fetchEventSource } from '@microsoft/fetch-event-source';

interface SSEMessage {
  event: 'message' | 'thought' | 'error' | 'done';
  data: string;
}

export class SSEClient {
  async chat(
    agentType: string,
    message: string,
    onMessage: (msg: string) => void,
    onThought: (thought: string) => void,
    onError: (error: string) => void,
    onComplete: () => void
  ) {
    const token = localStorage.getItem('access_token');

    await fetchEventSource('/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        agent_type: agentType,
        message: message
      }),
      onmessage(msg) {
        const data: SSEMessage = JSON.parse(msg.data);

        switch (data.event) {
          case 'message':
            onMessage(data.data);
            break;
          case 'thought':
            onThought(data.data);
            break;
          case 'error':
            onError(data.data);
            break;
          case 'done':
            onComplete();
            break;
        }
      },
      onerror(err) {
        onError(err.message);
      }
    });
  }
}
```

---

### 3.5 监控与可观测性

#### 3.5.1 Prometheus指标

```python
# api/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
chat_requests_total = Counter(
    'chat_requests_total',
    'Total chat requests',
    ['tenant_id', 'agent_type', 'status']
)

chat_duration_seconds = Histogram(
    'chat_duration_seconds',
    'Chat request duration',
    ['tenant_id', 'agent_type']
)

active_sessions = Gauge(
    'active_sessions',
    'Number of active sessions',
    ['tenant_id']
)

token_usage_total = Counter(
    'token_usage_total',
    'Total token usage',
    ['tenant_id', 'model']
)

# 使用示例
@router.post("/api/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    start_time = time.time()

    try:
        # 处理请求
        response = await process_chat(request)

        # 记录指标
        chat_requests_total.labels(
            tenant_id=request.tenant_id,
            agent_type=request.agent_type,
            status='success'
        ).inc()

        duration = time.time() - start_time
        chat_duration_seconds.labels(
            tenant_id=request.tenant_id,
            agent_type=request.agent_type
        ).observe(duration)

        return response

    except Exception as e:
        chat_requests_total.labels(
            tenant_id=request.tenant_id,
            agent_type=request.agent_type,
            status='error'
        ).inc()
        raise
```

#### 3.5.2 OpenTelemetry追踪

```python
# api/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger import JaegerExporter

# 配置追踪
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# 使用示例
@router.post("/api/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    with tracer.start_as_current_span("chat_completion") as span:
        span.set_attribute("agent_type", request.agent_type)
        span.set_attribute("tenant_id", request.tenant_id)

        with tracer.start_as_current_span("llm_call"):
            response = await llm_service.chat(request.messages)

        return response
```

---

## 4. 数据库扩展策略

### 4.1 SQLite 多租户扩展

**扩展方式**: 应用层租户隔离 + 表结构扩展

**新增表** (使用 SQLite + SQLAlchemy):

```python
# services/database.py (扩展)

class Tenant(Base):
    """租户表"""
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)
    plan = Column(String(50), nullable=False)  # 'free', 'pro', 'enterprise'
    status = Column(String(20), default='active')
    settings = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'admin', 'user', 'viewer'
    status = Column(String(20), default='active')
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uq_tenant_email'),
    )

class APIKey(Base):
    """API密钥表"""
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    key_hash = Column(String(255), nullable=False, unique=True)
    name = Column(String(100), nullable=True)
    scopes = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class TenantQuota(Base):
    """租户配额表"""
    __tablename__ = "tenant_quotas"

    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    max_users = Column(Integer, default=5)
    max_agents = Column(Integer, default=10)
    max_sessions_per_day = Column(Integer, default=100)
    max_tokens_per_month = Column(Integer, default=1000000)
    current_month_tokens = Column(Integer, default=0)
    reset_date = Column(Date, nullable=False)

# 扩展现有表 (添加 tenant_id)
# 注意：需要数据迁移脚本为现有数据添加默认租户
```

**数据迁移** (为现有数据添加租户):

```python
# migrations/add_tenant_support.py
def upgrade_add_tenant_support():
    """为现有数据库添加多租户支持"""

    # 1. 添加 tenant_id 列到现有表
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE sessions ADD COLUMN tenant_id STRING REFERENCES tenants(id)"))
        conn.execute(text("ALTER TABLE messages ADD COLUMN tenant_id STRING REFERENCES tenants(id)"))
        conn.execute(text("ALTER TABLE agent_logs ADD COLUMN tenant_id STRING REFERENCES tenants(id)"))

        # 2. 创建默认租户
        default_tenant_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO tenants (id, name, display_name, plan, status)
            VALUES (:id, 'default', 'Default Tenant', 'free', 'active')
        """), {"id": default_tenant_id})

        # 3. 更新现有数据关联到默认租户
        conn.execute(text("UPDATE sessions SET tenant_id = :tid WHERE tenant_id IS NULL"), {"tid": default_tenant_id})
        conn.execute(text("UPDATE messages SET tenant_id = :tid WHERE tenant_id IS NULL"), {"tid": default_tenant_id})
        conn.execute(text("UPDATE agent_logs SET tenant_id = :tid WHERE tenant_id IS NULL"), {"tid": default_tenant_id})

        conn.commit()

    print("✅ 多租户支持已添加，现有数据已关联到默认租户")
```

---

## 5. 项目结构

```
AgentDevProject/
├── .worktrees/
│   └── phase2-multi-tenant/          # Phase 2 分支
│       ├── api/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── sse_protocol.py
│       │   ├── metrics.py             # NEW: Prometheus指标
│       │   ├── tracing.py             # NEW: OpenTelemetry
│       │   ├── routers/
│       │   │   ├── auth.py            # NEW: 认证路由
│       │   │   ├── tenants.py         # NEW: 租户管理
│       │   │   ├── users.py           # NEW: 用户管理
│       │   │   ├── chat.py
│       │   │   ├── agents.py
│       │   │   └── sessions.py
│       │   ├── middleware/
│       │   │   ├── auth.py            # NEW: 认证中间件
│       │   │   ├── tenant.py          # NEW: 租户隔离
│       │   │   └── rate_limit.py      # NEW: 速率限制
│       │   └── schemas/
│       │       ├── auth.py            # NEW: 认证模型
│       │       ├── tenant.py          # NEW: 租户模型
│       │       └── user.py            # NEW: 用户模型
│       ├── services/
│       │   ├── database.py            # 更新: PostgreSQL
│       │   ├── session_service.py     # 更新: 租户隔离
│       │   ├── agent_factory.py
│       │   ├── llm_service.py         # NEW: LLM服务
│       │   ├── auth_service.py        # NEW: 认证服务
│       │   ├── tenant_service.py      # NEW: 租户服务
│       │   └── quota_service.py       # NEW: 配额管理
│       ├── agents/
│       │   ├── base_agent.py
│       │   ├── langchain_agents.py   # NEW: LangChain集成
│       │   └── ...
│       ├── tests/
│       │   ├── unit/
│       │   ├── integration/
│       │   └── e2e/                  # NEW: 端到端测试
│       ├── alembic/                  # NEW: 数据库迁移
│       │   └── versions/
│       ├── docker/                   # NEW: Docker配置
│       │   ├── Dockerfile
│       │   └── docker-compose.yml
│       ├── kubernetes/               # NEW: K8s配置 (可选)
│       │   ├── deployment.yaml
│       │   ├── service.yaml
│       │   └── configmap.yaml
│       └── frontend/                # NEW: 前端项目
│           ├── src/
│           ├── package.json
│           └── vite.config.ts
├── docs/
│   └── plans/
│       ├── 2025-02-08-agent-paas-phase1-design.md
│       └── 2026-02-14-agent-paas-phase2-design.md  # 本文档
└── README.md
```

---

## 6. 实施计划

### Week 1-2: 多租户基础与认证
- Day 1-2: SQLite多租户扩展 (Tenant/User/APIKey模型）
- Day 3-5: JWT认证服务
- Day 6-8: 租户隔离中间件
- Day 9-10: 配额管理服务
- Day 11-14: 测试与验证

### Week 3-4: LLM集成与LangChain
- Day 1-3: LLM服务抽象
- Day 4-7: 真实LLM集成 (智谱AI)
- Day 8-10: LangChain Agent注册
- Day 11-14: Token配额与计费

### Week 5-6: 前端UI
- Day 1-3: 项目脚手架 + 基础组件
- Day 4-7: 对话界面 + SSE集成
- Day 8-10: 管理后台
- Day 11-14: 测试与优化

### Week 7-8: 监控与部署
- Day 1-3: Prometheus + Grafana
- Day 4-5: OpenTelemetry追踪
- Day 6-7: Docker化
- Day 8-10: K8s部署 (可选)
- Day 11-14: 性能测试 + 压测

---

## 7. MVP功能范围

### ✅ Phase 2 会做

#### 核心功能
- [ ] PostgreSQL数据库 + Alembic迁移
- [ ] 租户/用户模型
- [ ] JWT认证 + OAuth2 (可选)
- [ ] 租户隔离中间件
- [ ] 行级安全 (RLS)
- [ ] 真实LLM集成 (智谱AI)
- [ ] LangChain Agent支持
- [ ] Token配额管理
- [ ] 基础前端UI (登录 + 对话)
- [ ] Prometheus指标

#### 测试
- [ ] 单元测试覆盖 > 80%
- [ ] 集成测试 (认证、租户隔离)
- [ ] E2E测试 (登录 → 对话 → 登出)
- [ ] 性能测试 (并发用户)

### ❌ Phase 2 暂不做 (后续阶段)

- [ ] 完整管理后台 (Phase 3)
- [ ] Agent可视化编排 (Phase 3)
- [ ] 高级权限管理 (RBAC) (Phase 3)
- [ ] 多租户高级功能 (子租户、跨租户共享) (Phase 3)
- [ ] 支付集成 (Phase 3)
- [ ] 多语言支持 (Phase 3)
- [ ] 移动端App (Phase 4)

---

## 8. 关键注意事项

### 8.1 安全性

1. **密码加密**: 使用bcrypt， NEVER使用明文
2. **JWT密钥**: 环境变量， NEVER硬编码
3. **SQL注入**: 始终使用ORM参数化查询
4. **租户隔离**: 验证每个请求的租户ID
5. **速率限制**: 防止API滥用

### 8.2 性能

1. **连接池**: PostgreSQL连接池 (SQLAlchemy)
2. **缓存**: Redis缓存会话、Token
3. **索引**: 租户ID字段必须索引
4. **查询优化**: 避免N+1查询
5. **SSE连接**: 超时断开机制

### 8.3 测试

1. **真实LLM**: 测试时使用Mock，生产才用真实API
2. **租户隔离**: 测试跨租户数据泄露
3. **并发测试**: 多租户并发场景
4. **Token配额**: 测试超限处理

---

## 9. 依赖更新

```txt
# requirements.txt 新增

# Authentication
python-jose[cryptography]>=3.3.0  # JWT处理
passlib[bcrypt]>=1.7.4          # 密码加密
python-multipart>=0.0.6        # 表单数据

# LLM
langchain>=0.1.0
langchain-community>=0.0.10
zhipuai>=4.0.0                 # 智谱AI SDK

# Monitoring (可选)
prometheus-client>=0.19.0       # Prometheus指标
opentelemetry-api>=1.21.0      # OpenTelemetry
opentelemetry-sdk>=1.21.0
opentelemetry-exporter-jaeger>=1.21.0

# Caching (可选)
redis>=5.0.0
```

---

## 10. 下一步行动

### 立即开始

1. **创建Phase 2分支**
   ```bash
   cd /home/wineash/PycharmProjects/AgentDevProject
   git worktree add .worktrees/phase2-multi-tenant -b feature/phase2-multi-tenant
   ```

2. **环境准备**
   - 安装PostgreSQL
   - 安装Redis
   - 配置智谱AI API Key

3. **数据库迁移**
   - 配置Alembic
   - 编写迁移脚本
   - 测试迁移

4. **多租户基础**
   - 创建租户/用户模型
   - 实现认证服务
   - 租户中间件

---

**设计状态**: ✅ 规划完成，待实施
**优先级**: 高
**预计工期**: 8周
**技术债务**: 低

---

*作者: Claude Code*
*日期: 2026-02-14*
*版本: 2.0.0*
