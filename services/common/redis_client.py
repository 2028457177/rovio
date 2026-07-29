"""Redis 客户端（复用现有配置）。

所有微服务共享同一个 Redis 实例，用于：
- 跨服务 pub/sub 事件总线（chat → admin 的埋点事件）
- 限流计数
- 会话缓存
- 任务队列
"""
import redis
from redis import ConnectionPool

from .config import redis_conf
from .logger import logger

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            host=redis_conf.get("host", "localhost"),
            port=int(redis_conf.get("port", 6379)),
            password=redis_conf.get("password", "") or None,
            db=int(redis_conf.get("db", 0)),
            decode_responses=redis_conf.get("decode_responses", True),
            socket_timeout=float(redis_conf.get("socket_timeout", 5)),
            socket_connect_timeout=float(redis_conf.get("socket_connect_timeout", 5)),
            max_connections=int(redis_conf.get("max_connections", 20)),
        )
    return _pool


def get_redis_client() -> redis.Redis:
    return redis.Redis(connection_pool=_get_pool())


def is_redis_available() -> bool:
    try:
        get_redis_client().ping()
        return True
    except Exception:
        logger.warning("Redis 服务不可用，将跳过 Redis 相关功能")
        return False


def close_redis():
    global _pool
    if _pool is not None:
        _pool.disconnect()
        _pool = None
        logger.info("Redis 连接池已关闭")
