"""file_service 自包含核心库。

本服务不再依赖 services/common，公共能力以副本形式内置于 core/，
可脱离项目根目录独立部署。
"""
from .config import PORT
from .jwt_auth import get_current_user, get_admin_user, get_client_ip
from .redis_client import get_redis_client, is_redis_available, close_redis
from .logger import logger
from .base_app import create_app

__all__ = [
    "PORT",
    "get_current_user",
    "get_admin_user",
    "get_client_ip",
    "get_redis_client",
    "is_redis_available",
    "close_redis",
    "logger",
    "create_app",
]
