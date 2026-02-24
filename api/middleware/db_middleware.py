"""
数据库会话中间件 - 为每个请求创建数据库会话

在请求开始时创建数据库会话，注入到 request.state.db，
在请求结束时自动关闭会话。
"""

from typing import Callable
from fastapi import Request
from sqlalchemy.orm import Session as SQLSession

from services.database import SessionLocal


async def db_middleware(
    request: Request,
    call_next: Callable
):
    """
    数据库会话中间件

    为每个请求创建一个独立的数据库会话，
    在请求结束时自动关闭。

    使用:
        app.middleware("http")(db_middleware)

    在路由中访问:
        @router.get("/api/sessions")
        async def list_sessions(request: Request):
            db: SQLSession = request.state.db
            sessions = db.query(Session).all()
            return {"sessions": sessions}

    或者使用 Depends:
        from api.middleware.db_middleware import get_db

        @router.get("/api/sessions")
        async def list_sessions(db: SQLSession = Depends(get_db)):
            sessions = db.query(Session).all()
            return {"sessions": sessions}
    """
    # 创建数据库会话
    db: SQLSession = SessionLocal()

    try:
        # 注入到 request.state
        request.state.db = db

        # 处理请求
        response = await call_next(request)

        return response

    finally:
        # 关闭会话
        db.close()


# ============================================================================
# 依赖注入函数（供路由使用）
# ============================================================================

async def get_db(request: Request) -> SQLSession:
    """
    获取数据库会话（依赖注入）

    这是一个 FastAPI 依赖注入函数，用于在路由中获取数据库会话。

    Args:
        request: FastAPI 请求对象

    Returns:
        数据库会话

    示例:
        @router.get("/api/sessions")
        async def list_sessions(db: SQLSession = Depends(get_db)):
            sessions = db.query(Session).all()
            return {"sessions": sessions}
    """
    return request.state.db
