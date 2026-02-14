"""
FastAPI Application - Agent PaaS Platform

Main entry point for the Agent Platform API service.
Provides RESTful endpoints and SSE streaming for agent interactions.
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
from services.database import init_db, engine, SessionLocal
from services.session_service import SessionService
from services.agent_factory import list_agents

# Import agents to trigger registration
import agents.simple_agents  # Registers: echo_agent, mock_chat_agent, counter_agent, error_agent


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Track server start time
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting Agent PaaS Platform...")
    logger.info(f"Version: {settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Log registered agents
    agents = list_agents()
    logger.info(f"Registered agents: {list(agents.keys())}")

    yield

    # Shutdown
    logger.info("Shutting down Agent PaaS Platform...")
    engine.dispose()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise-grade Agent Platform as a Service",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)


# ============================================================================
# Middleware
# ============================================================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> JSONResponse:
    """
    Log all incoming requests and add processing time header.
    """
    start_time_req = time.time()

    # Log request
    logger.info(f"{request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Add processing time header
    process_time = time.time() - start_time_req
    response.headers["X-Process-Time"] = str(process_time)

    # Log response
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )

    return response


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
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
    """Handle request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": exc.errors()},
            path=request.url.path
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="INTERNAL_SERVER_ERROR",
            message=str(exc) if settings.debug else "An unexpected error occurred",
            path=request.url.path
        ).model_dump()
    )


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint"
)
async def health_check() -> HealthResponse:
    """
    Check the health status of the API service.

    Returns:
        HealthResponse: Status information including database connectivity
    """
    # Check database connection
    db_connected = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_connected = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Get registered agents count
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
# Root Endpoint
# ============================================================================

@app.get("/", tags=["Root"])
async def root() -> dict:
    """
    Root endpoint with API information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled (debug mode off)",
        "health": "/health",
        "api_prefix": settings.api_prefix
    }


# ============================================================================
# Router Registration
# ============================================================================

from api.routers import chat, agents, sessions

app.include_router(chat.router, prefix=settings.api_prefix, tags=["Chat"])
app.include_router(agents.router, prefix=settings.api_prefix, tags=["Agents"])
app.include_router(sessions.router, prefix=settings.api_prefix, tags=["Sessions"])


# ============================================================================
# Development Server
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
