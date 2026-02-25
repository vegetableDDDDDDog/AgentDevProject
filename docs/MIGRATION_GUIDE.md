# 数据库迁移说明

## 当前状态

数据库中共有 **10 个表**：

### Phase 1 表（原始表）
- sessions
- messages
- agent_logs

### Phase 2 表（多租户基础）
- tenants
- users
- api_keys
- tenant_quotas

### Phase 3 表（工具调用）
- tool_call_logs
- tenant_tool_quotas

## 迁移脚本

### Phase 2: add_tenant_support.py
**必须手动执行** - 因为涉及数据迁移：
- 修改现有表结构
- 迁移现有数据
- 创建默认租户

**执行方式**：
```bash
python migrations/add_tenant_support.py
```

### Phase 3: add_tool_calling_tables.py
**可以自动执行** - 只创建新表：
```bash
# 方式 1: 使用迁移脚本
python migrations/add_tool_calling_tables.py

# 方式 2: 使用自动创建（推荐）
python -c "from services.database import init_db; init_db()"
```

**推荐**: 方式 2，因为更简单

## 数据库初始化

### 开发环境
```bash
# 首次初始化
python -c "from services.database import init_db; init_db()"
```

### 生产环境
```bash
# 执行迁移脚本（按顺序）
python migrations/add_tenant_support.py      # Phase 2
python migrations/add_tool_calling_tables.py  # Phase 3
```

## 表关系

```
tenants (租户)
  ├─ users (用户)
  ├─ api_keys (API密钥)
  ├─ tenant_quotas (一般配额)
  ├─ tenant_tool_quotas (工具配额)
  └─ sessions → messages → agent_logs

tool_call_logs (工具调用日志，关联 tenant)
```

## 避免重复迁移

所有迁移脚本都是**幂等的**：
- 可以安全地多次执行
- SQLAlchemy 会检查表是否存在
- 已存在的表不会被重复创建
