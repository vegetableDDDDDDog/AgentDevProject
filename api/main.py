"""
FastAPI 应用 - Agent PaaS 平台

Agent 平台 API 服务的主入口点。
为 Agent 交互提供 RESTful 端点和 SSE 流式传输。
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text

from api.config import settings
from api.schemas import HealthResponse, ErrorResponse
# 从 database.py 导入数据库初始化函数和引擎
from services.database import init_db, engine, SessionLocal
from services.session_service import SessionService
from services.agent_factory import list_agents

# 导入 agents 以触发注册
import agents.simple_agents  # 注册: echo_agent, mock_chat_agent, counter_agent, error_agent
import agents.llm_agents  # 注册: llm_chat, llm_single_turn

# 导入认证路由和异常处理器
from api.routers import auth, metrics, tools


# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 追踪服务器启动时间
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用程序生命周期管理器。

    处理 FastAPI 应用程序的启动和关闭事件。
    """
    # 启动
    logger.info("正在启动 Agent PaaS 平台...")
    logger.info(f"版本: {settings.app_version}")
    logger.info(f"调试模式: {settings.debug}")

    # 初始化数据库（调用 services/database.py:init_db()）
    try:
        init_db()  # 创建所有数据库表
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

    # 记录已注册的 agents
    agents = list_agents()
    logger.info(f"已注册的 agents: {list(agents.keys())}")

    yield

    # 关闭
    logger.info("正在关闭 Agent PaaS 平台...")
    engine.dispose()
    logger.info("数据库连接已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="企业级 Agent 平台即服务",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)


# ============================================================================
# 中间件
# ============================================================================

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 监控中间件
from api.middleware.metrics_middleware import metrics_middleware
app.middleware("http")(metrics_middleware)

# ============================================================================
# 自定义中间件
# ============================================================================

# 数据库会话中间件（必须在其他中间件之前）
from api.middleware.db_middleware import db_middleware
app.middleware("http")(db_middleware)

# 租户隔离中间件（依赖数据库中间件）
from api.middleware.tenant_middleware import tenant_middleware
app.middleware("http")(tenant_middleware)


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> JSONResponse:
    """
    记录所有传入请求并添加处理时间头。
    """
    start_time_req = time.time()

    # 记录请求
    logger.info(f"{request.method} {request.url.path}")

    # 处理请求
    response = await call_next(request)

    # 添加处理时间头
    process_time = time.time() - start_time_req
    response.headers["X-Process-Time"] = str(process_time)

    # 记录响应
    logger.info(
        f"{request.method} {request.url.path} - "
        f"状态: {response.status_code} - "
        f"时间: {process_time:.3f}s"
    )

    return response


# ============================================================================
# 异常处理器
# ============================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """处理 HTTP 异常。"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTP_ERROR",
            message=exc.detail,
            path=request.url.path
        ).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """处理请求验证错误。"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="VALIDATION_ERROR",
            message="请求验证失败",
            details={"errors": exc.errors()},
            path=request.url.path
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未处理的异常。"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="INTERNAL_SERVER_ERROR",
            message=str(exc) if settings.debug else "发生意外错误",
            path=request.url.path
        ).model_dump()
    )


# ============================================================================
# 注册自定义异常处理器
# ============================================================================

from api.middleware import error_handlers
error_handlers.register_exception_handlers(app)


# ============================================================================
# 健康检查端点
# ============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="健康检查端点"
)
async def health_check() -> HealthResponse:
    """
    检查 API 服务的健康状态。

    Returns:
        HealthResponse: 包括数据库连接性的状态信息
    """
    # 检查数据库连接
    db_connected = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_connected = True
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")

    # 获取已注册 agents 数量
    agents = list_agents()
    agent_count = len(agents)

    return HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        version=settings.app_version,
        uptime_seconds=time.time() - start_time,
        database_connected=db_connected,
        agents_registered=agent_count
    )


# ============================================================================
# 根端点
# ============================================================================

@app.get("/", tags=["Root"])
async def root() -> dict:
    """
    带有 API 信息的根端点。
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.debug else "已禁用（调试模式关闭）",
        "health": "/health",
        "api_prefix": settings.api_prefix
    }


# ============================================================================
# 路由注册
# ============================================================================

from api.routers import chat, agents, sessions

app.include_router(chat.router, prefix=settings.api_prefix, tags=["Chat"])
app.include_router(agents.router, prefix=settings.api_prefix, tags=["Agents"])
app.include_router(sessions.router, prefix=settings.api_prefix, tags=["Sessions"])
app.include_router(auth.router, prefix=settings.api_prefix, tags=["Auth"])
app.include_router(metrics.router, prefix=settings.api_prefix, tags=["Metrics"])
app.include_router(tools.router, prefix=settings.api_prefix, tags=["Tools"])


# ============================================================================
# 开发服务器
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
