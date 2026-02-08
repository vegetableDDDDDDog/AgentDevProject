# 工具调用 Agent 使用指南

> 📅 创建时间：2026-02-04
> 🎯 功能：为 Agent 添加工具使用能力，让 AI 不仅能聊天，还能执行实际操作

---

## 📚 什么是工具调用？

工具调用（Tool Calling）是 Agent 的核心能力之一。通过工具调用，AI 模型可以：

- 🔧 执行数学计算
- ⏰ 获取实时信息（时间、日期）
- 🌐 搜索网络信息
- 📊 处理和分析数据
- 🎨 生成特定格式的内容

**核心优势**：让 AI 从"只会聊天"变成"能实际做事"！

---

## 🛠️ 可用工具

### 1. 计算器 (calculator)
执行数学计算

**支持运算**：`+`, `-`, `*`, `/`, `**` (幂运算), `%` (取模)

**示例**：
```python
calculator.invoke({"expression": "2 + 2"})
# 输出: "计算结果: 4"

calculator.invoke({"expression": "10 ** 2"})
# 输出: "计算结果: 100"

calculator.invoke({"expression": "(10 * 25 + 15) * 0.8"})
# 输出: "计算结果: 212.0"
```

### 2. 时间工具 (get_current_time)
获取当前时间

**参数**：
- `full` - 完整日期时间 (默认)
- `date` - 仅日期
- `time` - 仅时间

**示例**：
```python
get_current_time.invoke({"format": "full"})
# 输出: "2026-02-04 23:26:27"

get_current_time.invoke({"format": "date"})
# 输出: "2026-02-04"

get_current_time.invoke({"format": "time"})
# 输出: "23:26:27"
```

### 3. 时间戳 (get_current_timestamp)
获取 Unix 时间戳

**示例**：
```python
get_current_timestamp.invoke({})
# 输出: "当前时间戳: 1770218787"
```

### 4. 字数统计 (word_counter)
统计文本信息

**统计内容**：
- 字符数
- 单词数
- 行数

**示例**：
```python
text = "工具调用 Agent 是一个强大的功能。"
word_counter.invoke({"text": text})
# 输出:
# 📊 文本统计结果:
# ━━━━━━━━━━━━━━━━━━
# 字符数: 58
# 单词数: 6
# 行数: 4
# ━━━━━━━━━━━━━━━━━━
```

### 5. ASCII 艺术字 (ascii_art_generator)
生成装饰性文本

**参数**：
- `text`: 要转换的文本
- `style`: 风格 (banner 或 standard)

**示例**：
```python
ascii_art_generator.invoke({"text": "HELLO", "style": "banner"})
# 输出:
# ╔════════╗
# ║  HELLO ║
# ╚════════╝
```

---

## 🚀 使用方法

### 方法 1: 直接调用工具

运行简化版交互脚本：
```bash
python3 tool_agent_simple.py
```

### 方法 2: 测试所有工具

运行工具测试脚本：
```bash
python3 test_tools.py
```

### 方法 3: 在代码中使用

```python
from tool_agent import calculator, get_current_time

# 使用计算器
result = calculator.invoke({"expression": "123 * 456"})
print(result)

# 使用时间工具
time = get_current_time.invoke({"format": "full"})
print(time)
```

---

## 📖 实际应用场景

### 场景 1: 数学计算助手
用户问题："帮我算一下，如果我有 1000 元，买 5 本书，每本 68 元，还剩多少钱？"

**Agent 思考过程**：
1. 识别需要计算
2. 调用 `calculator` 工具
3. 执行: `1000 - 5 * 68`
4. 返回结果并解释

### 场景 2: 时间提醒助手
用户问题："现在几点了？还有多久到 2026 年春节？"

**Agent 思考过程**：
1. 识别需要时间信息
2. 调用 `get_current_time` 工具
3. 计算时间差
4. 返回友好的回复

### 场景 3: 文本分析助手
用户问题："帮我统计这段文章有多少字..."

**Agent 思考过程**：
1. 识别需要统计
2. 调用 `word_counter` 工具
3. 解析统计结果
4. 返回格式化的报告

---

## 🔍 代码结构

```
tool_agent.py           # 主程序（包含 Agent 和工具定义）
├── @tool 装饰器        # 定义工具
├── create_tool_agent() # 创建带工具的 Agent
└── main()             # 交互循环

tool_agent_simple.py   # 简化版（直接调用工具）
test_tools.py         # 工具测试脚本
```

---

## 💡 扩展新工具

添加自定义工具非常简单：

```python
from langchain_core.tools import tool

@tool
def my_custom_tool(param: str) -> str:
    """
    工具描述（AI 会看到这个描述）
    """
    # 实现工具逻辑
    result = do_something(param)
    return f"处理结果: {result}"
```

**然后在 `create_tool_agent()` 中注册**：
```python
tools = [
    calculator,
    get_current_time,
    my_custom_tool,  # 添加新工具
]
```

---

## 🎯 最佳实践

1. **工具命名**：使用清晰、描述性的名称
2. **文档字符串**：详细说明工具功能、参数、示例
3. **错误处理**：捕获异常并返回友好错误信息
4. **参数验证**：检查输入参数的有效性
5. **结果格式化**：返回清晰、易读的结果

---

## 🔧 故障排除

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 工具未被执行 | 模型未识别到需求 | 调整提示词，明确说明工具用途 |
| 计算错误 | 表达式格式不正确 | 使用标准数学表达式语法 |
| 参数错误 | 参数类型或值不匹配 | 检查工具定义和传入参数 |

---

## 📊 与普通 Agent 的对比

| 特性 | 普通 Agent | 工具调用 Agent |
|------|-----------|---------------|
| 对话能力 | ✅ | ✅ |
| 历史记忆 | ✅ | ✅ |
| 执行操作 | ❌ | ✅ |
| 实时信息 | ❌ | ✅ |
| 数据处理 | ❌ | ✅ |

---

## 🚀 下一步

- [ ] 添加搜索工具（网络搜索）
- [ ] 添加文件操作工具
- [ ] 添加数据库查询工具
- [ ] 实现工具链（多个工具组合使用）
- [ ] 添加工具权限控制

---

**祝开发顺利！有问题随时查看本文档 📖**
