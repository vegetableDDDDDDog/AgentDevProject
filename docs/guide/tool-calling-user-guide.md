# 工具调用功能使用指南

## 概述

Agent PaaS 平台支持工具调用功能，让 Agent 可以执行实际任务，而不仅仅是生成文本。

## 可用工具

### 1. 网络搜索 (Tavily Search)

Agent 可以搜索实时网络信息。

**使用示例**:
- "搜索今天的天气"
- "查找最新的 AI 新闻"
- "搜索 Python 3.12 的新特性"

**配置**:
```json
{
  "enable_search": true,
  "tavily_api_key": "tvly-your-key"
}
```

**获取 API Key**:
访问 [Tavily](https://tavily.com/) 注册并获取 API Key。

### 2. 数学计算 (LLM Math)

Agent 可以执行复杂数学计算。

**使用示例**:
- "计算 123 * 456"
- "圆周率后 100 位是什么"
- "求解 x^2 + 2x + 1 = 0"

**配置**:
```json
{
  "enable_math": true
}
```

### 3. 文件处理（规划中）

Agent 将支持处理用户上传的文件（CSV、PDF、TXT）。

**计划功能**:
- "读取 data.csv 并统计行数"
- "提取 report.pdf 中的关键信息"

### 4. API 调用（规划中）

Agent 将支持调用第三方 REST API。

**计划功能**:
- "查询当前的比特币价格"
- "获取 GitHub 仓库信息"

## 配额管理

每个租户可以配置工具调用配额：

- **日配额**: 每天最多调用次数
- **月配额**: 每月最多调用次数

查询配额使用情况：
```bash
GET /api/v1/tools/usage
Authorization: Bearer <access_token>
```

响应示例：
```json
{
  "total_calls": 150,
  "by_tool": {
    "tavily_search": 100,
    "llm_math": 50
  },
  "success_rate": 0.98
}
```

## API 使用

### 获取可用工具列表

```bash
GET /api/v1/tools
Authorization: Bearer <access_token>
```

响应示例：
```json
[
  {
    "name": "tavily_search",
    "display_name": "Tavily Search",
    "description": "搜索实时网络信息，获取最新数据和答案",
    "enabled": true,
    "quota_limit": 100,
    "quota_used": 45,
    "quota_remaining": 55
  },
  {
    "name": "llm_math",
    "display_name": "Llm Math",
    "description": "执行复杂数学计算，包括算术、代数、微积分等",
    "enabled": true,
    "quota_limit": null,
    "quota_used": null,
    "quota_remaining": null
  }
]
```

### 获取工具配置

```bash
GET /api/v1/tools/config
Authorization: Bearer <access_token>
```

响应示例：
```json
{
  "enable_search": true,
  "enable_math": true,
  "tavily_api_key": "tvl****1234"
}
```

### 更新工具配置

```bash
PUT /api/v1/tools/config
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "enable_search": true,
  "enable_math": false
}
```

## 监控和审计

所有工具调用都会被记录和监控：

### 调用日志

记录每次工具调用的参数和结果：
- 工具名称
- 输入参数
- 输出结果
- 执行状态（成功/失败）
- 执行时间
- 错误信息（如果失败）

### Prometheus 指标

可监控的指标：
- `tool_calls_total` - 工具调用总次数（按租户、工具、状态）
- `tool_execution_duration` - 工具执行时间分布
- `active_tool_calls` - 当前活跃工具调用数

访问指标：
```bash
GET /metrics
```

### Grafana Dashboard

（规划中）可视化监控数据

## 前端使用

### 工具事件展示

当 Agent 调用工具时，聊天界面会显示工具调用状态：

- **⚙️ 正在调用...** - 工具开始执行
- **✅ 完成** - 工具执行成功
- **❌ 失败** - 工具执行失败

### 选择工具使用 Agent

在前端聊天界面，从 Agent 选择器中选择 "工具使用 Agent (Phase 3)"。

## 安全说明

1. **域名白名单**: API 调用受域名白名单限制（规划中）
2. **文件隔离**: 文件操作限制在租户目录内（规划中）
3. **配额限制**: 防止滥用和意外的高额费用
4. **审计日志**: 所有调用都可追溯
5. **API Key 保护**: API Key 在配置接口中会脱敏显示

## 故障排查

### 问题：工具调用失败

**原因**：
- API Key 未配置或无效
- 网络连接问题
- 配额已用完

**解决方法**：
1. 检查环境变量或租户配置中的 API Key
2. 查看错误消息获取详细信息
3. 检查配额使用情况

### 问题：配额不足

**原因**：日配额或月配额已用完

**解决方法**：
1. 联系管理员增加配额
2. 等待配额重置（日配额每天重置，月配额每月重置）

### 问题：工具不响应

**原因**：工具执行超时或服务不可用

**解决方法**：
1. 检查网络连接
2. 查看后端日志
3. 尝试简化任务描述

## 后续改进

- [ ] 添加文件处理工具 (CSV/PDF)
- [ ] 添加自定义工具支持
- [ ] 添加工作流编排
- [ ] 添加 Grafana 监控面板
- [ ] 优化工具调用延迟
