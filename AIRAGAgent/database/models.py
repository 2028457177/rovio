from datetime import datetime
from typing import Optional
from AIRAGAgent.database.connection import get_db


def save_conversation_full(conversation_id: str, title: str, messages: list) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO conversations (id, title)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE title = VALUES(title), updated_at = CURRENT_TIMESTAMP
            """,
            (conversation_id, title)
        )
        cursor.execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
        for msg in messages:
            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                (conversation_id, msg.get("role", ""), msg.get("content", ""))
            )
        conn.commit()


def get_conversations() -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at
            FROM conversations c
            ORDER BY c.updated_at DESC
            """
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


def get_conversation(conversation_id: str) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM conversations WHERE id = %s", (conversation_id,))
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


def delete_conversation(conversation_id: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))


def save_message(conversation_id: str, role: str, content: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO conversations (id, title)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
            """,
            (conversation_id, "")
        )
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
            (conversation_id, role, content)
        )
        conn.commit()


def get_messages_by_conversation(conversation_id: str) -> list:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
            (conversation_id,)
        )
        return [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]


def get_session_messages(session_id: str) -> list:
    return get_messages_by_conversation(session_id)


def clear_session(session_id: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE conversation_id = %s", (session_id,))
