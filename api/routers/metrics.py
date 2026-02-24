"""
监控端点 - 暴露指标数据

提供 /metrics 端点用于查询系统指标。
"""

from fastapi import APIRouter
from pydantic import BaseModel

from api.metrics import metrics_store


router = APIRouter(prefix="/api/v1", tags=["Monitoring"])


class MetricsResponse(BaseModel):
    """指标响应模型"""
    uptime_seconds: float
    requests_total: int
    errors_total: int
    chat_requests_total: int
    active_sessions: int
    average_latency_ms: float
    p95_latency_ms: float
    error_rate: float
    tokens_used_total: int
    tokens_by_tenant: dict
    timestamp: str


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="获取系统指标",
    description="获取当前系统的核心性能指标"
)
async def get_metrics() -> MetricsResponse:
    """
    获取系统指标

    返回当前的核心性能指标，包括：
    - 系统运行时间
    - 请求总数和错误数
    - 聊天请求数
    - 活跃会话数
    - 平均和 P95 延迟
    - 错误率
    - Token 使用量

    Returns:
        MetricsResponse: 指标数据

    示例:
        GET /api/v1/metrics

        {
          "uptime_seconds": 3600,
          "requests_total": 1000,
          "errors_total": 10,
          "chat_requests_total": 500,
          "active_sessions": 20,
          "average_latency_ms": 150.5,
          "p95_latency_ms": 300.0,
          "error_rate": 0.01,
          "tokens_used_total": 50000,
          "tokens_by_tenant": {
            "tenant-001": 30000,
            "tenant-002": 20000
          },
          "timestamp": "2026-02-24T10:30:00"
        }
    """
    metrics = metrics_store.get_metrics()

    return MetricsResponse(**metrics)


@router.get(
    "/health",
    summary="健康检查",
    description="检查服务是否健康运行"
)
async def health_check():
    """
    健康检查端点

    返回服务状态，用于负载均衡器健康检查。

    Returns:
        {
            "status": "healthy",
            "timestamp": "2026-02-24T10:30:00"
        }
    """
    return {
        "status": "healthy",
        "timestamp": metrics_store.get_metrics()["timestamp"]
    }


@router.get(
    "/stats",
    summary="获取详细统计",
    description="获取更详细的系统统计信息"
)
async def get_stats():
    """
    获取详细统计

    返回比 /metrics 更详细的统计信息。
    """
    metrics = metrics_store.get_metrics()

    # 计算速率
    uptime = metrics["uptime_seconds"]
    if uptime > 0:
        requests_per_second = metrics["requests_total"] / uptime
    else:
        requests_per_second = 0

    return {
        **metrics,
        "requests_per_second": round(requests_per_second, 2),
        "latency_samples": len(metrics_store.latency_samples),
        "tracked_tenants": len(metrics["tokens_by_tenant"])
    }
