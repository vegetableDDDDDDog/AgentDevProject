# Phase 3 快速启动指南

## 🚀 快速开始

### 1. 初始化数据库

```bash
# 创建 data 目录
mkdir -p data

# 初始化数据库（自动创建所有表）
python -c "from services.database import init_db; init_db()"
```

### 2. 验证表创建

```bash
python -c "
from services.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text(\"SELECT name FROM sqlite_master WHERE type='table'\"))
    tables = [row[0] for row in result]
    print('数据库表:', tables)
"
```

**预期输出**：
```
数据库表: ['agent_logs', 'api_keys', 'messages', 'sessions',
            'tenant_quotas', 'tenant_tool_quotas', 'tenants',
            'tool_call_logs', 'users']
```

### 3. 运行应用

```bash
# 启动 API 服务器
uvicorn api.main:app --reload

# 查看监控
# 访问: http://localhost:8000/metrics
```

## 📊 数据库表说明

### Phase 1 表
- `sessions` - 会话表
- `messages` - 消息表
- `agent_logs` - Agent 日志表

### Phase 2 表（多租户）
- `tenants` - 租户表
- `users` - 用户表
- `api_keys` - API 密钥表
- `tenant_quotas` - 一般配额表

### Phase 3 表（工具调用）
- `tool_call_logs` - 工具调用日志
- `tenant_tool_quotas` - 工具专用配额

## 🔄 数据库迁移

### Phase 2 → Phase 3 迁移

如果你之前在 Phase 2，现在要升级到 Phase 3：

```bash
# 1. 拉取最新代码
git pull

# 2. 安装新依赖
pip install -r requirements.txt

# 3. 初始化数据库（会自动创建 Phase 3 的表）
python -c "from services.database import init_db; init_db()"
```

**注意**：
- 不需要手动迁移脚本
- `init_db()` 会自动创建所有新表
- 已有的表不会被修改或删除

## 🧪 测试

```bash
# 测试模型导入
python -c "from services.database import ToolCallLog, TenantToolQuota; print('✅ 模型导入成功')"

# 测试服务导入
python -c "from services.tool_adapter import ToolAdapter; print('✅ 适配器导入成功')"
python -c "from services.quota_service import QuotaService; print('✅ 配额服务导入成功')"
python -c "from services.tool_registry import ToolRegistry; print('✅ 工具注册表导入成功')"
```

## 🔧 开发环境配置

### 环境变量

创建 `.env` 文件：
```bash
# 数据库
DATABASE_URL=sqlite:///data/agent_platform.db

# LLM API（可选）
OPENAI_API_KEY=your-key
OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4/

# 工具 API（可选）
TAVILY_API_KEY=tvly-your-key
```

## 📝 常见问题

**Q: 如何重置数据库？**
```bash
rm data/agent_platform.db
python -c "from services.database import init_db; init_db()"
```

**Q: 如何查看表结构？**
```bash
python -c "
from services.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('PRAGMA table_info(tool_call_logs)'))
    for row in result:
        print(f'{row[1]}: {row[2]}')
"
```

**Q: 如何备份数据？**
```bash
cp data/agent_platform.db data/agent_platform_backup_$(date +%Y%m%d).db
```
