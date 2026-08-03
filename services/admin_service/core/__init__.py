"""admin_service 自包含核心库。

本服务不再依赖 services/common，公共能力以副本形式内置于 core/，
可脱离项目根目录独立部署。
"""
from .config import PORT, DB_NAME, get_service_url, get_mysql_config
from .jwt_auth import create_access_token, get_current_user, get_admin_user, get_client_ip
from .http_client import ServiceClient, call_service
from .redis_client import get_redis_client, is_redis_available, close_redis
from .db import get_db, get_connection, ensure_database_exists
from .events import publish_event, subscribe_events
from .logger import logger
from .base_app import create_app

__all__ = [
    "PORT",
    "DB_NAME",
    "get_service_url",
    "get_mysql_config",
    "create_access_token",
    "get_current_user",
    "get_admin_user",
    "get_client_ip",
    "ServiceClient",
    "call_service",
    "get_redis_client",
    "is_redis_available",
    "close_redis",
    "get_db",
    "get_connection",
    "ensure_database_exists",
    "publish_event",
    "subscribe_events",
    "logger",
    "create_app",
]
