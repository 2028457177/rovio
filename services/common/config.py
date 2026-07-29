"""微服务统一配置 + 服务注册表。

- 复用 AIRAGAgent/config/*.yml 作为基础配置（MySQL/Redis/RAG/Chroma）
- 通过环境变量覆盖服务端口 / 数据库名 / 跨服务调用地址
- 提供服务注册表，供 http_client 做服务发现
"""
import os
import yaml
from .paths import CONFIG_DIR


def _load_yml(name: str) -> dict:
    path = os.path.join(CONFIG_DIR, name)
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=yaml.FullLoader) or {}


# 复用现有 YAML 配置
mysql_conf = _load_yml("mysql.yml")
redis_conf = _load_yml("redis.yml")
rag_conf = _load_yml("rag.yml")
chroma_conf = _load_yml("chroma.yml")
agent_conf = _load_yml("agent.yml")
prompts_conf = _load_yml("prompts.yml")

# 环境变量覆盖（部署时通过 .env 注入）
MYSQL_HOST = os.getenv("MYSQL_HOST", mysql_conf.get("host", "localhost"))
MYSQL_PORT = int(os.getenv("MYSQL_PORT", mysql_conf.get("port", 3306)))
MYSQL_USER = os.getenv("MYSQL_USER", mysql_conf.get("user", "root"))
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", mysql_conf.get("password", ""))
MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", mysql_conf.get("charset", "utf8mb4"))

# JWT 共享密钥（所有服务必须一致，才能互相验证 token）
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "lc-course-secret-key-2025")
JWT_ALGORITHM = "HS256"
JWT_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_TOKEN_EXPIRE_HOURS", "72"))

# 管理员 IP 白名单
ADMIN_ALLOWED_IPS = (
    [ip.strip() for ip in os.getenv("ADMIN_ALLOWED_IPS", "").split(",") if ip.strip()]
    if os.getenv("ADMIN_ALLOWED_IPS") else []
)


# ==================== 服务注册表 ====================
# 每个服务的端口、内部 base_url、独立数据库名
SERVICE_REGISTRY = {
    "auth":  {"port": int(os.getenv("AUTH_PORT", "8001")),  "db": os.getenv("AUTH_DB", "lc_auth")},
    "user":  {"port": int(os.getenv("USER_PORT", "8002")),  "db": os.getenv("USER_DB", "lc_user")},
    "chat":  {"port": int(os.getenv("CHAT_PORT", "8003")),  "db": os.getenv("CHAT_DB", "lc_chat")},
    "kb":    {"port": int(os.getenv("KB_PORT", "8004")),    "db": os.getenv("KB_DB", "lc_kb")},
    "admin": {"port": int(os.getenv("ADMIN_PORT", "8005")), "db": os.getenv("ADMIN_DB", "lc_admin")},
    "file":  {"port": int(os.getenv("FILE_PORT", "8006")),  "db": None},
}

# 内部调用走 127.0.0.1，避免经过 nginx
_INTERNAL_HOST = os.getenv("INTERNAL_HOST", "127.0.0.1")


def get_service_url(name: str) -> str:
    """返回内部服务的基础 URL，如 http://127.0.0.1:8001"""
    info = SERVICE_REGISTRY.get(name)
    if not info:
        raise ValueError(f"未知服务: {name}")
    return f"http://{_INTERNAL_HOST}:{info['port']}"


def get_db_name(service: str) -> str:
    """返回该服务对应的独立数据库名"""
    info = SERVICE_REGISTRY.get(service)
    if not info or not info.get("db"):
        raise ValueError(f"服务 {service} 无独立数据库")
    return info["db"]


def get_mysql_config(service: str) -> dict:
    """返回指定服务的 MySQL 连接配置（指向独立数据库）"""
    return {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "database": get_db_name(service),
        "charset": MYSQL_CHARSET,
    }
