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
                title VARCHAR(255) NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                conversation_id VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_conversation_id (conversation_id),
                CONSTRAINT fk_messages_conversation
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        conn.commit()


def close_pool():
    pass
