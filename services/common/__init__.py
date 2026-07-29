"""微服务共享库。

提供跨服务通用能力：
- config: 统一配置 + 服务注册表
- jwt_auth: JWT 编解码 + FastAPI 鉴权依赖
- http_client: 跨服务 HTTP 调用（带服务发现）
- redis_client: Redis 连接
- events: Redis pub/sub 事件总线
- logger: 日志
- base_app: FastAPI 应用工厂
- paths: 项目路径
"""
from .config import SERVICE_REGISTRY, get_service_url, get_db_name, get_mysql_config
from .jwt_auth import create_access_token, get_current_user, get_admin_user, get_client_ip
from .http_client import ServiceClient, call_service
from .redis_client import get_redis_client, is_redis_available, close_redis
from .events import publish_event, subscribe_events
from .db import get_db, get_connection, ensure_database_exists
from .logger import logger
from .base_app import create_app

__all__ = [
    "SERVICE_REGISTRY",
    "get_service_url",
    "get_db_name",
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
    "publish_event",
    "subscribe_events",
    "get_db",
    "get_connection",
    "ensure_database_exists",
    "logger",
    "create_app",
]
