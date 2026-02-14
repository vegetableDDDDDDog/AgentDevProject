# Agent PaaS 平台 - 阶段二实施日志

## 项目概述

**目标**: 构建生产级多租户Agent PaaS平台
**当前阶段**: Phase 2 - 多租户与生产化
**技术栈**: FastAPI + PostgreSQL + Redis + React + TypeScript
**开发分支**: `feature/phase2-multi-tenant`
**工作目录**: `/home/wineash/PycharmProjects/AgentDevProject/.worktrees/phase2-multi-tenant`

---

## Phase 2 开发进度

### 1. 环境准备 (2026-02-14)

#### 1.1 分支创建 ✅
```bash
# 提交设计文档
git add docs/plans/2026-02-14-agent-paas-phase2-design.md
git commit -m "docs: Add Phase 2 design document"

# 创建worktree
git worktree add .worktrees/phase2-multi-tenant -b feature/phase2-multi-tenant
```

#### 1.2 依赖更新计划

**新增依赖**:
```txt
# Database
psycopg2-binary>=2.9.0          # PostgreSQL驱动
alembic>=1.12.0                # 数据库迁移

# Authentication
python-jose[cryptography]>=3.3.0  # JWT处理
passlib[bcrypt]>=1.7.4          # 密码加密
python-multipart>=0.0.6        # 表单数据

# LLM
langchain>=0.1.0
langchain-community>=0.0.10
zhipuai>=4.0.0                 # 智谱AI SDK

# Caching
redis>=5.0.0

# Monitoring
prometheus-client>=0.19.0       # Prometheus指标
opentelemetry-api>=1.21.0      # OpenTelemetry
opentelemetry-sdk>=1.21.0
opentelemetry-exporter-jaeger>=1.21.0
```

---

## 核心架构设计

### 2. 多租户架构

#### 2.1 数据库Schema

**租户表 (tenants)**:
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    plan VARCHAR(50) NOT NULL,  -- 'free', 'pro', 'enterprise'
    status VARCHAR(20) DEFAULT 'active',
    settings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**用户表 (users)**:
```sql
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
```

**API Keys表 (api_keys)**:
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100),
    scopes JSONB,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**租户配额表 (tenant_quotas)**:
```sql
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

#### 2.2 租户隔离策略

**行级安全 (Row-Level Security)**:
```python
# services/tenant_service.py
def get_tenant_context(db: Session, tenant_id: str) -> TenantContext:
    """获取租户上下文，包含隔离验证"""
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
```

---

### 3. 认证与授权

#### 3.1 JWT认证流程

**认证服务**:
```python
# services/auth_service.py
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
```

#### 3.2 认证中间件

```python
# api/middleware/auth_middleware.py
async def auth_middleware(request: Request, call_next):
    """认证中间件"""
    # 1. 提取令牌
    token = extract_token_from_request(request)

    # 2. 验证令牌
    auth_service = AuthService()
    payload = auth_service.verify_token(token)

    # 3. 获取用户信息
    user = get_user_by_id(payload.sub)

    # 4. 注入到请求状态
    request.state.user = user
    request.state.tenant_id = payload.tenant_id

    # 5. 继续处理请求
    response = await call_next(request)
    return response
```

---

### 4. 真实LLM集成

#### 4.1 LLM服务抽象

```python
# services/llm_service.py
from abc import ABC, abstractmethod

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
        from langchain.chat_models import ChatGLM
        self.client = ChatGLM(
            zhipuai_api_key=api_key,
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
```

#### 4.2 LLM服务工厂

```python
# services/llm_service.py (续)
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
```

---

### 5. 前端UI设计

#### 5.1 技术栈

**核心依赖**:
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
  }
}
```

#### 5.2 SSE客户端

```typescript
// services/sse.ts
import { fetchEventSource } from '@microsoft/fetch-event-source';

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
        const data = JSON.parse(msg.data);

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

### 6. 监控与可观测性

#### 6.1 Prometheus指标

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
```

#### 6.2 OpenTelemetry追踪

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
```

---

## 实施日志

### 待实施任务

#### Week 1-2: 数据库迁移与多租户基础
- [ ] 配置PostgreSQL (安装、用户、数据库)
- [ ] 配置Alembic (初始化、生成迁移脚本)
- [ ] 创建租户/用户模型 (Tenant, User, APIKey, TenantQuota)
- [ ] 实现认证服务 (AuthService)
- [ ] 实现租户服务 (TenantService)
- [ ] 实现配额服务 (QuotaService)
- [ ] 创建认证中间件
- [ ] 创建租户隔离中间件
- [ ] 编写单元测试
- [ ] 编写集成测试

#### Week 3-4: LLM集成
- [ ] 创建LLM服务抽象 (LLMProvider)
- [ ] 实现智谱AI提供者 (GLMProvider)
- [ ] 实现OpenAI提供者 (OpenAIProvider)
- [ ] 创建LLM服务工厂 (LLMService)
- [ ] 集成LangChain Agents
- [ ] 实现Token配额管理
- [ ] 注册LangChain Agents
- [ ] 编写LLM测试 (使用Mock)

#### Week 5-6: 前端UI
- [ ] 创建React项目 (Vite + TypeScript)
- [ ] 配置路由 (React Router)
- [ ] 配置状态管理 (Zustand)
- [ ] 实现登录页面
- [ ] 实现对话界面 (SSE集成)
- [ ] 实现Agent管理界面
- [ ] 实现会话历史界面
- [ ] 实现设置页面
- [ ] 编写前端测试

#### Week 7-8: 监控与部署
- [ ] 配置Prometheus指标
- [ ] 配置Grafana仪表盘
- [ ] 配置OpenTelemetry追踪
- [ ] 创建Dockerfile
- [ ] 创建docker-compose.yml
- [ ] 编写K8s配置 (可选)
- [ ] 性能测试
- [ ] 压力测试
- [ ] 文档完善

---

## 快速链接

- **设计文档**: `docs/plans/2026-02-14-agent-paas-phase2-design.md`
- **进度跟踪**: `PROGRESS.md`
- **实施日志**: 本文档
- **Phase 1参考**: `.worktrees/phase1-api/project_process.md`

---

*更新时间: 2026-02-14*
*状态: 准备实施*
