"""chat_service 独立配置（纯环境变量驱动，无外部 YAML 依赖）。

每个服务目录自包含 core/ 包，可脱离项目根目录独立启动。
配置来源优先级：环境变量 > 服务级默认值。
"""
import os

# ===== 服务自身 =====
# 兼容旧变量名 CHAT_PORT / CHAT_DB（部署 .env 使用），优先新变量名 PORT / DB_NAME
PORT = int(os.getenv("PORT") or os.getenv("CHAT_PORT") or "8003")
DB_NAME = os.getenv("DB_NAME") or os.getenv("CHAT_DB") or "lc_chat"

# ===== MySQL =====
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4")

# ===== Redis =====
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))

# ===== JWT =====
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "lc-course-secret-key-2025")
JWT_ALGORITHM = "HS256"
JWT_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_TOKEN_EXPIRE_HOURS", "72"))

# ===== 管理员 IP 白名单 =====
ADMIN_ALLOWED_IPS = (
    [ip.strip() for ip in os.getenv("ADMIN_ALLOWED_IPS", "").split(",") if ip.strip()]
    if os.getenv("ADMIN_ALLOWED_IPS") else []
)

# ===== 跨服务调用 =====
# chat_service 自身不通过 ServiceClient 调用其他服务；
# 其依赖的 AIRAGAgent 引擎读取 USER_SERVICE_URL 环境变量直连 user_service。


def get_mysql_config() -> dict:
    """本服务独立的 MySQL 连接配置（指向 DB_NAME 库）"""
    return {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "database": DB_NAME,
        "charset": MYSQL_CHARSET,
    }
