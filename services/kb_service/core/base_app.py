"""FastAPI 应用工厂（本服务独立副本）。

每个微服务用 create_app() 创建各自的 app，统一处理：
- CORS
- lifespan 生命周期（子类可覆盖 on_startup/on_shutdown）
- /api/health 健康检查
- 日志初始化
"""
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .logger import logger, set_service_name
from .redis_client import close_redis, is_redis_available


def create_app(
    service_name: str,
    *,
    version: str = "1.0.0",
    on_startup: Optional[Callable[[], Awaitable[None]]] = None,
    on_shutdown: Optional[Callable[[], Awaitable[None]]] = None,
) -> FastAPI:
    """创建微服务 FastAPI 应用。

    Args:
        service_name: 服务名（用于日志和健康检查标识）
        version: 服务版本
        on_startup: 启动时异步回调（如初始化数据库、订阅事件）
        on_shutdown: 关闭时异步回调（如关闭连接池）
    """
    set_service_name(service_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(f"[{service_name}] 启动中...")
        if on_startup:
            await on_startup()
        logger.info(f"[{service_name}] 就绪")
        yield
        logger.info(f"[{service_name}] 关闭中...")
        if on_shutdown:
            await on_shutdown()
        close_redis()
        logger.info(f"[{service_name}] 已停止")

    app = FastAPI(
        title=f"lc-course {service_name} service",
        version=version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "service": service_name,
            "redis": "connected" if is_redis_available() else "disconnected",
        }

    return app
