import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager

from AIRAGAgent.utils.config_handler import mysql_conf


def _get_db_config():
    return {
        "host": mysql_conf.get("host", "localhost"),
        "port": int(mysql_conf.get("port", 3306)),
        "user": mysql_conf.get("user", "root"),
        "password": mysql_conf.get("password", ""),
        "database": mysql_conf.get("database", "agent_records"),
        "charset": mysql_conf.get("charset", "utf8mb4"),
        "cursorclass": DictCursor,
        "autocommit": True,
    }


def get_connection():
    return pymysql.connect(**_get_db_config())


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR(100) PRIMARY KEY,
                user_id BIGINT NOT NULL DEFAULT 0,
                title VARCHAR(255) NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_conv_user (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        # 迁移：给已有的 conversations 表补充 user_id 列
        _safe_add_column(cursor, "conversations", "user_id", "BIGINT NOT NULL DEFAULT 0")
        _safe_add_index(cursor, "conversations", "idx_conv_user", "user_id")
        # 迁移：软删除标记
        _safe_add_column(cursor, "conversations", "is_deleted", "TINYINT NOT NULL DEFAULT 0")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                conversation_id VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_conv_created (conversation_id, created_at),
                CONSTRAINT fk_messages_conversation
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(100) NOT NULL DEFAULT '',
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_users_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        # 迁移：给已有的 users 表补充 role 列
        _safe_add_column(cursor, "users", "role", "VARCHAR(20) NOT NULL DEFAULT 'user'")
        conn.commit()

        # 创建默认管理员账号 admin/admin123
        _seed_admin_user(cursor, conn)


def _safe_add_column(cursor, table: str, column: str, definition: str):
    """安全添加列：如果列已存在则跳过"""
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except Exception:
        pass  # 列已存在，跳过


def _safe_add_index(cursor, table: str, index_name: str, columns: str):
    """安全添加索引：如果索引已存在则跳过"""
    try:
        cursor.execute(f"CREATE INDEX {index_name} ON {table} ({columns})")
    except Exception:
        pass  # 索引已存在，跳过


def _seed_admin_user(cursor, conn):
    """创建默认管理员账号 admin/admin123（如果不存在）"""
    import hashlib
    import os
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if cursor.fetchone():
        return
    # 使用与 models.py 相同的密码哈希方式
    salt = os.urandom(32)
    hash_obj = hashlib.pbkdf2_hmac("sha256", "admin123".encode("utf-8"), salt, 100000)
    password_hash = salt.hex() + ":" + hash_obj.hex()
    cursor.execute(
        "INSERT INTO users (username, password_hash, display_name, role) VALUES (%s, %s, %s, %s)",
        ("admin", password_hash, "系统管理员", "admin")
    )
    conn.commit()


def close_pool():
    pass
