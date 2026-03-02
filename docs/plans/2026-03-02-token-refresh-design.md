# Token 自动刷新功能设计文档

> **日期**: 2026-03-02
> **作者**: Claude & 用户
> **状态**: 设计阶段
> **优先级**: 高（用户体验改进）

---

## 1. 概述

### 1.1 问题背景

当前系统的Token认证机制存在以下问题：

- **Access Token有效期**: 15分钟
- **Refresh Token有效期**: 7天
- **当前行为**: Token过期后直接跳转登录页，无自动刷新
- **用户体验问题**: 用户每15分钟就被强制登出，需要频繁重新登录

### 1.2 目标

实现Token自动刷新机制，提升用户体验：

- ✅ Access Token过期前自动刷新（提前2分钟）
- ✅ API返回401时自动刷新（被动降级）
- ✅ 并发请求的刷新控制（避免重复刷新）
- ✅ 刷新失败时优雅降级（强制登出+友好提示）

---

## 2. 技术方案选择

### 2.1 方案对比

| 方案 | 描述 | 优点 | 缺点 | 选择 |
|------|------|------|------|------|
| **A. 纯前端定时器** | setInterval定时检查token | 简单 | 休眠/多标签页问题 | ❌ |
| **B. 后端辅助+请求拦截器** | 后端返回expires_in，请求前检查 | 健壮、标准 | 需后端微调 | ✅ **推荐** |
| **C. 纯被动刷新** | 仅401时刷新 | 最简单 | 用户体验差 | ❌ |

### 2.2 最终方案：方案B（混合策略）

**核心特性**：
- **主动刷新**: 在请求拦截器中检查 `expires_at`，剩余≤2分钟时刷新
- **被动刷新**: 响应拦截器捕获401错误，触发刷新
- **刷新锁**: `isRefreshing` 标志位防止重复刷新
- **队列化**: `failedQueue` 保存并发请求，刷新后批量重试

**选择理由**：
1. ✅ 无需定时器（避免休眠问题）
2. ✅ 基于服务端过期时间（准确可靠）
3. ✅ 完美实现混合策略（主动+被动）
4. ✅ 后端改动极小（仅添加 `expires_in` 字段）

---

## 3. 架构设计

### 3.1 工作流程

```
用户发起请求
    ↓
Axios 请求拦截器
    ↓
检查 expires_at 是否 ≤ (当前时间 + 120秒)
    ↓
    ├─ 是 → 触发刷新流程
    │         ├─ isRefreshing = true（上锁）
    │         ├─ POST /auth/refresh
    │         ├─ 成功: 更新token，处理队列，重试原请求
    │         └─ 失败:
    │               ├─ 401: 强制登出
    │               └─ 网络/5xx: 提示重试，不登出
    │
    └─ 否 → 正常发送请求

---

API 响应
    ↓
Axios 响应拦截器
    ↓
是否返回 401？
    ↓
    ├─ 是 → 触发刷新流程（被动降级）
    │         （逻辑同上）
    │
    └─ 否 → 正常返回响应
```

### 3.2 核心组件

| 组件 | 文件路径 | 职责 |
|------|----------|------|
| **后端Schema** | `api/schemas/auth.py` | 定义响应模型（添加 `expires_in`） |
| **后端AuthService** | `services/auth_service.py` | 生成token时返回过期秒数 |
| **后端AuthRouter** | `api/routers/auth.py` | 返回登录/刷新响应 |
| **前端Token工具** | `frontend/src/utils/token.ts` | 存储/获取 `expires_at` |
| **前端API客户端** | `frontend/src/services/api.ts` | Axios拦截器核心逻辑 |
| **前端Auth服务** | `frontend/src/services/auth.ts` | 登录/刷新方法 |

---

## 4. 后端修改

### 4.1 修改文件清单

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `api/schemas/auth.py` | 添加 `expires_in` 字段到响应模型 | P0 |
| `services/auth_service.py` | 返回字典中添加 `expires_in` | P0 |
| `api/routers/auth.py` | 无需修改（自动使用新Schema） | - |

### 4.2 Schema 修改

**文件**: `api/schemas/auth.py`

```python
class LoginResponse(BaseModel):
    """登录成功响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token过期秒数")
    user: UserInfo


class RefreshResponse(BaseModel):
    """刷新 token 成功响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="新Access token过期秒数")
```

### 4.3 AuthService 修改

**文件**: `services/auth_service.py`

**常量定义**:
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Access token 15分钟
REFRESH_TOKEN_EXPIRE_DAYS = 7  # Refresh token 7天
```

**返回字典修改**:
```python
# authenticate_user() 返回
return {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer",
    "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 转换为秒
    "user": user_info
}

# refresh_access_token() 返回
return {
    "access_token": new_access_token,
    "token_type": "bearer",
    "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
}
```

---

## 5. 前端实现

### 5.1 修改文件清单

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `frontend/src/utils/token.ts` | 添加 `expires_at` 存储/获取函数 | P0 |
| `frontend/src/services/auth.ts` | 登录/刷新时保存 `expires_in` | P0 |
| `frontend/src/services/api.ts` | 实现拦截器核心逻辑 | P0 |
| `frontend/src/pages/LoginPage.tsx` | 添加登出原因提示 | P1 |

### 5.2 Token 工具函数

**文件**: `frontend/src/utils/token.ts`

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
 * @return true表示需要刷新
 */
export const isTokenExpiring = (): boolean => {
  const expiresAt = getExpiresAt();
  if (!expiresAt) return false;
  // 提前2分钟（120000毫秒）判断
  return Date.now() + 120000 > expiresAt;
};
```

### 5.3 Auth 服务更新

**文件**: `frontend/src/services/auth.ts`

**login 函数修改**:
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

**refreshAccessToken 函数**:
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

### 5.4 Axios 拦截器核心逻辑

**文件**: `frontend/src/services/api.ts`

```typescript
import { refreshAccessToken } from './auth';
import { getToken, getExpiresAt, isTokenExpiring } from '../utils/token';

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

// ============================================================================
// 请求拦截器 - 主动刷新
// ============================================================================

apiClient.interceptors.request.use(
  async (config) => {
    // 检查token是否即将过期
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
            const { forceLogout } = await import('./auth');
            forceLogout();
          }
          // 网络/5xx错误 → 提示用户
          else {
            showToast('网络连接失败，请检查网络后重试', 'error');
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
  (error) => Promise.reject(error)
);

// ============================================================================
// 响应拦截器 - 被动刷新（401降级）
// ============================================================================

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<APIError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // 处理401错误
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
            const { forceLogout } = await import('./auth');
            forceLogout();
          }
          // 网络/5xx: 不登出，提示重试
          else {
            showToast('网络连接失败，请检查网络后重试', 'error');
          }
        }

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);
```

### 5.5 登录页提示

**文件**: `frontend/src/pages/LoginPage.tsx`

```typescript
import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';

export const LoginPage = () => {
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const reason = searchParams.get('reason');
    if (reason === 'session_expired') {
      showToast('会话已过期，请重新登录', 'info');
    }
  }, [searchParams]);

  // ... 其余登录逻辑
};
```

---

## 6. 错误处理

### 6.1 错误场景与处理策略

| 错误场景 | 后端响应 | 前端处理 | 用户体验 |
|----------|----------|----------|----------|
| **Refresh Token过期** | 401 + `TOKEN_EXPIRED` | 清空token，跳转登录页 | "会话已过期，请重新登录" |
| **Refresh Token无效** | 401 + `TOKEN_INVALID` | 清空token，跳转登录页 | "会话已过期，请重新登录" |
| **网络断开** | Network Error | 保留会话，显示toast | "网络连接失败，请检查网络后重试" |
| **服务器错误** | 500/502/503 | 保留会话，显示toast | "服务暂时不可用，请稍后重试" |
| **Access Token过期** | 401 | 自动刷新（无感知） | 无影响 |

### 6.2 错误区分逻辑

```typescript
// 在拦截器 catch 块中
if (refreshError instanceof AxiosError) {
  if (refreshError.response?.status === 401) {
    // Token真正过期 → 强制登出
    forceLogout();
  } else {
    // 网络/服务器错误 → 保留会话，提示用户
    showToast('网络连接失败，请检查网络后重试', 'error');
  }
}
```

---

## 7. 测试策略

### 7.1 功能测试清单

**核心场景**：
- [ ] 正常登录后 `expires_in` 正确保存
- [ ] Token剩余≤2分钟时主动刷新
- [ ] API返回401时被动刷新
- [ ] 刷新成功后原请求自动重试
- [ ] 刷新失败（401）后强制登出

### 7.2 并发测试

**测试场景**：
- [ ] 3个并发请求同时触发刷新
- [ ] 验证只发送1个 `/auth/refresh` 请求
- [ ] 验证3个请求都使用新token重试
- [ ] 验证请求执行顺序保持一致

**测试方法**：
```javascript
// 在浏览器控制台模拟
Promise.all([
  apiClient.get('/api/v1/sessions'),
  apiClient.get('/api/v1/sessions'),
  apiClient.get('/api/v1/sessions')
]);
// 检查Network面板，应该只有1个refresh请求
```

### 7.3 边界测试

| 场景 | 测试方法 | 预期结果 |
|------|----------|----------|
| **用户休眠后唤醒** | 1. 登录后等待token过期<br>2. 关闭电脑<br>3. 唤醒并发起请求 | 被动刷新成功 |
| **刷新过程中登出** | 1. 触发刷新<br>2. 立即点击登出按钮 | 正常登出，取消刷新 |
| **多标签页刷新** | 1. 打开2个标签页<br>2. 同时触发刷新 | 后端允许重复使用refresh_token（验证） |
| **网络慢刷新超时** | Chrome DevTools → Network → Slow 3G | 显示"网络连接失败"提示 |

### 7.4 安全测试

| 测试项 | 方法 | 预期结果 |
|--------|------|----------|
| Refresh Token过期 | 等待7天后刷新 | 强制登出 |
| Refresh Token篡改 | 修改localStorage中的refresh_token | 后端返回401，强制登出 |
| 重放攻击 | 使用已用过的refresh_token | 根据后端策略决定 |

### 7.5 测试工具

- **手动测试**: Chrome DevTools + Network throttling
- **单元测试**: Jest + axios-mock-adapter
- **E2E测试**: Playwright（可选，生产环境建议）

---

## 8. 边界情况与技术细节

### 8.1 多标签页竞争条件

**问题**：
- `isRefreshing` 是内存变量，各标签页独立
- Tab A 和 Tab B 可能同时触发刷新

**影响分析**：
- 依赖后端策略
- 如果后端允许多次使用同一 refresh_token → ✅ 无问题
- 如果后端采用严格 Refresh Token Rotation → ⚠️ 可能冲突

**当前项目**：
- 后端使用标准 JWT，允许多次使用
- **建议先测试验证**

**进阶解决方案**（如真有冲突）：
```typescript
// 方案1: localStorage 事件监听
window.addEventListener('storage', (e) => {
  if (e.key === 'token_refreshing') {
    isRefreshing = true;
  }
});

// 刷新时设置标记
localStorage.setItem('token_refreshing', Date.now().toString());
// 刷新后移除
localStorage.removeItem('token_refreshing');

// 方案2: navigator.locks（浏览器原生锁）
await navigator.locks.request('token_refresh', async () => {
  // 刷新逻辑
});
```

### 8.2 时间同步问题

**问题**：客户端时间不准确

**影响**：可能导致提前/延后刷新

**缓解措施**：
- JWT 的 `exp` 字段由服务端签名，服务端会验证
- 即使客户端时间不准，过期token会在服务端被拒绝

### 8.3 XSS 安全考虑

**当前方案**：
- Token存储在 localStorage
- 容易被 XSS 攻击窃取

**MVP阶段**：✅ 可接受

**生产增强建议**：
- 使用 httpOnly cookie 存储 refresh_token
- Access Token 可继续存储在内存/localStorage
- 实施 CSP (Content Security Policy)

### 8.4 Token Rotation（进阶）

**当前方案**：
- Refresh Token 长期有效（7天）
- 不实施 rotation

**生产建议**：
- 每次刷新返回新的 refresh_token
- 旧的 refresh_token 立即失效
- 提升安全性（防止refresh token被盗用）

---

## 9. 实施计划

### 9.1 实施阶段

**阶段1：后端修改**（预计30分钟）
1. 修改 `api/schemas/auth.py` - 添加 `expires_in`
2. 修改 `services/auth_service.py` - 返回过期秒数
3. 单元测试验证

**阶段2：前端基础**（预计30分钟）
1. 扩展 `frontend/src/utils/token.ts` - 添加过期时间函数
2. 更新 `frontend/src/services/auth.ts` - 保存 `expires_in`
3. 手动测试登录流程

**阶段3：拦截器实现**（预计1小时）
1. 实现 `frontend/src/services/api.ts` - 请求拦截器（主动刷新）
2. 实现响应拦截器（被动刷新）
3. 实现刷新锁和队列逻辑

**阶段4：错误处理**（预计30分钟）
1. 实现错误区分逻辑
2. 添加登录页提示
3. 测试各种错误场景

**阶段5：集成测试**（预计1小时）
1. 手动测试核心场景
2. 并发测试
3. 边界情况测试
4. 多标签页测试

**阶段6：文档更新**（预计30分钟）
1. 更新用户指南
2. 更新开发者日志
3. 更新 phase3-progress.md

**总工时估算**: 约 4 小时

### 9.2 风险与依赖

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 后端测试用例失败 | 低 | 中 | 先修改后端，验证通过再继续 |
| 多标签页冲突 | 低 | 低 | 测试验证，大概率无问题 |
| 拦截器逻辑bug | 中 | 高 | 充分测试，特别是并发场景 |
| 旧浏览器兼容性 | 低 | 低 | 使用现代浏览器（Chrome/Edge/Firefox） |

### 9.3 回滚计划

如果实施过程中遇到严重问题：
1. 后端修改可保留（向后兼容，旧客户端忽略 `expires_in`）
2. 前端代码回滚：恢复 `api.ts` 和 `auth.ts` 到旧版本
3. Git回滚命令：`git revert <commit-hash>`

---

## 10. 验收标准

### 10.1 功能验收

- [x] 用户登录后，`expires_in` 正确保存到 localStorage
- [ ] Token剩余≤2分钟时，下次请求自动刷新（用户无感知）
- [ ] API返回401时，自动刷新并重试请求
- [ ] 3个并发请求只发送1个refresh请求
- [ ] Refresh Token过期后，强制登出并显示友好提示
- [ ] 网络错误时不强制登出，显示重试提示

### 10.2 性能验收

- [ ] 主动刷新不影响请求性能（增加延迟<50ms）
- [ ] 并发场景下请求执行顺序保持一致
- [ ] 刷新成功后，排队请求批量重试无卡顿

### 10.3 安全验收

- [ ] Refresh Token过期后被正确拒绝（401）
- [ ] 刷新失败后所有token被清空
- [ ] 强制登出后无法绕过（无残留有效token）

---

## 11. 附录

### 11.1 相关文档

- [Phase 2设计文档](../plans/phase2-design.md) - 认证架构
- [开发者日志 - 2026-02-28](../DEVELOPER_LOGS/2026/2026-02-28.md) - 当前问题记录
- [Axios拦截器文档](https://axios-http.com/docs/interceptors) - 官方文档

### 11.2 技术术语

| 术语 | 说明 |
|------|------|
| **Access Token** | 短期token（15分钟），用于API认证 |
| **Refresh Token** | 长期token（7天），用于刷新Access Token |
| **expires_in** | Access token过期秒数（服务端返回） |
| **expires_at** | Access token过期时间戳（客户端计算） |
| **刷新锁** | 防止并发刷新的标志位 |
| **队列化** | 将并发请求排队，刷新后批量重试 |

### 11.3 参考资料

- [RFC 6749 - OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749)
- [JWT最佳实践](https://tools.ietf.org/html/rfc8725)
- [Axios拦截器模式](https://github.com/axios/axios#interceptors)

---

**文档状态**: ✅ 设计完成，待实施
**下一步**: 编写详细实施计划 → 实施 → 测试 → 部署

**维护者**: Phase 3 开发团队
**最后更新**: 2026-03-02
