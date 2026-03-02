# Token 自动刷新功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现 JWT Token 自动刷新机制，提升用户体验，避免频繁重新登录

**架构:** 混合策略 - 请求拦截器中主动刷新（剩余≤2分钟）+ 响应拦截器被动刷新（401降级），使用刷新锁+队列化处理并发请求

**技术栈:**
- 后端: FastAPI, Pydantic, JWT (python-jose)
- 前端: Axios, TypeScript, React
- 测试: pytest, Jest

---

## 前置准备

**阅读材料:**
1. 设计文档: `docs/plans/2026-03-02-token-refresh-design.md`
2. 当前认证实现: `api/routers/auth.py`, `services/auth_service.py`
3. 前端API服务: `frontend/src/services/api.ts`

**环境检查:**
```bash
# 确认在正确的分支
git branch
# 应显示: * main 或 feature/phase3-tool-calling

# 检查后端依赖
pip list | grep -E "jose|fastapi|pydantic"

# 检查前端依赖
cd frontend && npm list axios typescript
```

---

## Task 1: 后端 Schema 修改 - 添加 expires_in 字段

**目标:** 修改响应模型，添加 `expires_in` 字段到登录和刷新响应

**文件:**
- 修改: `api/schemas/auth.py`

**步骤 1: 备份原文件**

```bash
cp api/schemas/auth.py api/schemas/auth.py.backup
```

**步骤 2: 修改 LoginResponse 模型**

在 `api/schemas/auth.py` 中找到 `LoginResponse` 类（第54行左右），添加 `expires_in` 字段：

```python
class LoginResponse(BaseModel):
    """登录成功响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token过期秒数")  # 新增
    user: UserInfo
```

**步骤 3: 修改 RefreshResponse 模型**

在同一个文件中找到 `RefreshResponse` 类（第69行左右），添加 `expires_in` 字段：

```python
class RefreshResponse(BaseModel):
    """刷新 token 成功响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="新Access token过期秒数")  # 新增
```

**步骤 4: 验证 Python 语法**

```bash
python -m py_compile api/schemas/auth.py
```

预期: 无输出（语法正确）

**步骤 5: 提交**

```bash
git add api/schemas/auth.py
git commit -m "feat(auth): add expires_in field to auth response schemas

- Add expires_in to LoginResponse
- Add expires_in to RefreshResponse
- Document field purpose in description

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: 后端 AuthService 修改 - 返回 expires_in

**目标:** 修改认证服务，在返回字典中包含 `expires_in` 字段

**文件:**
- 修改: `services/auth_service.py`

**步骤 1: 备份原文件**

```bash
cp services/auth_service.py services/auth_service.py.backup
```

**步骤 2: 查找 authenticate_user 方法的返回语句**

```bash
grep -n "return {" services/auth_service.py | grep -A 10 "authenticate_user"
```

预期: 找到返回字典的代码块

**步骤 3: 修改 authenticate_user 返回值**

在 `services/auth_service.py` 的 `authenticate_user` 方法中，找到返回字典的地方，添加 `expires_in` 字段：

```python
# 找到类似这样的代码块
return {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer",
    "user": user_info
}

# 修改为
return {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer",
    "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 转换为秒
    "user": user_info
}
```

**步骤 4: 修改 authenticate_user_with_tenant 返回值**

同样修改 `authenticate_user_with_tenant` 方法的返回字典，添加相同的 `expires_in` 字段：

```python
return {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer",
    "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 新增
    "user": user_info
}
```

**步骤 5: 修改 refresh_access_token 返回值**

找到 `refresh_access_token` 方法，修改返回字典：

```python
# 找到返回语句
return {
    "access_token": new_access_token,
    "token_type": "bearer"
}

# 修改为
return {
    "access_token": new_access_token,
    "token_type": "bearer",
    "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 新增
}
```

**步骤 6: 验证 Python 语法**

```bash
python -m py_compile services/auth_service.py
```

**步骤 7: 手动测试后端API**

```bash
# 启动后端服务（如果未运行）
python -m api.main &

# 测试登录接口
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}' | jq .

# 验证响应包含 expires_in 字段
```

预期输出:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900,  // ✅ 15分钟 = 900秒
  "user": {...}
}
```

**步骤 8: 提交**

```bash
git add services/auth_service.py
git commit -m "feat(auth): return expires_in in token responses

- Add expires_in to authenticate_user() return value
- Add expires_in to authenticate_user_with_tenant() return value
- Add expires_in to refresh_access_token() return value
- Convert minutes to seconds (15 min = 900 sec)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: 前端 Token 工具函数扩展

**目标:** 添加 `expires_at` 的存储、获取和判断函数

**文件:**
- 修改: `frontend/src/utils/token.ts`

**步骤 1: 备份原文件**

```bash
cp frontend/src/utils/token.ts frontend/src/utils/token.ts.backup
```

**步骤 2: 添加 expires_at 存储函数**

在 `frontend/src/utils/token.ts` 文件末尾添加：

```typescript
/**
 * 保存Token过期时间戳
 * @param expiresIn 过期秒数
 */
export const setExpiresAt = (expiresIn: number): void => {
  const expiresAt = Date.now() + expiresIn * 1000;
  localStorage.setItem('expires_at', expiresAt.toString());
};

/**
 * 获取Token过期时间戳
 * @returns 过期时间戳（毫秒）或null
 */
export const getExpiresAt = (): number | null => {
  const expiresAt = localStorage.getItem('expires_at');
  return expiresAt ? parseInt(expiresAt) : null;
};

/**
 * 判断Token是否即将过期（剩余≤2分钟）
 * @returns true表示需要刷新
 */
export const isTokenExpiring = (): boolean => {
  const expiresAt = getExpiresAt();
  if (!expiresAt) return false;
  // 提前2分钟（120000毫秒）判断
  return Date.now() + 120000 > expiresAt;
};
```

**步骤 3: 更新 removeToken 函数**

找到 `removeToken` 函数，确保它也清除 `expires_at`：

```typescript
export const removeToken = (): void => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('expires_at');  // 新增
  localStorage.removeItem('user');
};
```

**步骤 4: 验证 TypeScript 语法**

```bash
cd frontend
npm run type-check
# 或
npx tsc --noEmit
```

预期: 无类型错误

**步骤 5: 提交**

```bash
git add frontend/src/utils/token.ts
git commit -m "feat(auth): add token expiration utilities

- Add setExpiresAt() - save expiration timestamp
- Add getExpiresAt() - retrieve expiration timestamp
- Add isTokenExpiring() - check if token needs refresh (≤2min)
- Update removeToken() to clear expires_at

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: 前端 Auth 服务更新

**目标:** 更新登录和刷新方法，保存 `expires_in`

**文件:**
- 修改: `frontend/src/services/auth.ts`

**步骤 1: 备份原文件**

```bash
cp frontend/src/services/auth.ts frontend/src/services/auth.ts.backup
```

**步骤 2: 更新导入**

在文件顶部添加新的导入：

```typescript
import {
  setToken,
  setRefreshToken,
  setUser,
  removeToken,
  setExpiresAt  // 新增
} from '../utils/token';
```

**步骤 3: 修改 login 函数**

找到 `login` 函数，更新它以保存 `expires_in`：

```typescript
export const login = async (
  email: string,
  password: string
): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>(
    '/auth/login',
    { email, password }
  );

  // 存储 Token、过期时间和用户信息
  setToken(response.data.access_token);
  setRefreshToken(response.data.refresh_token);
  setExpiresAt(response.data.expires_in);  // 新增
  setUser(response.data.user);

  return response.data;
};
```

**步骤 4: 添加 refreshAccessToken 函数**

在文件中添加新的刷新函数：

```typescript
/**
 * 刷新Access Token
 * @returns 新的Access Token
 * @throws 刷新失败时抛出错误（由拦截器处理）
 */
export const refreshAccessToken = async (): Promise<string> => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token');
  }

  const response = await apiClient.post<{access_token: string; expires_in: number}>(
    '/auth/refresh',
    { refresh_token: refreshToken }
  );

  // 更新token和过期时间
  setToken(response.data.access_token);
  setExpiresAt(response.data.expires_in);

  return response.data.access_token;
};

/**
 * 强制登出（会话过期时调用）
 */
export const forceLogout = (): void => {
  removeToken();
  window.location.href = '/login?reason=session_expired';
};
```

**步骤 5: 更新 types/index.ts**

检查并确保 `AuthResponse` 类型包含 `expires_in` 字段：

```typescript
export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;  // 确保添加此字段
  user: User;
}
```

**步骤 6: 验证 TypeScript 语法**

```bash
cd frontend
npx tsc --noEmit
```

**步骤 7: 提交**

```bash
git add frontend/src/services/auth.ts frontend/src/types/index.ts
git commit -m "feat(auth): save expires_in and add refreshAccessToken

- Update login() to save expires_in to localStorage
- Add refreshAccessToken() - refresh and save new token
- Add forceLogout() - redirect to login with session_expired flag
- Update AuthResponse type to include expires_in

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Axios 拦截器核心实现 - 请求拦截器

**目标:** 实现主动刷新逻辑，在请求前检查token是否即将过期

**文件:**
- 修改: `frontend/src/services/api.ts`

**步骤 1: 备份原文件**

```bash
cp frontend/src/services/api.ts frontend/src/services/api.ts.backup
```

**步骤 2: 添加导入和刷新锁变量**

在文件顶部导入区域添加：

```typescript
import { refreshAccessToken, forceLogout } from './auth';
import { getToken, isTokenExpiring } from '../utils/token';
import type { APIError } from '../types';
```

在 apiClient 创建后添加刷新锁和队列：

```typescript
// 创建 Axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// 刷新锁和队列
// ============================================================================

let isRefreshing = false;
let failedQueue: Array<(token: string) => void> = [];

/**
 * 处理排队的请求
 */
const processQueue = (newToken: string) => {
  failedQueue.forEach(cb => cb(newToken));
  failedQueue = [];
};
```

**步骤 3: 实现请求拦截器**

找到现有的请求拦截器，替换为以下实现：

```typescript
// 请求拦截器 - 添加Token + 主动刷新
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    // 检查token是否即将过期（主动刷新）
    if (getToken() && isTokenExpiring()) {
      // 如果正在刷新，加入队列等待
      if (isRefreshing) {
        return new Promise((resolve) => {
          failedQueue.push((newToken) => {
            config.headers.Authorization = `Bearer ${newToken}`;
            resolve(config);
          });
        });
      }

      // 触发刷新流程
      isRefreshing = true;
      try {
        const newToken = await refreshAccessToken();
        processQueue(newToken);
        config.headers.Authorization = `Bearer ${newToken}`;
      } catch (error) {
        // 刷新失败处理
        if (error instanceof AxiosError) {
          // 401: Refresh Token过期/无效 → 强制登出
          if (error.response?.status === 401) {
            forceLogout();
          }
          // 网络/5xx错误 → 提示用户（不强制登出）
          else {
            console.error('Token refresh failed:', error.message);
          }
        }
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    // 正常添加token
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);
```

**步骤 4: 验证 TypeScript 语法**

```bash
cd frontend
npx tsc --noEmit
```

**步骤 5: 提交**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): implement request interceptor with proactive refresh

- Add isRefreshing flag and failedQueue for concurrent request handling
- Check token expiration before each request (expires_in ≤ 2min)
- Trigger refresh if expiring, queue other requests
- Handle 401 refresh errors with forceLogout
- Handle network errors without logout

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Axios 响应拦截器实现 - 被动刷新

**目标:** 实现401错误处理，被动刷新token

**文件:**
- 修改: `frontend/src/services/api.ts`

**步骤 1: 找到现有响应拦截器**

当前响应拦截器（大约在第36行）处理401错误。我们需要替换它。

**步骤 2: 替换响应拦截器**

将现有的响应拦截器替换为新的实现：

```typescript
// 响应拦截器 - 处理错误 + 被动刷新
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<APIError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // 处理401错误（被动刷新）
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      // 如果正在刷新，加入队列等待
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            resolve(apiClient(originalRequest));
          });
        });
      }

      // 触发刷新流程
      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const newToken = await refreshAccessToken();
        processQueue(newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // 清空队列
        failedQueue = [];
        isRefreshing = false;

        // 区分错误类型
        if (refreshError instanceof AxiosError) {
          // 401: 强制登出
          if (refreshError.response?.status === 401) {
            forceLogout();
          }
          // 网络/5xx: 不登出，提示用户
          else {
            console.error('Token refresh failed:', refreshError.message);
          }
        }

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // 返回统一错误格式
    const apiError: APIError = error.response?.data || {
      error: 'UNKNOWN_ERROR',
      message: '未知错误',
    };

    return Promise.reject(apiError);
  }
);
```

**步骤 3: 验证 TypeScript 语法**

```bash
cd frontend
npx tsc --noEmit
```

**步骤 4: 提交**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): implement response interceptor with reactive refresh

- Handle 401 errors with automatic token refresh
- Add _retry flag to prevent infinite loops
- Queue concurrent requests during refresh
- Distinguish between 401 (logout) and network errors (retry)
- Maintain failedQueue for batch retry after refresh

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: 登录页提示增强

**目标:** 在登录页显示"会话已过期"提示

**文件:**
- 修改: `frontend/src/pages/LoginPage.tsx` (或类似文件)

**步骤 1: 查找登录页文件**

```bash
find frontend/src -name "*[Ll]ogin*" -o -name "*[Aa]uth*"
```

**步骤 2: 添加 URL 参数检查**

在登录组件中添加 useEffect 钩子：

```typescript
import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify'; // 或你使用的toast库

export const LoginPage = () => {
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const reason = searchParams.get('reason');
    if (reason === 'session_expired') {
      toast.info('会话已过期，请重新登录');
    }
  }, [searchParams]);

  // ... 其余登录逻辑
};
```

**步骤 3: 提交**

```bash
git add frontend/src/pages/LoginPage.tsx
git commit -m "feat(ui): add session expired message on login page

- Check URL reason parameter
- Display toast message when reason=session_expired
- Improve user experience for expired sessions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: 集成测试 - 核心场景

**目标:** 手动测试核心功能

**步骤 1: 启动服务**

```bash
# 启动后端（如果未运行）
python -m api.main

# 启动前端
cd frontend
npm run dev
```

**步骤 2: 测试登录并验证 expires_in**

1. 打开浏览器 DevTools → Application → Local Storage
2. 登录到应用
3. 检查 localStorage 是否包含 `expires_at` 键
4. 验证值是未来的时间戳

预期:
```javascript
localStorage.getItem('expires_at')
// 返回: "1712345678900" (未来的时间戳)
```

**步骤 3: 测试主动刷新**

1. 登录后等待 13 分钟（或手动修改 localStorage 的 `expires_at` 为当前时间+130秒）
2. 发起一个 API 请求
3. 在 Network 标签页观察

预期:
- 自动发送 `/auth/refresh` 请求
- 刷新成功后发送原始请求
- 用户体验无感知（无错误提示）

**步骤 4: 测试被动刷新（401场景）**

1. 手动篡改 access_token（在 localStorage 中修改一个字符）
2. 发起 API 请求
3. 观察网络请求

预期:
- 第一个请求返回 401
- 自动触发刷新请求
- 刷新成功后重试原始请求

**步骤 5: 测试并发请求**

在浏览器控制台执行：

```javascript
// 模拟3个并发请求
Promise.all([
  fetch('http://localhost:8000/api/v1/sessions', {
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('access_token') }
  }),
  fetch('http://localhost:8000/api/v1/sessions', {
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('access_token') }
  }),
  fetch('http://localhost:8000/api/v1/sessions', {
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('access_token') }
  })
]);
```

预期:
- 只发送 1 个 `/auth/refresh` 请求
- 3个原始请求都成功返回

**步骤 6: 测试强制登出**

1. 等待7天（或手动清空 refresh_token）
2. 触发刷新
3. 观察行为

预期:
- 跳转到 `/login?reason=session_expired`
- 显示"会话已过期"提示
- localStorage 被清空

---

## Task 9: 错误场景测试

**目标:** 测试各种错误场景

**步骤 1: 测试网络错误**

1. 打开 Chrome DevTools → Network → Offline
2. 触发token刷新
3. 观察行为

预期:
- 不强制登出
- console.error 日志
- 用户可以手动重试

**步骤 2: 测试服务器错误**

使用工具模拟后端返回500：

```bash
# 临时修改后端路由，返回500
# 在 api/routers/auth.py 的 /refresh 端点添加：
# raise HTTPException(status_code=500, detail="Internal server error")
```

预期:
- 不强制登出
- console.error 日志

**步骤 3: 恢复后端代码**

```bash
git checkout api/routers/auth.py
```

---

## Task 10: 文档更新

**目标:** 更新相关文档

**步骤 1: 更新 Phase 3 进度文件**

编辑 `docs/progress/phase3-progress.md`，在末尾添加：

```markdown
### ✅ Token 自动刷新功能 (2026-03-02)

#### 完成内容
- 后端添加 `expires_in` 字段到登录/刷新响应
- 前端实现主动刷新（请求拦截器）
- 前端实现被动刷新（响应拦截器）
- 刷新锁 + 队列化处理并发请求
- 完善的错误处理（401登出，网络错误保留会话）

#### 技术特性
- 混合策略：主动刷新（剩余≤2分钟）+ 被动刷新（401降级）
- 并发控制：使用 isRefreshing 锁防止重复刷新
- 队列化：failedQueue 保存并发请求，批量重试
- 错误区分：401强制登出，网络/5xx保留会话

#### 文件清单
| 文件 | 状态 | 说明 |
|------|------|------|
| api/schemas/auth.py | ✅ 修改 | 添加 expires_in 字段 |
| services/auth_service.py | ✅ 修改 | 返回 expires_in |
| frontend/src/utils/token.ts | ✅ 修改 | 添加过期时间工具函数 |
| frontend/src/services/auth.ts | ✅ 修改 | 保存 expires_in，添加刷新函数 |
| frontend/src/services/api.ts | ✅ 修改 | 实现拦截器核心逻辑 |
| frontend/src/pages/LoginPage.tsx | ✅ 修改 | 添加会话过期提示 |
```

**步骤 2: 创建开发者日志**

创建 `docs/DEVELOPER_LOGS/2026/2026-03-02.md`：

```markdown
# 开发者日志 - 2026-03-02

## 基本信息
- **日期**: 2026-03-02
- **开发者**: Claude
- **工作阶段**: Phase 3 - Token自动刷新
- **主要任务**: 实现JWT Token自动刷新机制

## 完成的工作
- ✅ 后端添加 expires_in 字段
- ✅ 前端实现主动刷新
- ✅ 前端实现被动刷新（401降级）
- ✅ 刷新锁和队列化
- ✅ 错误处理和用户提示
- ✅ 集成测试

## 技术亮点
- 混合刷新策略（主动+被动）
- 并发请求控制
- 优雅的错误处理

## 统计数据
- 修改文件: 6个
- 新增函数: 5个
- 代码行数: ~300行
```

**步骤 3: 提交文档更新**

```bash
git add docs/progress/phase3-progress.md docs/DEVELOPER_LOGS/2026/2026-03-02.md
git commit -m "docs: update Phase 3 progress with token auto-refresh

- Document Token auto-refresh implementation
- Add developer log for 2026-03-02
- Update progress tracking

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 11: 最终验证和清理

**目标:** 最终验证和代码清理

**步骤 1: 运行所有测试**

```bash
# 后端测试
pytest tests/ -v

# 前端测试（如果有）
cd frontend
npm test
```

**步骤 2: 代码审查清单**

- [ ] 所有修改已提交
- [ ] 备份文件已删除（或移到 .gitignore）
- [ ] 代码无 console.log 调试语句
- [ ] TypeScript 编译无错误
- [ ] Python 语法检查通过

**步骤 3: 清理备份文件**

```bash
rm -f api/schemas/auth.py.backup
rm -f services/auth_service.py.backup
rm -f frontend/src/utils/token.ts.backup
rm -f frontend/src/services/auth.ts.backup
rm -f frontend/src/services/api.ts.backup
```

**步骤 4: 最终提交**

```bash
git status
# 确认没有未跟踪的修改文件

# 创建总结提交
git commit --allow-empty -m "feat: complete token auto-refresh implementation

✅ Backend: Add expires_in to auth responses
✅ Frontend: Implement proactive and reactive refresh
✅ Frontend: Add refresh lock and queue management
✅ Frontend: Handle 401 errors with graceful degradation
✅ Frontend: Add session expired user notification
✅ Testing: All scenarios verified

Features:
- Auto-refresh before expiration (≤2min)
- Reactive refresh on 401 errors
- Concurrent request handling
- Error distinction (401 vs network)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**步骤 5: 推送到远程（可选）**

```bash
git push origin feature/phase3-tool-calling
# 或创建 Pull Request
```

---

## 验收标准

### 功能验收
- [ ] 用户登录后，`expires_at` 正确保存到 localStorage
- [ ] Token剩余≤2分钟时，下次请求自动刷新（用户无感知）
- [ ] API返回401时，自动刷新并重试请求
- [ ] 3个并发请求只发送1个refresh请求
- [ ] Refresh Token过期后，强制登出并显示友好提示
- [ ] 网络错误时不强制登出

### 性能验收
- [ ] 主动刷新不影响请求性能（增加延迟<50ms）
- [ ] 并发场景下请求执行顺序保持一致

### 安全验收
- [ ] Refresh Token过期后被正确拒绝（401）
- [ ] 刷新失败后所有token被清空

---

## 故障排查

### 问题1: expires_in 未返回

**检查:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}' | jq '.expires_in'
```

**解决方案:** 确认 Task 1 和 Task 2 已完成，后端返回包含 expires_in

### 问题2: 刷新不触发

**检查:**
```javascript
// 在浏览器控制台
console.log('expires_at:', localStorage.getItem('expires_at'));
console.log('isExpiring:', isTokenExpiring());
```

**解决方案:** 确认 Task 3 和 Task 4 已完成，expires_at 正确保存

### 问题3: 多次刷新请求

**检查:** Network 标签页，查看是否有多个 `/auth/refresh` 请求

**解决方案:** 确认 Task 5 和 Task 6 的刷新锁逻辑正确实现

---

## 参考资料

- 设计文档: `docs/plans/2026-03-02-token-refresh-design.md`
- Axios 拦截器: https://axios-http.com/docs/interceptors
- JWT 最佳实践: https://tools.ietf.org/html/rfc8725

---

**计划状态:** ✅ 完成
**下一步:** 执行实施计划
**预计工时:** 4小时
