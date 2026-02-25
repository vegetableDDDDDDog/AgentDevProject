# JWT 认证服务设计文档

**日期**: 2026-02-22
**任务**: Task #2 - JWT 认证服务实现
**状态**: 设计完成，待实施

---

## 一、设计决策总结

### 1.1 核心设计原则

- **无状态 JWT**: 服务端不存储 token，客户端在 Authorization Header 中传递
- **邮箱自动租户识别**: 用户只需邮箱+密码，系统自动查找租户
- **双 token 机制**: Access token (15分钟) + Refresh token (7天)
- **bcrypt 加密**: 密码使用 cost=12 的 bcrypt 哈希
- **客户端删除登出**: 登出时客户端删除 token，服务端不维护黑名单

### 1.2 技术选型

| 组件 | 技术选择 | 原因 |
|------|---------|------|
| JWT 库 | python-jose[cryptography] | 成熟稳定，文档完善 |    ## 数字签名器 确保发出去的 Token 没被用户篡改过。
| 密码加密 | passlib[bcrypt] | 行业标准，cost=12 安全 |       ## 碎纸机/保险柜   确保即使数据库被偷了，黑客也拿不到用户的真实密码
| 传递方式 | Authorization Header | RESTful 标准，灵活 |
| 登出机制 | 客户端删除 token | 无状态，符合 JWT 理念 |

### 1.3 采纳的优化建议

**租户歧义处理**:
- 如果邮箱关联多个租户，返回 202 Accepted + 租户列表
- 前端提示用户选择租户后重新登录

**JWT Payload 增强**:
- 添加 `iat` (Issued At) - 标准字段
- 添加 `token_version` - 用于强制下线机制

---

## 二、架构设计

### 2.1 核心组件

```
┌─────────────────────────────────────────────────────────┐
│                     客户端应用                          │
│                  (Web/Mobile/CLI)                      │
└────────────────────┬────────────────────────────────────┘
                     │ Authorization: Bearer <token>
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI 应用 (api/main.py)                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 中间件层                                           │  │
│  │  - auth_middleware.py (验证 JWT)                  │  │
│  │  - error_handlers.py (处理认证异常)               │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 路由层 (api/routers/)                             │  │
│  │  - auth.py (登录、刷新)                           │  │
│  │  - chat.py (SSE 聊天，需要认证)                   │  │
│  │  - sessions.py (会话管理，需要认证)              │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           服务层 (services/auth_service.py)             │
│  - 跨租户用户查询                                       │
│  - 密码验证 (bcrypt)                                    │
│  - JWT token 生成/验证                                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                 数据库 (SQLite)                         │
│  - users (用户表，tenant_id + email 唯一约束)           │
│  - tenants (租户表)                                     │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流程

#### 登录流程

```
客户端 → POST /auth/login → 验证邮箱密码 → 查询租户 → 生成 JWT → 返回 token
                                         ↓
                                    找到多个租户？
                                         ↓
                                    返回 202 + 租户列表
```

#### Token 使用流程

```
客户端 → API 请求 + Authorization Header → 中间件验证 JWT → 注入用户信息 → 业务逻辑
                                                         ↓
                                                    request.state.auth_user
```

---

## 三、API 端点设计

### 3.1 登录

**端点**: `POST /api/auth/login`

**请求**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**成功响应 (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "role": "admin",
    "tenant_id": "tenant-001"
  }
}
```

**多租户歧义响应 (202 Accepted)**:
```json
{
  "status": "tenant_selection_required",
  "message": "您的邮箱属于多个租户，请选择",
  "tenants": [
    {"id": "tenant-001", "name": "Acme Corp"},
    {"id": "tenant-002", "name": "Globex Inc"}
  ]
}
```

**失败响应 (401 Unauthorized)**:
```json
{
  "error": "INVALID_CREDENTIALS",
  "message": "邮箱或密码错误",
  "code": "auth_001"
}
```

### 3.2 刷新 Token

**端点**: `POST /api/auth/refresh`

**请求**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**成功响应 (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 3.3 受保护端点示例

**端点**: `GET /api/sessions`

**请求**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**成功响应 (200 OK)**:
```json
{
  "sessions": [...]
}
```

**无 Token 失败响应 (401 Unauthorized)**:
```json
{
  "error": "MISSING_TOKEN",
  "message": "需要认证",
  "code": "auth_002"
}
```

---

## 四、JWT Payload 结构

### 4.1 Access Token Payload

```json
{
  "sub": "user-123",              // 用户 ID (标准字段)
  "tenant_id": "tenant-001",      // 租户 ID
  "role": "admin",                // 用户角色
  "iat": 1706900000,              // 签发时间 (标准字段)
  "exp": 1706900900,              // 过期时间 (标准字段)
  "token_version": 1              // Token 版本号
}
```

### 4.2 Refresh Token Payload

```json
{
  "sub": "user-123",
  "tenant_id": "tenant-001",
  "type": "refresh",              // 标识为 refresh token
  "iat": 1706900000,
  "exp": 1707504800,              // 7 天后
  "token_version": 1
}
```

---

## 五、错误处理

### 5.1 异常类型

```python
class AuthException(Exception):
    """认证异常基类"""

class UserNotFoundException(AuthException):
    """用户不存在 → 404"""

class InvalidCredentialsException(AuthException):
    """无效凭据 → 401"""

class TokenExpiredException(AuthException):
    """Token 过期 → 401"""

class TokenInvalidException(AuthException):
    """Token 无效 → 401"""

class TenantSelectionRequiredException(AuthException):
    """需要选择租户 → 202"""

class UserSuspendedException(AuthException):
    """用户被暂停 → 403"""
```

### 5.2 HTTP 状态码映射

| 异常类型 | HTTP 状态码 | WWW-Authenticate |
|---------|------------|-----------------|
| InvalidCredentialsException | 401 | - |
| TokenExpiredException | 401 | Bearer error="invalid_token" |
| TokenInvalidException | 401 | Bearer error="invalid_token" |
| UserSuspendedException | 403 | - |
| UserNotFoundException | 404 | - |
| TenantSelectionRequiredException | 202 | - |

---

## 六、安全考虑

### 6.1 密码策略

- **最小长度**: 8 个字符
- **加密算法**: bcrypt with cost=12
- **不存储明文**: 只存储哈希值
- **验证延迟**: bcrypt 故意设计为慢（~100ms），防止暴力破解

### 6.2 Token 安全

- **短期 Access token**: 15 分钟后自动过期
- **长期 Refresh token**: 7 天有效期
- **签名算法**: HS256 (HMAC-SHA256)
- **密钥管理**: 从环境变量 `SECRET_KEY` 读取

### 6.3 防御措施

- **通用错误消息**: 登录失败不区分"用户不存在"和"密码错误"
- **限流建议**: 后续可添加速率限制（如 5 次/分钟）
- **日志记录**: 记录失败的认证尝试（不记录敏感信息）

---

## 七、文件结构

### 7.1 新增文件

```
phase2-multi-tenant/
├── services/
│   ├── auth_service.py          # AuthService 类
│   └── exceptions.py            # 自定义异常
├── api/
│   ├── middleware/
│   │   ├── __init__.py          # 中间件包
│   │   ├── auth_middleware.py   # 认证中间件
│   │   └── error_handlers.py    # 错误处理
│   ├── routers/
│   │   └── auth.py              # 认证路由
│   └── schemas/
│       └── auth.py              # Pydantic 模型
└── tests/
    ├── test_auth_service.py     # 单元测试
    └── test_auth_api.py         # 集成测试
```

### 7.2 修改文件

```
├── api/main.py                  # 注册认证路由
├── requirements.txt             # 添加依赖
└── services/database.py         # User 模型添加 token_version 字段
```

---

## 八、依赖项

### 8.1 新增依赖

```txt
# JWT 认证
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6

# 测试
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

---

## 九、实施检查清单

### Phase 1: 核心服务 (Day 1-2)
- [ ] 创建 `services/exceptions.py`
- [ ] 实现 `services/auth_service.py`
  - [ ] 跨租户用户查询
  - [ ] 密码验证 (bcrypt)
  - [ ] JWT token 生成
  - [ ] JWT token 验证
- [ ] User 模型添加 `token_version` 字段
- [ ] 编写单元测试 (`tests/test_auth_service.py`)

### Phase 2: API 集成 (Day 2-3)
- [ ] 创建 `api/schemas/auth.py`
- [ ] 实现 `api/routers/auth.py`
  - [ ] POST /auth/login
  - [ ] POST /auth/refresh
- [ ] 创建 `api/middleware/__init__.py`
- [ ] 实现 `api/middleware/auth_middleware.py`
- [ ] 实现 `api/middleware/error_handlers.py`
- [ ] 更新 `api/main.py` 注册路由
- [ ] 编写集成测试 (`tests/test_auth_api.py`)

### Phase 3: 文档和收尾 (Day 3)
- [ ] 更新 requirements.txt
- [ ] 运行所有测试
- [ ] 更新 API 文档
- [ ] Git commit

---

## 十、后续扩展路径

完成当前 Task #2 后，可以按以下顺序扩展：

1. **Task #2.1**: 添加 API Key 认证支持
2. **Task #2.2**: 实现 Redis token 黑名单
3. **Task #2.3**: 添加密码重置功能
4. **Task #2.4**: 添加 OAuth2 第三方登录

---

**设计批准**: ✅ 2026-02-22
**实施开始**: 2026-02-22
**预计完成**: 2026-02-24 (3天)
