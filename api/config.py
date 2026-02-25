"""
API 配置管理

使用 pydantic-settings 从环境变量和 .env 文件管理配置。
提供类型安全和验证功能。
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    从环境变量加载的应用程序设置。

    配置优先级（从高到低）:
    1. 环境变量
    2. .env 文件
    3. 默认值

    示例 .env 文件:
        OPENAI_API_KEY=your-key-here
        DATABASE_URL=sqlite:///data/agent_platform.db
        LOG_LEVEL=INFO
    """

    # API 设置
    app_name: str = Field(default="Agent PaaS Platform", description="应用程序名称")
    app_version: str = Field(default="0.1.0", description="应用程序版本")
    api_prefix: str = Field(default="/api/v1", description="API URL 前缀")
    host: str = Field(default="0.0.0.0", description="服务器主机")
    port: int = Field(default=8000, description="服务器端口")
    debug: bool = Field(default=False, description="调试模式")

    # LLM 设置
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API 密钥（或兼容服务如智谱AI）"
    )
    openai_api_base: Optional[str] = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        description="OpenAI API 基础 URL"
    )
    model_name: str = Field(
        default="glm-4-flash",
        description="要使用的默认 LLM 模型"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM 生成的默认温度"
    )
    max_tokens: int = Field(
        default=2000,
        ge=1,
        description="LLM 生成的默认最大 token 数"
    )

    # 数据库设置
    database_url: str = Field(
        default="sqlite:///data/agent_platform.db",
        description="数据库连接 URL"
    )

    # 安全设置
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT token 签名密钥（生产环境必须更改）"
    )

    # 日志设置
    log_level: str = Field(
        default="INFO",
        description="日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_file: str = Field(
        default="logs/agent_platform.log",
        description="日志文件路径"
    )
    log_max_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="日志轮转前的最大日志文件大小"
    )
    log_backup_count: int = Field(
        default=5,
        description="要保留的备份日志文件数量"
    )

    # CORS 设置
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="允许的 CORS 源"
    )

    # Agent 设置
    max_execution_time: int = Field(
        default=300,  # 5 分钟
        ge=1,
        description="Agent 最大执行时间（秒）"
    )
    max_concurrent_agents: int = Field(
        default=10,
        ge=1,
        description="最大并发 Agent 执行数"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# 全局设置实例
settings = Settings()


def get_settings() -> Settings:
    """
    获取应用程序设置实例。

    此函数可用作 FastAPI 依赖项用于测试。

    Returns:
        Settings: 全局设置实例
    """
    return settings


def reload_settings() -> Settings:
    """
    从环境变量重新加载设置。

    用于测试或环境变量在运行时更改的情况。

    Returns:
        Settings: 新的设置实例
    """
    global settings
    settings = Settings()
    return settings
