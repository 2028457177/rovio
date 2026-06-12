import hashlib
import os
from datetime import datetime
from typing import Optional
from AIRAGAgent.database.connection import get_db


def save_conversation_full(user_id: int, conversation_id: str, title: str, messages: list) -> None:
    """保存会话：更新标题。消息已由 save_message() 在流式对话时逐条持久化，此处不再重复写入。"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO conversations (id, user_id, title)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE title = VALUES(title), updated_at = CURRENT_TIMESTAMP
            """,
            (conversation_id, user_id, title)
        )
        conn.commit()


def get_conversations(user_id: int) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at
            FROM conversations c
            WHERE c.user_id = %s AND c.is_deleted = 0
            ORDER BY c.updated_at DESC
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            conv = {
                "id": row["id"],
                "title": row["title"],
                "time": row["updated_at"].strftime("%H:%M") if row["updated_at"] else "",
                "messages": [],
            }
            cursor.execute(
                "SELECT role, content, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
                (row["id"],)
            )
            messages = cursor.fetchall()
            for msg in messages:
                conv["messages"].append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "time": msg["created_at"].strftime("%H:%M") if msg["created_at"] else "",
                })
            result.append(conv)
        return result


def delete_user_admin(target_user_id: int) -> bool:
    """管理员注销用户（级联删除其会话和消息）"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 不允许删除管理员
        cursor.execute("SELECT role FROM users WHERE id = %s", (target_user_id,))
        row = cursor.fetchone()
        if not row or row["role"] == "admin":
            return False
        # 级联：先删消息，再删会话，最后删用户
        cursor.execute(
            "DELETE m FROM messages m JOIN conversations c ON m.conversation_id = c.id WHERE c.user_id = %s",
            (target_user_id,)
        )
        cursor.execute("DELETE FROM conversations WHERE user_id = %s", (target_user_id,))
        cursor.execute("DELETE FROM users WHERE id = %s", (target_user_id,))
        conn.commit()
        return cursor.rowcount > 0


def reset_user_password(target_user_id: int, new_password: str) -> bool:
    """管理员重置用户密码"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, role FROM users WHERE id = %s", (target_user_id,))
        row = cursor.fetchone()
        if not row or row["role"] == "admin":
            return False
        password_hash = _hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (password_hash, target_user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_conversation(user_id: int, conversation_id: str) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title FROM conversations WHERE id = %s AND user_id = %s AND is_deleted = 0",
            (conversation_id, user_id)
        )
        row = cursor.fetchone()
        if not row:
            return None
        conv = {"id": row["id"], "title": row["title"], "messages": []}
        cursor.execute(
            "SELECT role, content, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
            (conversation_id,)
        )
        for msg in cursor.fetchall():
            conv["messages"].append({
                "role": msg["role"],
                "content": msg["content"],
                "time": msg["created_at"].strftime("%H:%M") if msg["created_at"] else "",
            })
        return conv


def delete_conversation(user_id: int, conversation_id: str) -> None:
    """软删除：标记 is_deleted=1，管理员仍可查看"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET is_deleted = 1 WHERE id = %s AND user_id = %s",
            (conversation_id, user_id)
        )


def _generate_title(content: str) -> str:
    """从消息内容生成标题：取前30个字符，超出则加省略号"""
    return content[:30] + "..." if len(content) > 30 else content


def save_message(user_id: int, conversation_id: str, role: str, content: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM conversations WHERE id = %s", (conversation_id,))
        row = cursor.fetchone()

        if row is None:
            # 新会话，从首条消息自动生成标题
            title = _generate_title(content)
            cursor.execute(
                "INSERT INTO conversations (id, user_id, title) VALUES (%s, %s, %s)",
                (conversation_id, user_id, title)
            )
        else:
            cursor.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP, is_deleted = 0 WHERE id = %s",
                (conversation_id,)
            )

        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
            (conversation_id, role, content)
        )
        conn.commit()


def get_messages_by_conversation(user_id: int, conversation_id: str) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        # 验证会话属于该用户
        cursor.execute(
            "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id)
        )
        if not cursor.fetchone():
            return []
        cursor.execute(
            "SELECT role, content FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
            (conversation_id,)
        )
        return [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]


def get_session_messages(user_id: int, session_id: str) -> list:
    return get_messages_by_conversation(user_id, session_id)


def clear_session(user_id: int, session_id: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM messages WHERE conversation_id = %s",
            (session_id,)
        )


# ==================== 用户认证相关 ====================

def _hash_password(password: str) -> str:
    """SHA-256 加盐哈希密码"""
    salt = os.urandom(32)
    hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + ":" + hash_obj.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    """验证密码是否匹配"""
    salt_hex, hash_hex = stored_hash.split(":")
    salt = bytes.fromhex(salt_hex)
    hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return hash_obj.hex() == hash_hex


def create_user(username: str, password: str, display_name: str = "") -> Optional[dict]:
    """创建用户，返回用户信息字典；用户名已存在时返回 None"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return None

        password_hash = _hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, display_name) VALUES (%s, %s, %s)",
            (username, password_hash, display_name or username)
        )
        conn.commit()
        return {
            "id": cursor.lastrowid,
            "username": username,
            "display_name": display_name or username,
        }


def get_user_by_username(username: str) -> Optional[dict]:
    """根据用户名获取用户信息"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash, display_name, role, created_at FROM users WHERE username = %s",
            (username,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "password_hash": row["password_hash"],
            "display_name": row["display_name"],
            "role": row["role"],
            "created_at": row["created_at"],
        }


def get_user_by_id(user_id: int) -> Optional[dict]:
    """根据用户 ID 获取用户信息（不含密码哈希）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, display_name, role, created_at FROM users WHERE id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "role": row["role"],
            "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S") if row["created_at"] else "",
        }


# ==================== 管理员相关 ====================

def get_all_users() -> list:
    """获取所有用户列表（管理员功能）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, display_name, role, created_at FROM users WHERE role != 'admin' ORDER BY id ASC"
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "role": row["role"],
                "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S") if row["created_at"] else "",
            }
            for row in rows
        ]


def get_user_conversations_admin(target_user_id: int) -> list:
    """管理员查看任意用户的会话列表（仅显示最近30天）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at
            FROM conversations c
            WHERE c.user_id = %s AND c.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            ORDER BY c.updated_at DESC
            """,
            (target_user_id,)
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            conv = {
                "id": row["id"],
                "title": row["title"],
                "time": row["updated_at"].strftime("%H:%M") if row["updated_at"] else "",
                "messages": [],
            }
            cursor.execute(
                "SELECT role, content, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
                (row["id"],)
            )
            messages = cursor.fetchall()
            for msg in messages:
                conv["messages"].append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "time": msg["created_at"].strftime("%H:%M") if msg["created_at"] else "",
                })
            result.append(conv)
        return result


def cleanup_old_conversations(days: int = 30) -> int:
    """物理删除超过指定天数的会话及其消息，返回删除的会话数"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE m FROM messages m JOIN conversations c ON m.conversation_id = c.id WHERE c.created_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
            (days,)
        )
        cursor.execute(
            "DELETE FROM conversations WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)",
            (days,)
        )
        deleted = cursor.rowcount
        conn.commit()
        return deleted
