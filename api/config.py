"""
API Configuration Management

Uses pydantic-settings to manage configuration from environment variables
and .env files. This provides type safety and validation.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Configuration priority (highest to lowest):
    1. Environment variables
    2. .env file
    3. Default values

    Example .env file:
        OPENAI_API_KEY=your-key-here
        DATABASE_URL=sqlite:///data/agent_platform.db
        LOG_LEVEL=INFO
    """

    # API Settings
    app_name: str = Field(default="Agent PaaS Platform", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    api_prefix: str = Field(default="/api/v1", description="API URL prefix")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")

    # LLM Settings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key (or compatible service like Zhipu AI)"
    )
    openai_api_base: Optional[str] = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        description="OpenAI API base URL"
    )
    model_name: str = Field(
        default="glm-4-flash",
        description="Default LLM model to use"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for LLM generation"
    )
    max_tokens: int = Field(
        default=2000,
        ge=1,
        description="Default max tokens for LLM generation"
    )

    # Database Settings
    database_url: str = Field(
        default="sqlite:///data/agent_platform.db",
        description="Database connection URL"
    )

    # Logging Settings
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_file: str = Field(
        default="logs/agent_platform.log",
        description="Log file path"
    )
    log_max_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum log file size before rotation"
    )
    log_backup_count: int = Field(
        default=5,
        description="Number of backup log files to keep"
    )

    # CORS Settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )

    # Agent Settings
    max_execution_time: int = Field(
        default=300,  # 5 minutes
        ge=1,
        description="Maximum agent execution time in seconds"
    )
    max_concurrent_agents: int = Field(
        default=10,
        ge=1,
        description="Maximum number of concurrent agent executions"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get the application settings instance.

    This function can be used as a FastAPI dependency for testing.

    Returns:
        Settings: The global settings instance
    """
    return settings


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.

    Useful for testing or when environment variables change at runtime.

    Returns:
        Settings: A new settings instance
    """
    global settings
    settings = Settings()
    return settings
