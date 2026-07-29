"""MySQL 连接辅助（按服务分库）。

每个微服务调用 get_db() 拿到自己独立数据库的连接。
"""
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor

from .config import get_mysql_config
from .logger import logger

# 每个服务的连接配置缓存
_configs = {}


def _get_config(service: str) -> dict:
    if service not in _configs:
        cfg = get_mysql_config(service)
        cfg["cursorclass"] = DictCursor
        cfg["autocommit"] = True
        _configs[service] = cfg
    return _configs[service]


def get_connection(service: str) -> pymysql.connections.Connection:
    """获取指定服务的数据库连接"""
    return pymysql.connect(**_get_config(service))


@contextmanager
def get_db(service: str):
    """上下文管理器：自动关闭连接。

    用法::

        with get_db("auth") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
    """
    conn = get_connection(service)
    try:
        yield conn
    finally:
        conn.close()


def ensure_database_exists(service: str):
    """确保该服务的数据库已创建。

    连接 MySQL 时不指定 database，CREATE DATABASE IF NOT EXISTS。
    """
    cfg = get_mysql_config(service)
    admin_cfg = {k: v for k, v in cfg.items() if k != "database"}
    conn = pymysql.connect(**admin_cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` "
                f"CHARACTER SET {cfg.get('charset', 'utf8mb4')} COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        logger.info(f"[db] 确保数据库 {cfg['database']} 存在")
    finally:
        conn.close()
