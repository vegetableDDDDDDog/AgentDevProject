"""
工具相关的 Pydantic 模型

定义工具 API 的请求和响应数据模型。
"""
from pydantic import BaseModel, Field
from typing import Dict, Optional, List


class ToolResponse(BaseModel):
    """工具响应"""

    name: str = Field(description="工具名称")
    display_name: str = Field(description="工具显示名称")
    description: str = Field(description="工具描述")
    enabled: bool = Field(default=True, description="是否启用")
    quota_limit: Optional[int] = Field(default=None, description="配额限制（每天）")
    quota_used: Optional[int] = Field(default=None, description="已使用配额")
    quota_remaining: Optional[int] = Field(default=None, description="剩余配额")


class ToolUsageResponse(BaseModel):
    """工具使用统计响应"""

    total_calls: int = Field(description="总调用次数")
    by_tool: Dict[str, int] = Field(description="按工具分组的统计")
    success_rate: float = Field(description="成功率")


class ToolConfigRequest(BaseModel):
    """工具配置请求"""

    enable_search: bool = Field(default=True, description="启用网络搜索")
    enable_math: bool = Field(default=True, description="启用数学计算")
    tavily_api_key: Optional[str] = Field(default=None, description="Tavily API Key")


class ToolConfigResponse(BaseModel):
    """工具配置响应"""

    enable_search: bool = Field(description="启用网络搜索")
    enable_math: bool = Field(description="启用数学计算")
    tavily_api_key: Optional[str] = Field(default=None, description="Tavily API Key (脱敏)")
