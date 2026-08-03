"""auth_service 测试固件。

环境变量必须在加载 main 之前设置；main.py 采用服务内相对导入（from core import ...），
通过 load_service_main 以唯一模块名加载，避免与 kb_service 的 core 包冲突。
"""
import os
import sys

# ====== 1. 环境变量（必须在 import main 之前设置）======
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_PORT", "3306")
os.environ.setdefault("MYSQL_USER", "root")
os.environ["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD", "")
os.environ["DB_NAME"] = "lc_auth_test"        # 独立测试库，不污染 lc_auth
os.environ["AUTH_DB"] = "lc_auth_test"
os.environ.setdefault("JWT_SECRET_KEY", "lc-course-secret-key-2025")
os.environ.setdefault("JWT_TOKEN_EXPIRE_HOURS", "72")
os.environ.pop("ADMIN_ALLOWED_IPS", None)     # 测试不启用管理员 IP 白名单

# ====== 2. 加载 main（唯一模块名，清理陈旧 core 缓存）======
import importlib.util  # noqa: E402


def _load_service_main(service_name: str, module_alias: str):
    """以唯一模块名加载 services/<service_name>/main.py。"""
    service_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "services", service_name))
    if service_dir not in sys.path:
        sys.path.insert(0, service_dir)
    for mod_name in list(sys.modules):
        if mod_name in ("core", "models") or mod_name.startswith("core.") or mod_name.startswith("models."):
            del sys.modules[mod_name]
    main_path = os.path.join(service_dir, "main.py")
    spec = importlib.util.spec_from_file_location(module_alias, main_path)
    module = importlib.util.module_from_spec(spec)
    # 注册到 sys.modules，使 pydantic v2 能解析模块内模型的 forward refs
    sys.modules[module_alias] = module
    spec.loader.exec_module(module)
    return module


auth_main = _load_service_main("auth_service", "auth_service_main")
app = auth_main.app
create_access_token = auth_main.create_access_token

import pymysql  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


# ====== 3. 测试库建表 SQL（与 services/migrate_to_microservices.py init_auth_schema 一致）======
SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'user',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_password_changed DATETIME NULL,
        INDEX idx_users_username (username)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS security_questions (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL UNIQUE,
        question VARCHAR(200) NOT NULL,
        answer_hash VARCHAR(255) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_sq_user (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS login_devices (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        device_token VARCHAR(100) NOT NULL,
        user_id BIGINT NOT NULL,
        device_type VARCHAR(20) NOT NULL DEFAULT 'desktop',
        os VARCHAR(50) NOT NULL DEFAULT '',
        browser VARCHAR(50) NOT NULL DEFAULT '',
        ip VARCHAR(64) NOT NULL DEFAULT '',
        user_agent VARCHAR(500) NOT NULL DEFAULT '',
        last_active_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        is_revoked TINYINT NOT NULL DEFAULT 0,
        UNIQUE KEY uk_device_token (device_token),
        INDEX idx_login_user (user_id, is_revoked)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

TABLES = ["login_devices", "security_questions", "users"]


def _admin_connect():
    """直连 MySQL（不指定库）用于建库建表。"""
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ["MYSQL_PORT"]),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        charset="utf8mb4",
        autocommit=True,
    )


# ====== 4. 固件 ======

@pytest.fixture(scope="session")
def db_setup():
    """session 级：创建测试库 + 三张表。"""
    conn = _admin_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE DATABASE IF NOT EXISTS lc_auth_test "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute("USE lc_auth_test")
            for sql in SCHEMA_SQL:
                cur.execute(sql)
    finally:
        conn.close()
    yield
    # session 结束不删库，便于复跑；如需清理可手动 DROP DATABASE lc_auth_test


@pytest.fixture(autouse=True)
def db_clean(db_setup):
    """每个测试前清空三张表，保证隔离。"""
    conn = _admin_connect()
    try:
        with conn.cursor() as cur:
            cur.execute("USE lc_auth_test")
            for tbl in TABLES:
                cur.execute(f"TRUNCATE TABLE {tbl}")
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def mock_cross_service(monkeypatch):
    """屏蔽 auth_service → user_service 的跨服务调用（避免污染 lc_user 库）。
    真实 _get_user_profile / _create_user_profile 均为 async def，mock 须保持 awaitable。
    """
    async def _noop_profile(user_id):
        return {}
    async def _noop_create(*args, **kwargs):
        return None
    monkeypatch.setattr(auth_main, "_create_user_profile", _noop_create)
    monkeypatch.setattr(auth_main, "_get_user_profile", _noop_profile)


@pytest.fixture
def client():
    """同步 TestClient（不进入 lifespan，避免触发任何启动副作用）。"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    """返回一个带有效 JWT 的请求头。需配合 register_user 使用。"""
    def _make(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}
    return _make


@pytest.fixture
def register_user(client):
    """注册一个用户，返回 (user_dict, token)。"""
    def _register(username="testuser", password="Test123456", display_name=""):
        resp = client.post("/api/auth/register", json={
            "username": username,
            "password": password,
            "display_name": display_name,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        return data["user"], data["token"]
    return _register


@pytest.fixture
def models():
    """暴露 auth_service 的 models 模块（直接操作 DB 创建测试数据，如 admin 用户）。"""
    return auth_main.models
