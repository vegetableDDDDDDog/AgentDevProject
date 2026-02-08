# 工具调用 Agent - 快速入门

## 🚀 5 分钟快速上手

### 1. 测试工具功能
```bash
python3 test_tools.py
```

你会看到所有工具的演示：
- 🧮 计算器
- ⏰ 时间工具
- 📊 字数统计
- 🎨 ASCII 艺术字

### 2. 交互式体验
```bash
python3 tool_agent_simple.py
```

选择菜单选项，直接调用各个工具！

---

## 💡 核心概念

### 什么是工具调用？

工具调用让 AI 不仅能聊天，还能**执行实际操作**！

**对比示例**：

❌ **普通 Agent**：
```
用户: 123 * 456 等于多少？
AI: 让我想想...123 乘以 456 是一个数学计算...
```

✅ **工具调用 Agent**：
```
用户: 123 * 456 等于多少？
AI: 🔧 调用工具: calculator
   参数: {'expression': '123 * 456'}
   结果: 计算结果: 56088
```

---

## 📖 三个关键步骤

### 步骤 1: 定义工具
```python
from langchain_core.tools import tool

@tool
def my_calculator(expression: str) -> str:
    """执行数学计算"""
    try:
        result = eval(expression)
        return f"结果: {result}"
    except Exception as e:
        return f"错误: {e}"
```

### 步骤 2: 绑定工具
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="glm-4")
tools = [my_calculator]
llm_with_tools = llm.bind_tools(tools)
```

### 步骤 3: 检查并执行
```python
response = llm_with_tools.invoke("帮我计算 123 * 456")

if hasattr(response, 'tool_calls') and response.tool_calls:
    # AI 决定调用工具
    for tool_call in response.tool_calls:
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        # 执行工具...
```

---

## 🎯 实用示例

### 示例 1: 计算购物总价
```python
from tool_agent import calculator

# 问题：买 5 本书，每本 68 元，运费 15 元
result = calculator.invoke({"expression": "5 * 68 + 15"})
print(result)
# 输出: 计算结果: 355
```

### 示例 2: 获取时间
```python
from tool_agent import get_current_time

time = get_current_time.invoke({"format": "full"})
print(time)
# 输出: 2026-02-04 23:26:27
```

### 示例 3: 统计字数
```python
from tool_agent import word_counter

text = "工具调用让 AI 变得更强大！"
result = word_counter.invoke({"text": text})
print(result)
# 输出:
# 📊 文本统计结果:
# ━━━━━━━━━━━━━━━━━━
# 字符数: 15
# 单词数: 3
# 行数: 1
# ━━━━━━━━━━━━━━━━━━
```

---

## 🛠️ 添加自定义工具

### 场景：添加单位转换工具

```python
from langchain_core.tools import tool

@tool
def celsius_to_fahrenheit(celsius: float) -> str:
    """
    摄氏度转华氏度

    Args:
        celsius: 摄氏度数值

    Returns:
        转换后的华氏度
    """
    fahrenheit = celsius * 9/5 + 32
    return f"{celsius}°C = {fahrenheit:.1f}°F"
```

然后注册到工具列表：
```python
tools = [
    calculator,
    get_current_time,
    word_counter,
    celsius_to_fahrenheit,  # 新工具
]
```

---

## 🔍 调试技巧

### 1. 查看可用工具
```python
tools_map = {tool.name: tool for tool in tools}
print("可用工具:", list(tools_map.keys()))
```

### 2. 检查 AI 决策
```python
response = chain.invoke({"input": user_input})

print("消息类型:", type(response))
print("是否有工具调用:", hasattr(response, 'tool_calls'))
print("工具调用:", response.tool_calls if hasattr(response, 'tool_calls') else None)
```

### 3. 测试单个工具
```bash
python3 -c "from tool_agent import calculator; print(calculator.invoke({'expression': '2+2'}))"
```

---

## 📚 相关文档

- **详细文档**：`TOOL_AGENT_README.md`
- **项目总结**：`summary.md`
- **测试脚本**：`test_tools.py`

---

## 🎓 学习路径

1. ✅ **基础**：运行 `test_tools.py` 了解所有工具
2. ✅ **实践**：运行 `tool_agent_simple.py` 交互体验
3. ✅ **进阶**：阅读 `tool_agent.py` 源代码
4. ✅ **扩展**：添加自定义工具
5. ✅ **深入**：集成到实际应用

---

**开始探索工具调用的世界吧！🚀**
