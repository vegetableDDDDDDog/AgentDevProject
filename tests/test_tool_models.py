"""
工具调用数据模型测试

测试 ToolCallLog 和 TenantToolQuota 模型的基本功能。
"""
import pytest
import uuid
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.database import Base, ToolCallLog, TenantToolQuota


def test_tool_call_log_creation():
    """测试工具调用日志模型创建"""
    # 创建测试租户ID
    tenant_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # 创建日志实例
    log = ToolCallLog(
        tenant_id=tenant_id,
        session_id=session_id,
        user_id=user_id,
        tool_name="tavily_search",
        tool_input={"query": "test query"},
        tool_output="test result",
        status="success",
        execution_time_ms=100
    )

    assert log.tool_name == "tavily_search"
    assert log.status == "success"
    assert log.execution_time_ms == 100
    assert log.tenant_id == tenant_id
    assert log.session_id == session_id
    assert log.user_id == user_id


def test_tenant_tool_quota_creation():
    """测试租户工具配额模型创建"""
    tenant_id = str(uuid.uuid4())

    # 创建配额实例
    quota = TenantToolQuota(
        tenant_id=tenant_id,
        tool_name="tavily_search",
        max_calls_per_day=100,
        max_calls_per_month=1000,
        current_day_calls=0,
        current_month_calls=0,
        last_reset_date=date.today()
    )

    assert quota.tenant_id == tenant_id
    assert quota.tool_name == "tavily_search"
    assert quota.max_calls_per_day == 100
    assert quota.max_calls_per_month == 1000
    assert quota.current_day_calls == 0
    assert quota.current_month_calls == 0


def test_tool_call_log_repr():
    """测试 ToolCallLog 的 __repr__ 方法"""
    log_id = str(uuid.uuid4())
    log = ToolCallLog(
        id=log_id,
        tenant_id=str(uuid.uuid4()),
        tool_name="test_tool",
        status="success"
    )

    repr_str = repr(log)
    assert "ToolCallLog" in repr_str
    assert log_id in repr_str
    assert "test_tool" in repr_str
    assert "success" in repr_str


def test_tenant_tool_quota_repr():
    """测试 TenantToolQuota 的 __repr__ 方法"""
    tenant_id = str(uuid.uuid4())
    quota = TenantToolQuota(
        tenant_id=tenant_id,
        tool_name="test_tool"
    )

    repr_str = repr(quota)
    assert "TenantToolQuota" in repr_str
    assert tenant_id in repr_str
    assert "test_tool" in repr_str
