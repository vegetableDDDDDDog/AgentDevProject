# AgentDevProject 完整 ORM 使用流程

基于当前工程的实际代码，演示从 API 请求到数据库保存的完整流程。

## 📋 完整流程概览

```
用户发送 HTTP POST 请求
    ↓
┌─────────────────────────────────────────┐
│  Layer 1: API 层 (api/routers/sessions.py) │  ← 接收 HTTP 请求
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Layer 2: Service 层 (services/         │  ← 业务逻辑处理
│              session_service.py)          │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Layer 3: ORM 层 (services/database.py) │  ← 定义数据库模型
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Layer 4: 数据库 (SQLite)                │  ← 实际存储
└─────────────────────────────────────────┘
```

---

## 🚀 场景：用户创建一个新的聊天会话

### Step 1: 用户发送 HTTP 请求

```bash
# 用户在终端或前端执行：
curl -X POST "http://localhost:8000/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "chat",
    "config": {"model": "gpt-4", "temperature": 0.7},
    "metadata": {"source": "web"}
  }'
```

---

### Step 2: API 层接收请求

**文件**: `api/routers/sessions.py`

```python
# ============================================
# api/routers/sessions.py (第20-52行)
# ============================================

from fastapi import APIRouter
from api.schemas import SessionCreateRequest, SessionResponse
from services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post(
    "",
    response_model=SessionResponse,
    summary="Create a new session",
    description="Create a new conversation session for an agent type"
)
async def create_session(request: SessionCreateRequest) -> SessionResponse:
    """
    创建新的对话会话。

    流程:
    1. 接收 HTTP POST 请求
    2. 验证请求数据（Pydantic 自动验证）
    3. 调用 Service 层创建会话
    4. 返回创建的会话信息
    """
    # ✅ 第1步：创建 Service 层实例
    service = SessionService()

    # ✅ 第2步：调用 Service 层方法创建会话
    # 这里会进入 services/session_service.py
    session = service.create_session(
        agent_type=request.agent_type,    # "chat"
        config=request.config,            # {"model": "gpt-4"}
        metadata=request.metadata         # {"source": "web"}
    )

    # ✅ 第3步：返回响应给用户
    return SessionResponse(
        id=session.id,                   # UUID: "abc-123-def"
        agent_type=session.agent_type,   # "chat"
        config=session.config,           # {"model": "gpt-4"}
        metadata=session.meta,           # {"source": "web"}
        created_at=session.created_at,   # datetime 对象
        updated_at=session.updated_at,   # datetime 对象
        message_count=0
    )
```

**此时发生了什么**：
- ✅ FastAPI 接收到 HTTP 请求
- ✅ 自动解析 JSON 到 Pydantic 模型
- ✅ 调用 `SessionService.create_session()`
- ⏳ 现在进入 Service 层

---

### Step 3: Service 层处理业务逻辑

**文件**: `services/session_service.py`

```python
# ============================================
# services/session_service.py (第31-72行)
# ============================================

from sqlalchemy.orm import Session as SQLSession
from sqlalchemy.exc import SQLAlchemyError
from services.database import Session, SessionLocal

class SessionService:
    """会话服务类 - 管理会话的 CRUD 操作"""

    def create_session(
        self,
        agent_type: str,
        config: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> Session:
        """
        创建具有指定 Agent 类型和配置的新会话。

        完整流程:
        1. 验证输入参数
        2. 创建数据库会话
        3. 创建 ORM 对象（内存中）
        4. 添加到会话并提交
        5. 返回创建的对象
        """

        # ✅ 验证输入
        if not agent_type or not isinstance(agent_type, str):
            raise ValueError("agent_type 必须是非空字符串")

        # ✅ 创建数据库会话（从连接池获取连接）
        db: SQLSession = SessionLocal()
        # ↑ SessionLocal() 在 services/database.py:36 定义
        # ↑ 这是 SQLAlchemy 的会话工厂
        # ↑ 每次调用都创建一个新的会话实例

        try:
            # ✅ 创建 ORM 对象（此时只在内存中）
            session = Session(
                agent_type=agent_type,
                config=config,
                meta=metadata  # 注意：数据库列名是 meta，不是 metadata
            )
            # ↑ Session 是 services/database.py:160 定义 ORM 模型
            # ↑ 此时 session 只是一个 Python 对象
            # ↑ 还没有写入数据库！

            # ✅ 添加到会话（标记为待保存）
            db.add(session)
            # ↑ 将 session 加入到 SQLAlchemy 的待处理列表
            # ↑ 此时仍然在内存中，还没有发送 SQL

            # ✅ 提交到数据库（真正的写入）
            db.commit()
            # ↑ 此时 SQLAlchemy 会生成并发送 SQL:
            """
            INSERT INTO sessions (
                id, tenant_id, agent_type, created_at, updated_at, config, meta
            ) VALUES (
                'uuid-abc-123', 'default-tenant', 'chat',
                '2026-02-22 10:00:00', '2026-02-22 10:00:00',
                '{"model": "gpt-4"}', '{"source": "web"}'
            );
            """

            # ✅ 刷新对象（获取数据库生成的值）
            db.refresh(session)
            # ↑ 虽然 id 是在 Python 中生成的，但为了确保对象是最新的
            return session

        except SQLAlchemyError as e:
            # ❌ 出错时回滚
            db.rollback()
            # ↑ 撤销所有未提交的更改
            raise ValueError(f"创建会话失败: {str(e)}")

        finally:
            # ✅ 关闭会话（释放连接回连接池）
            db.close()
            # ↑ 将数据库连接返回连接池，供下次使用
```

**此时发生了什么**：
- ✅ 创建了 Python 对象 `Session(agent_type="chat")`
- ✅ `db.add(session)` 标记为待保存
- ✅ `db.commit()` 生成并执行 `INSERT` SQL
- ✅ 数据真正写入 `data/agent_platform.db`
- ⏳ 现在返回到 API 层

---

### Step 4: ORM 层定义模型

**文件**: `services/database.py`

```python
# ============================================
# services/database.py (第160-193行)
# ============================================

from sqlalchemy.orm import declarative_base

# 创建基类（所有 ORM 模型继承它）
Base = declarative_base()

# ORM 模型定义
class Session(Base):
    """
    Agent 会话 ORM 模型。

    这个类对应数据库中的 sessions 表。
    每个属性对应表中的一列。
    """
    __tablename__ = "sessions"  # ← 指定表名

    # 定义列（对应数据库表的列）
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())  # ← 自动生成 UUID
    )
    tenant_id = Column(
        String,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False
    )
    agent_type = Column(String(50), nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    config = Column(JSON, nullable=True)  # ← 存储 JSON 配置
    meta = Column(JSON, nullable=True)    # ← 存储元数据

    # 定义关系（关联其他表）
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )

    def __repr__(self):
        return f"<Session(id={self.id}, agent_type={self.agent_type})>"
```

**ORM 魔法**：
```python
# 当你写：
session = Session(agent_type="chat", config={"model": "gpt-4"})

# SQLAlchemy 在后台做了：
# 1. 创建 Python 对象
# 2. 当 db.add(session) 时，将对象转换为 INSERT 语句
# 3. 当 db.commit() 时，执行 SQL 并保存到数据库
```

---

### Step 5: 数据库层实际存储

**数据库文件**: `data/agent_platform.db`

```sql
-- 数据库中的实际表结构（SQLite）
CREATE TABLE sessions (
    id VARCHAR PRIMARY KEY,           -- 'uuid-abc-123'
    tenant_id VARCHAR NOT NULL,      -- 'default-tenant'
    agent_type VARCHAR(50) NOT NULL,  -- 'chat'
    created_at TIMESTAMP NOT NULL,   -- '2026-02-22 10:00:00'
    updated_at TIMESTAMP NOT NULL,   -- '2026-02-22 10:00:00'
    config JSON,                     -- '{"model": "gpt-4"}'
    meta JSON                        -- '{"source": "web"}'
);

-- 插入的数据
INSERT INTO sessions VALUES (
    'uuid-abc-123', 'default-tenant', 'chat',
    '2026-02-22 10:00:00', '2026-02-22 10:00:00',
    '{"model": "gpt-4"}', '{"source": "web"}'
);
```

---

## 📊 完整数据流图

```
┌─────────────────────────────────────────────────────────────┐
│ 1. HTTP 请求层                                               │
└─────────────────────────────────────────────────────────────┘
POST /api/v1/sessions
Body: {"agent_type": "chat", "config": {...}}
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. API 层 (api/routers/sessions.py:26)                      │
│                                                             │
│ async def create_session(request: SessionCreateRequest):    │
│     service = SessionService()                              │
│     session = service.create_session(...)                   │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Service 层 (services/session_service.py:36-65)          │
│                                                             │
│ db = SessionLocal()              # 创建数据库会话            │
│ session = Session(...)            # 创建 ORM 对象（内存）     │
│ db.add(session)                  # 标记为待保存             │
│ db.commit()                      # 提交到数据库（INSERT SQL） │
│ db.refresh(session)              # 刷新对象                 │
│ db.close()                       # 关闭会话                 │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. ORM 层 (services/database.py:160-193)                   │
│                                                             │
│ class Session(Base):                                        │
│     __tablename__ = "sessions"                              │
│     id = Column(String, primary_key)                         │
│     agent_type = Column(String)                              │
│     ...                                                       │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. SQL 执行层 (SQLAlchemy 自动生成)                        │
│                                                             │
│ INSERT INTO sessions (id, agent_type, config, ...)          │
│ VALUES ('uuid-123', 'chat', '{"model":"gpt-4"}', ...)      │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. 数据库层 (SQLite: data/agent_platform.db)               │
│                                                             │
│ 实际存储数据                                                 │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. 返回响应                                                 │
│                                                             │
│ SessionResponse(id="uuid-123", agent_type="chat", ...)    │
│     ↓                                                       │
│ HTTP 200 OK + JSON                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 完整示例：查询会话历史

### 场景：用户查看某个会话的所有消息

**API 请求**:
```bash
GET /api/v1/sessions/uuid-abc-123
```

### API 层

```python
# api/routers/sessions.py (第110-144行)

@router.get("/{session_id}")
async def get_session(session_id: str) -> SessionResponse:
    """获取会话详情。"""
    service = SessionService()

    # 调用 Service 层查询会话
    session = service.get_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # 获取消息计数
    messages = service.get_messages(session_id, limit=1000)

    return SessionResponse(
        id=session.id,
        agent_type=session.agent_type,
        config=session.config,
        metadata=session.meta,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(messages)
    )
```

### Service 层

```python
# services/session_service.py (第72-95行)

def get_session(self, session_id: str) -> Optional[Session]:
    """通过 ID 检索会话。"""
    if not session_id:
        raise ValueError("必须提供 session_id")

    db: SQLSession = SessionLocal()
    try:
        # ✅ 方式1：使用 filter 查询
        session = db.query(Session).filter(
            Session.id == session_id
        ).first()
        # ↑ 生成 SQL:
        # SELECT * FROM sessions WHERE id = 'uuid-abc-123' LIMIT 1

        # ↑ SQLAlchemy 自动将 Session 类转换为 sessions 表
        # ↑ filter(Session.id == session_id) 转换为 WHERE 子句
        # ↑ .first() 添加 LIMIT 1

        return session  # 返回 Session 对象或 None
    finally:
        db.close()
```

### ORM 层自动转换

```python
# services/database.py - ORM 模型

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    agent_type = Column(String)
    # ...

# 当你写:
db.query(Session).filter(Session.id == "uuid-123").first()

# SQLAlchemy 自动转换为:
# SELECT * FROM sessions WHERE id = 'uuid-123' LIMIT 1
```

---

## 🔗 关系查询示例

### 场景：获取会话及其所有消息

```python
# services/session_service.py (第279-315行)

def get_session_history(self, session_id: str) -> dict:
    """获取完整的会话历史，包括会话信息和所有消息。"""
    db: SQLSession = SessionLocal()
    try:
        # ✅ 步骤1：查询会话
        session = db.query(Session).filter(
            Session.id == session_id
        ).first()

        if not session:
            raise ValueError(f"未找到 ID 为 '{session_id}' 的会话")

        # ✅ 步骤2：使用关系查询消息
        # 方式1：通过关系属性（会触发额外查询）
        # messages = session.messages
        # ↑ 这会自动执行: SELECT * FROM messages WHERE session_id = '...'

        # 方式2：显式查询（更高效）
        messages = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.asc())  # 按时间升序
            .all()
        )
        # ↑ 生成 SQL:
        # SELECT * FROM messages
        # WHERE session_id = 'uuid-abc-123'
        # ORDER BY created_at ASC

        return {
            "session": session,   # Session 对象
            "messages": messages  # Message 对象列表
        }
    finally:
        db.close()
```

### ORM 关系定义

```python
# services/database.py

class Session(Base):
    # 一个会话有多个消息
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )

class Message(Base):
    session_id = Column(String, ForeignKey("sessions.id"))
    # 多个消息属于一个会话
    session = relationship("Session", back_populates="messages")
```

---

## 💾 实际运行示例

让我们运行一个真实的例子：

```bash
# 进入项目目录
cd /home/wineash/PycharmProjects/AgentDevProject/.worktrees/phase2-multi-tenant

# 启动 Python 交互式环境
python3
```

```python
# 在 Python REPL 中执行：

# ============================================
# 1. 导入必要的模块
# ============================================
from services.session_service import SessionService
from services.database import SessionLocal, Session, Message
import json

# ============================================
# 2. 创建 Service 实例
# ============================================
service = SessionService()

# ============================================
# 3. 创建一个新会话
# ============================================
print("=" * 70)
print("步骤1: 创建新会话")
print("=" * 70)

session = service.create_session(
    agent_type="chat",
    config={"model": "gpt-4", "temperature": 0.7},
    metadata={"source": "test", "user": "demo"}
)

print(f"✅ 会话创建成功！")
print(f"   ID: {session.id}")
print(f"   Agent 类型: {session.agent_type}")
print(f"   配置: {session.config}")
print(f"   元数据: {session.meta}")

# ============================================
# 4. 向会话添加消息
# ============================================
print("\n" + "=" * 70)
print("步骤2: 添加用户消息")
print("=" * 70)

user_msg = service.add_message(
    session_id=session.id,
    role="user",
    content="你好！"
)

print(f"✅ 用户消息添加成功！")
print(f"   消息 ID: {user_msg.id}")
print(f"   角色: {user_msg.role}")
print(f"   内容: {user_msg.content}")

# ============================================
# 5. 添加助手回复
# ============================================
print("\n" + "=" * 70)
print("步骤3: 添加助手消息")
print("=" * 70)

assistant_msg = service.add_message(
    session_id=session.id,
    role="assistant",
    content="你好！有什么可以帮助你的吗？"
)

print(f"✅ 助手消息添加成功！")
print(f"   消息 ID: {assistant_msg.id}")
print(f"   内容: {assistant_msg.content}")

# ============================================
# 6. 查询会话历史
# ============================================
print("\n" + "=" * 70)
print("步骤4: 查询会话历史")
print("=" * 70)

history = service.get_session_history(session.id)

print(f"会话 ID: {history['session'].id}")
print(f"Agent 类型: {history['session'].agent_type}")
print(f"消息总数: {len(history['messages'])}")
print(f"\n消息列表:")
for i, msg in enumerate(history['messages'], 1):
    print(f"  {i}. [{msg.role}] {msg.content}")

# ============================================
# 7. 验证数据库中的数据
# ============================================
print("\n" + "=" * 70)
print("步骤5: 验证数据库中的实际数据")
print("=" * 70)

db = SessionLocal()
try:
    # 查询会话
    session_record = db.query(Session).filter(
        Session.id == session.id
    ).first()

    print(f"数据库中的会话记录:")
    print(f"  ID: {session_record.id}")
    print(f"  Agent 类型: {session_record.agent_type}")
    print(f"  配置 (JSON): {session_record.config}")
    print(f"  元数据 (JSON): {session_record.meta}")

    # 查询消息
    message_records = db.query(Message).filter(
        Message.session_id == session.id
    ).order_by(Message.created_at.asc()).all()

    print(f"\n数据库中的消息记录:")
    for msg in message_records:
        print(f"  [{msg.role}] {msg.content} (ID: {msg.id})")

finally:
    db.close()

print("\n" + "=" * 70)
print("✅ 完整流程演示完成！")
print("=" * 70)
```

---

## 📊 关键点总结

### 1. 分层架构

| 层级 | 文件 | 作用 |
|-----|------|------|
| API 层 | `api/routers/sessions.py` | 接收 HTTP 请求，返回响应 |
| Service 层 | `services/session_service.py` | 业务逻辑，事务管理 |
| ORM 层 | `services/database.py` | 定义数据模型，映射到数据库 |
| 数据库层 | `data/agent_platform.db` | 实际存储数据 |

### 2. 核心对象

| 对象 | 类型 | 作用 |
|-----|------|------|
| `SessionLocal()` | 工厂函数 | 创建数据库会话 |
| `db = SessionLocal()` | 会话实例 | 管理数据库连接和事务 |
| `Session(...)` | ORM 模型 | Python 对象，映射到数据库行 |
| `db.add(session)` | 方法 | 标记对象为待保存 |
| `db.commit()` | 方法 | 提交事务，执行 SQL |
| `db.close()` | 方法 | 关闭会话，释放连接 |

### 3. ORM 映射

| Python 代码 | SQL 操作 |
|-----------|---------|
| `Session(agent_type="chat")` | 创建 Python 对象（内存） |
| `db.add(session)` | 添加到待处理列表（内存） |
| `db.commit()` | `INSERT INTO sessions ...` |
| `db.query(Session).filter(...)` | `SELECT * FROM sessions WHERE ...` |
| `session.agent_type = "chat"` | `UPDATE sessions SET agent_type=...` |
| `db.delete(session)` | `DELETE FROM sessions WHERE ...` |

---

## 🎯 实际运行输出

当您运行上面的代码时，会看到：

```
======================================================================
步骤1: 创建新会话
======================================================================
✅ 会话创建成功！
   ID: uuid-abc-123
   Agent 类型: chat
   配置: {'model': 'gpt-4', 'temperature': 0.7}
   元数据: {'source': 'test', 'user': 'demo'}

======================================================================
步骤2: 添加用户消息
======================================================================
✅ 用户消息添加成功！
   消息 ID: uuid-msg-456
   角色: user
   内容: 你好！

======================================================================
步骤3: 添加助手消息
======================================================================
✅ 助手消息添加成功！
   消息 ID: uuid-msg-789
   内容: 你好！有什么可以帮助你的吗？

======================================================================
步骤4: 查询会话历史
======================================================================
会话 ID: uuid-abc-123
Agent 类型: chat
消息总数: 2

消息列表:
  1. [user] 你好！
  2. [assistant] 你好！有什么可以帮助你的吗？

======================================================================
步骤5: 验证数据库中的实际数据
======================================================================
数据库中的会话记录:
  ID: uuid-abc-123
  Agent 类型: chat
  配置 (JSON): {'model': 'gpt-4', 'temperature': 0.7}
  元数据 (JSON): {'source': 'test', 'user': 'demo'}

数据库中的消息记录:
  [user] 你好！ (ID: uuid-msg-456)
  [assistant] 你好！有什么可以帮助你的吗？ (ID: uuid-msg-789)

======================================================================
✅ 完整流程演示完成！
======================================================================
```

---

这就是 **AgentDevProject** 中 ORM 的完整使用流程！从 HTTP 请求到数据库存储，每一个环节都清晰可见。🎉
