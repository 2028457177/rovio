"""kb_service 测试固件。

kb_service 复用 AIRAGAgent.kb 业务逻辑（DB 已重定向到 lc_kb_test）。
ChromaDB / 嵌入 API 在测试中全部 mock，避免依赖外部向量服务。
"""
import os
import sys
import importlib.util

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ====== 1. 环境变量（必须在 import main 之前设置）======
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_PORT", "3306")
os.environ.setdefault("MYSQL_USER", "root")
os.environ["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD", "")
os.environ["DB_NAME"] = "lc_kb_test"          # 独立测试库，不污染 lc_kb
os.environ["KB_DB"] = "lc_kb_test"
os.environ.setdefault("JWT_SECRET_KEY", "lc-course-secret-key-2025")
os.environ.setdefault("JWT_TOKEN_EXPIRE_HOURS", "72")
os.environ.pop("ADMIN_ALLOWED_IPS", None)     # 测试不启用管理员 IP 白名单
os.environ.setdefault("PROJECT_ROOT", PROJECT_ROOT)

# ====== 2. 加载 main（唯一模块名，清理陈旧 core 缓存）======
def _load_service_main(service_name: str, module_alias: str):
    service_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "services", service_name))
    if service_dir not in sys.path:
        sys.path.insert(0, service_dir)
    for mod_name in list(sys.modules):
        if mod_name in ("core", "models") or mod_name.startswith("core.") or mod_name.startswith("models."):
            del sys.modules[mod_name]
    main_path = os.path.join(service_dir, "main.py")
    spec = importlib.util.spec_from_file_location(module_alias, main_path)
    module = importlib.util.module_from_spec(spec)
    # 注册到 sys.modules，使 pydantic v2 能解析模块内模型的 forward refs（KbUpdateRequest 等）
    sys.modules[module_alias] = module
    spec.loader.exec_module(module)
    return module


kb_main = _load_service_main("kb_service", "kb_service_main")
app = kb_main.app
kb_models = kb_main.kb_models        # AIRAGAgent.kb.models
kb_service_mod = kb_main.kb_service  # AIRAGAgent.kb.service

# kb main 未导入 create_access_token，从 kb 的 core.jwt_auth 取
import core.jwt_auth as _kb_jwt  # noqa: E402  (kb 的 core 已缓存)
create_access_token = _kb_jwt.create_access_token

import pymysql  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


# ====== 3. 测试库建表 SQL（与 AIRAGAgent/database/connection.py init_db 一致）======
SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS knowledge_bases (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        scope VARCHAR(20) NOT NULL DEFAULT 'global',
        owner_user_id BIGINT NULL,
        biz_line VARCHAR(100) NOT NULL DEFAULT '',
        description VARCHAR(500) NOT NULL DEFAULT '',
        is_enabled TINYINT NOT NULL DEFAULT 1,
        is_default TINYINT NOT NULL DEFAULT 0,
        created_by BIGINT NULL,
        created_by_name VARCHAR(100) NOT NULL DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_kb_scope_owner (scope, owner_user_id),
        INDEX idx_kb_enabled (is_enabled)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS kb_documents (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        kb_id BIGINT NOT NULL,
        filename VARCHAR(255) NOT NULL,
        stored_path VARCHAR(500) NOT NULL DEFAULT '',
        file_ext VARCHAR(20) NOT NULL DEFAULT '',
        file_size BIGINT NOT NULL DEFAULT 0,
        file_md5 VARCHAR(64) NOT NULL DEFAULT '',
        version INT NOT NULL DEFAULT 1,
        source VARCHAR(50) NOT NULL DEFAULT 'upload',
        uploader_id BIGINT NULL,
        uploader_name VARCHAR(100) NOT NULL DEFAULT '',
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        chunk_count INT NOT NULL DEFAULT 0,
        error_msg VARCHAR(1000) NOT NULL DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_doc_kb (kb_id),
        INDEX idx_doc_status (status),
        INDEX idx_doc_md5 (kb_id, file_md5)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

TABLES = ["kb_documents", "knowledge_bases"]


def _admin_connect():
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
    conn = _admin_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE DATABASE IF NOT EXISTS lc_kb_test "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute("USE lc_kb_test")
            for sql in SCHEMA_SQL:
                cur.execute(sql)
    finally:
        conn.close()
    yield


@pytest.fixture(autouse=True)
def db_clean(db_setup):
    conn = _admin_connect()
    try:
        with conn.cursor() as cur:
            cur.execute("USE lc_kb_test")
            for tbl in TABLES:
                cur.execute(f"TRUNCATE TABLE {tbl}")
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def mock_chroma(monkeypatch):
    """屏蔽所有 ChromaDB / 嵌入 API 调用，使 CRUD/权限测试不依赖向量服务。
    kb_service 中所有 kb_service.* 调用均为 fire-and-forget（无 await），故用同步 no-op。
    """
    monkeypatch.setattr(kb_service_mod, "seed_default_kb", lambda: None)
    monkeypatch.setattr(kb_service_mod, "_get_vector_store", lambda *a, **kw: None)
    monkeypatch.setattr(kb_service_mod, "index_document_async", lambda *a, **kw: None)
    monkeypatch.setattr(kb_service_mod, "delete_kb_vectors", lambda *a, **kw: None)
    monkeypatch.setattr(kb_service_mod, "delete_document_vectors", lambda *a, **kw: None)
    monkeypatch.setattr(kb_service_mod, "rebuild_kb_async", lambda *a, **kw: None)
    monkeypatch.setattr(kb_service_mod, "_invalidate_cache", lambda *a, **kw: None)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_token():
    """普通用户 JWT（user_id=1001）。"""
    return create_access_token(1001, "normal_user", "user")


@pytest.fixture
def admin_token():
    """管理员 JWT（user_id=1）。"""
    return create_access_token(1, "admin", "admin")


@pytest.fixture
def user_headers(user_token):
    return _hdr(user_token)


@pytest.fixture
def admin_headers(admin_token):
    return _hdr(admin_token)


@pytest.fixture
def make_user_token():
    """工厂：为指定 user_id 签发用户 token（测试多用户隔离）。"""
    def _make(user_id, username=None):
        return create_access_token(user_id, username or f"user{user_id}", "user")
    return _make
