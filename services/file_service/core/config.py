"""file_service 独立配置（纯环境变量驱动，无外部 YAML 依赖）。

每个服务目录自包含 core/ 包，可脱离项目根目录独立启动。
file_service 不持有独立数据库（文件系统即存储）。
"""
import os

# ===== 服务自身 =====
# 兼容旧变量名 FILE_PORT（部署 .env 使用），优先新变量名 PORT
PORT = int(os.getenv("PORT") or os.getenv("FILE_PORT") or "8006")

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
