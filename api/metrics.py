"""
监控指标收集和暴露

提供核心业务指标的收集、统计和暴露功能。
"""

from time import time
from typing import Dict, List
from collections import defaultdict
from datetime import datetime, timedelta


# ============================================================================
# 指标存储（内存存储）
# ============================================================================

class MetricsStore:
    """
    指标存储类

    使用内存存储核心指标，支持查询和重置。
    """

    def __init__(self):
        """初始化指标存储"""
        # 计数器
        self.counters = defaultdict(int)

        # 直方图数据（用于计算延迟分布）
        self.latency_samples: List[float] = []

        # 时间戳
        self.start_time = datetime.now()

        # Token 使用统计
        self.tokens_used_by_tenant: Dict[str, int] = defaultdict(int)

    def increment(self, counter_name: str, value: int = 1, labels: Dict[str, str] = None):
        """
        增加计数器

        Args:
            counter_name: 计数器名称
            value: 增量值
            labels: 标签（暂不使用，预留）
        """
        self.counters[counter_name] += value

    def record_latency(self, latency_ms: float):
        """
        记录延迟样本

        Args:
            latency_ms: 延迟（毫秒）
        """
        self.latency_samples.append(latency_ms)

        # 只保留最近 1000 个样本
        if len(self.latency_samples) > 1000:
            self.latency_samples = self.latency_samples[-1000:]

    def add_tokens_used(self, tenant_id: str, tokens: int):
        """
        记录 Token 使用量

        Args:
            tenant_id: 租户 ID
            tokens: Token 数量
        """
        self.tokens_used_by_tenant[tenant_id] += tokens

    def get_average_latency(self) -> float:
        """
        获取平均延迟

        Returns:
            平均延迟（毫秒）
        """
        if not self.latency_samples:
            return 0.0
        return sum(self.latency_samples) / len(self.latency_samples)

    def get_p95_latency(self) -> float:
        """
        获取 P95 延迟

        Returns:
            P95 延迟（毫秒）
        """
        if not self.latency_samples:
            return 0.0
        sorted_samples = sorted(self.latency_samples)
        index = int(len(sorted_samples) * 0.95)
        return sorted_samples[index]

    def get_total_tokens(self) -> int:
        """
        获取总 Token 使用量

        Returns:
            所有租户的 Token 总和
        """
        return sum(self.tokens_used_by_tenant.values())

    def get_uptime_seconds(self) -> float:
        """
        获取运行时间（秒）

        Returns:
            从启动到现在的秒数
        """
        return (datetime.now() - self.start_time).total_seconds()

    def get_metrics(self) -> Dict:
        """
        获取所有指标

        Returns:
            包含所有指标的字典
        """
        return {
            "uptime_seconds": self.get_uptime_seconds(),
            "requests_total": self.counters["requests_total"],
            "errors_total": self.counters["errors_total"],
            "chat_requests_total": self.counters["chat_requests_total"],
            "active_sessions": self.counters["active_sessions"],
            "average_latency_ms": self.get_average_latency(),
            "p95_latency_ms": self.get_p95_latency(),
            "error_rate": self._calculate_error_rate(),
            "tokens_used_total": self.get_total_tokens(),
            "tokens_by_tenant": dict(self.tokens_used_by_tenant),
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_error_rate(self) -> float:
        """
        计算错误率

        Returns:
            错误率（0-1）
        """
        total = self.counters["requests_total"]
        errors = self.counters["errors_total"]
        if total == 0:
            return 0.0
        return errors / total


# ============================================================================
# 全局指标存储实例
# ============================================================================

metrics_store = MetricsStore()


# ============================================================================
# Prometheus 风格的指标类型定义（预留）
# ============================================================================

class Counter:
    """
    计数器指标

    示例:
        chat_requests = Counter("chat_requests_total", "Total chat requests")
        chat_requests.inc()
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def inc(self, amount: int = 1, labels: Dict[str, str] = None):
        """增加计数"""
        metrics_store.increment(self.name, amount, labels)


class Histogram:
    """
    直方图指标（用于延迟分布）

    示例:
        chat_duration = Histogram("chat_duration_seconds", "Chat request duration")
        chat_duration.observe(0.5)
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def observe(self, value: float):
        """记录观察值"""
        metrics_store.record_latency(value * 1000)  # 转换为毫秒


class Gauge:
    """
    仪表指标（可增减的数值）

    示例：
        active_sessions = Gauge("active_sessions", "Number of active sessions")
        active_sessions.set(10)
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def set(self, value: int):
        """设置值"""
        metrics_store.counters[self.name] = value

    def inc(self):
        """增加 1"""
        metrics_store.increment(self.name)

    def dec(self):
        """减少 1"""
        metrics_store.increment(self.name, -1)


# ============================================================================
# 预定义的指标
# ============================================================================

# 请求数量
requests_total = Counter("requests_total", "Total HTTP requests")
chat_requests_total = Counter("chat_requests_total", "Total chat requests")

# 延迟指标
chat_duration_seconds = Histogram("chat_duration_seconds", "Chat request duration")

# 错误数量
errors_total = Counter("errors_total", "Total errors")

# 会话指标
active_sessions = Gauge("active_sessions", "Number of active sessions")

# Token 使用
token_usage_total = Counter("token_usage_total", "Total tokens used")
