import os
import sqlite3
import json
from dotenv import load_dotenv
# 1. 导入核心聊天模型
from langchain_openai import ChatOpenAI
# 2. 导入构建提示词的工具
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# 3. 导入管理聊天历史的工具
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
# 4. 导入消息类型（用于裁剪逻辑）
from langchain_core.messages import SystemMessage, BaseMessage
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage as LCSystemMessage

# 加载 .env 里的 API Key
load_dotenv()

# --- 配置参数 ---
# 保留的历史消息数量（建议 10-20 条，即 5-10 轮对话）
# 数字越大，记忆越长，但消耗的 token 越多
MAX_HISTORY_MESSAGES = 10

# --- 初始化模型 (大脑) ---
llm = ChatOpenAI(
    model="glm-4.7",  # 智谱模型
    temperature=0.6,  # 稍微活泼一点
)

# --- 准备一个"字典"来存储所有用户的聊天记录 ---
# 在真实项目中，这里通常是连接 Redis 或数据库
# 现在使用 SQLite 实现持久化存储

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "chat_history.db")


class SQLiteChatMessageHistory:
    """基于 SQLite 的聊天历史存储，支持程序重启后恢复"""

    def __init__(self, session_id: str, db_path: str = DB_PATH):
        self.session_id = session_id
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    @property
    def messages(self) -> list[BaseMessage]:
        """获取所有消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT type, content FROM chat_messages WHERE session_id = ? ORDER BY id',
            (self.session_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        messages = []
        for msg_type, content in rows:
            # 解析 content（可能是 JSON 字符串）
            try:
                content_data = json.loads(content)
            except:
                content_data = content

            if msg_type == 'system':
                messages.append(LCSystemMessage(content=content_data))
            elif msg_type == 'human':
                messages.append(HumanMessage(content=content_data))
            elif msg_type == 'ai':
                messages.append(AIMessage(content=content_data))
        return messages

    def add_message(self, message: BaseMessage):
        """添加一条消息"""
        self.add_messages([message])

    def add_messages(self, messages: list[BaseMessage]):
        """批量添加消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for message in messages:
            msg_type = message.type
            # 处理 content（可能是字典或字符串）
            if isinstance(message.content, dict):
                content = json.dumps(message.content, ensure_ascii=False)
            else:
                content = message.content

            cursor.execute(
                'INSERT INTO chat_messages (session_id, type, content) VALUES (?, ?, ?)',
                (self.session_id, msg_type, content)
            )
        conn.commit()
        conn.close()

    def clear(self):
        """清空所有消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM chat_messages WHERE session_id = ?',
            (self.session_id,)
        )
        conn.commit()
        conn.close()


# 内存缓存，避免每次都查询数据库
store: dict[str, SQLiteChatMessageHistory] = {}


# --- 定义获取历史记录的函数（带裁剪功能） ---
# 每次对话时，LangChain 会调用这个函数：
# "嘿，session_id 为 'user_123' 的人之前聊过什么？"
def get_session_history(session_id: str):
    """
    获取会话历史，并自动裁剪到指定长度

    Args:
        session_id: 会话 ID
    """
    if session_id not in store:
        store[session_id] = SQLiteChatMessageHistory(session_id)

    history = store[session_id]

    # 裁剪历史记录：保留最近的 MAX_HISTORY_MESSAGES 条消息
    messages = history.messages
    if len(messages) > MAX_HISTORY_MESSAGES:
        # 保留系统消息（如果存在）和最近的对话
        system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
        other_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]

        # 裁剪非系统消息，保留最近的 MAX_HISTORY_MESSAGES 条
        trimmed_messages = other_messages[-MAX_HISTORY_MESSAGES:]

        # 清空并重新添加消息
        history.clear()
        for msg in system_messages + trimmed_messages:
            history.add_message(msg)

        print(f"📝 [系统提示] 历史记录已裁剪，保留最近 {MAX_HISTORY_MESSAGES} 条消息")

    return history


# --- 设计提示词模板 (Prompt) ---
prompt = ChatPromptTemplate.from_messages([
    # 系统设定：给它一个人设
    ("system", "你是一个名叫'贾维斯'的 AI 助手，说话简练且幽默。"),

    # 关键点：这里预留了一个位置，专门放历史聊天记录
    MessagesPlaceholder(variable_name="history"),

    # 用户的当前输入
    ("human", "{input}"),
])

# --- 组装流水线 ---
# 1. 先把 history + input 塞进 prompt
# 2. 再传给 llm
chain = prompt | llm

# --- 加上记忆功能的外壳 ---
# 这个对象会自动处理"读取历史 -> 调用模型 -> 保存新回复"的全过程
with_message_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

# --- 启动聊天循环 ---
if __name__ == "__main__":
    print("🤖 贾维斯已上线！(输入 'exit' 或 'q' 退出)")
    print("-" * 50)
    print(f"⚙️  配置: 最多保留 {MAX_HISTORY_MESSAGES} 条历史消息（约 {MAX_HISTORY_MESSAGES // 2} 轮对话）")
    print(f"💾 持久化: {DB_PATH}")
    print("-" * 50)

    # 我们假设当前对话的用户 ID 是 "user_1"
    session_config = {"configurable": {"session_id": "user_1"}}

    while True:
        # 1. 获取用户输入
        user_input = input("You: ")

        # 退出机制
        if user_input.lower() in ["exit", "quit", "q"]:
            print("🤖 贾维斯: 下班啦，回见！")
            break

        # 清除历史命令
        if user_input.lower() in ["clear", "cls"]:
            history = get_session_history("user_1")
            history.clear()
            print("🗑️  历史记录已清除")
            continue

        # 查看状态命令
        if user_input.lower() in ["status", "info"]:
            history = get_session_history("user_1")
            msg_count = len(history.messages)
            print(f"📊 当前会话状态: {msg_count} 条消息")

            # 显示数据库中的所有会话
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT session_id FROM chat_messages')
            sessions = cursor.fetchall()
            conn.close()
            print(f"📁 数据库中共有 {len(sessions)} 个会话: {[s[0] for s in sessions]}")
            continue

        if not user_input.strip():
            continue

        # 2. 调用模型 (带有历史记录)
        # stream 方法可以让字一个个蹦出来，像打字机一样
        print("贾维斯: ", end="", flush=True)

        try:
            # 显示当前历史记录数量
            current_history = get_session_history("user_1")
            msg_count = len(current_history.messages)
            if msg_count > 0:
                print(f"💾 [记忆库: {msg_count} 条消息] ", end="")

            response = with_message_history.stream(
                {"input": user_input},
                config=session_config
            )

            # 实时打印每个生成的字
            for chunk in response:
                print(chunk.content, end="", flush=True)
            print()  # 换行

        except Exception as e:
            print(f"\n❌ 出错了: {e}")