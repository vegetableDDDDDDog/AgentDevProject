# Agent PaaS 前端

React + TypeScript 实现的前端应用，提供登录和对话功能。

## 功能特性

- ✅ 用户登录（JWT 认证）
- ✅ SSE 流式对话
- ✅ 多 Agent 切换
- ✅ 响应式设计

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 3. 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录。

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **React Router** - 路由管理
- **Axios** - HTTP 客户端
- **@microsoft/fetch-event-source** - SSE 支持

## 页面路由

- `/login` - 登录页面
- `/chat` - 对话页面（需要认证）

## API 配置

前端通过 Vite proxy 代理到后端 API（`http://localhost:8000`）。

如需修改后端地址，编辑 `vite.config.ts` 中的 `proxy.target`。

## 开发说明

### 添加新页面

1. 在 `src/pages/` 创建页面组件
2. 在 `src/App.tsx` 添加路由

### 添加新 API

1. 在 `src/services/` 创建服务函数
2. 使用 `apiClient` 发起请求

### 状态管理

当前使用 localStorage 存储 Token，后续可扩展为 Redux/Zustand。

## 测试账号

使用 Mock Agent 测试无需真实 API Key：
- Agent: `mock_chat_agent` 或 `echo_agent`

真实 LLM 需要：
1. 注册账号
2. 配置租户 LLM API Key
3. 选择 Agent: `llm_chat`
