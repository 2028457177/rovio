"""auth_service 数据访问层（lc_auth 数据库）。"""
import hashlib
import os
import secrets
from datetime import datetime
from typing import Optional

from services.common.db import get_db


# ==================== 密码哈希 ====================

def _hash_password(password: str) -> str:
    """SHA-256 加盐哈希密码（与原实现保持一致）"""
    salt = os.urandom(32)
    hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + ":" + hash_obj.hex()


def _hash_security_answer(answer: str) -> str:
    return _hash_password(answer.strip().lower())


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hash_obj.hex() == hash_hex
    except Exception:
        return False


def verify_security_answer(answer: str, stored_hash: str) -> bool:
    return verify_password(answer.strip().lower(), stored_hash)


# ==================== 用户认证信息 ====================

def create_user(username: str, password: str, role: str = "user") -> Optional[dict]:
    """创建用户认证记录（仅 auth 信息）。返回 {id, username, role} 或 None（用户名已存在）"""
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            return None
        password_hash = _hash_password(password)
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, password_hash, role)
        )
        conn.commit()
        return {"id": cur.lastrowid, "username": username, "role": role}


def get_user_by_username(username: str) -> Optional[dict]:
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password_hash, role, created_at, last_password_changed "
            "FROM users WHERE username = %s",
            (username,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S") if row["created_at"] else "",
            "last_password_changed": row["last_password_changed"].strftime("%Y-%m-%d %H:%M:%S") if row.get("last_password_changed") else "",
        }


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, role, created_at, last_password_changed "
            "FROM users WHERE id = %s",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S") if row["created_at"] else "",
            "last_password_changed": row["last_password_changed"].strftime("%Y-%m-%d %H:%M:%S") if row.get("last_password_changed") else "",
            "has_security_question": has_security_question(user_id),
        }


def get_all_users() -> list:
    """管理员：获取所有用户（仅 auth 信息，profile 由 admin_service 合并 user_service）"""
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, role, created_at, last_password_changed FROM users ORDER BY id ASC"
        )
        rows = cur.fetchall()
        return [{
            "id": r["id"],
            "username": r["username"],
            "role": r["role"],
            "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r["created_at"] else "",
            "last_password_changed": r["last_password_changed"].strftime("%Y-%m-%d %H:%M:%S") if r.get("last_password_changed") else "",
        } for r in rows]


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if not row or not verify_password(old_password, row["password_hash"]):
            return False
        new_hash = _hash_password(new_password)
        cur.execute(
            "UPDATE users SET password_hash = %s, last_password_changed = CURRENT_TIMESTAMP WHERE id = %s",
            (new_hash, user_id)
        )
        conn.commit()
        return cur.rowcount > 0


def reset_user_password(target_user_id: int, new_password: str) -> bool:
    """管理员重置密码（不允许操作 admin 账号）"""
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE id = %s", (target_user_id,))
        row = cur.fetchone()
        if not row or row["role"] == "admin":
            return False
        password_hash = _hash_password(new_password)
        cur.execute(
            "UPDATE users SET password_hash = %s, last_password_changed = CURRENT_TIMESTAMP WHERE id = %s",
            (password_hash, target_user_id)
        )
        conn.commit()
        return cur.rowcount > 0


def delete_user(target_user_id: int) -> bool:
    """删除用户认证记录（不允许删 admin）。登录设备一并清理。"""
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE id = %s", (target_user_id,))
        row = cur.fetchone()
        if not row or row["role"] == "admin":
            return False
        cur.execute("DELETE FROM login_devices WHERE user_id = %s", (target_user_id,))
        cur.execute("DELETE FROM security_questions WHERE user_id = %s", (target_user_id,))
        cur.execute("DELETE FROM users WHERE id = %s", (target_user_id,))
        conn.commit()
        return cur.rowcount > 0


# ==================== 密保问题 ====================

def set_security_question(user_id: int, question: str, answer: str) -> bool:
    if not question.strip() or not answer.strip():
        return False
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO security_questions (user_id, question, answer_hash) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE question = VALUES(question), answer_hash = VALUES(answer_hash)",
            (user_id, question.strip()[:200], _hash_security_answer(answer))
        )
        conn.commit()
        return cur.rowcount > 0


def has_security_question(user_id: int) -> bool:
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM security_questions WHERE user_id = %s", (user_id,))
        return cur.fetchone() is not None


def get_security_question_by_username(username: str) -> Optional[dict]:
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT u.id, u.username, sq.question, sq.answer_hash "
            "FROM users u LEFT JOIN security_questions sq ON sq.user_id = u.id "
            "WHERE u.username = %s AND u.role != 'admin'",
            (username,)
        )
        row = cur.fetchone()
        if not row or not row["question"]:
            return None
        return {"user_id": row["id"], "username": row["username"], "question": row["question"]}


def reset_password_by_security_answer(username: str, answer: str, new_password: str) -> bool:
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT u.id, sq.answer_hash FROM users u "
            "JOIN security_questions sq ON sq.user_id = u.id "
            "WHERE u.username = %s AND u.role != 'admin'",
            (username,)
        )
        row = cur.fetchone()
        if not row or not row["answer_hash"]:
            return False
        if not verify_security_answer(answer, row["answer_hash"]):
            return False
        new_hash = _hash_password(new_password)
        cur.execute(
            "UPDATE users SET password_hash = %s, last_password_changed = CURRENT_TIMESTAMP WHERE id = %s",
            (new_hash, row["id"])
        )
        conn.commit()
        return cur.rowcount > 0


# ==================== 登录设备 ====================

def _parse_os(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if "windows" in ua: return "Windows"
    if "mac" in ua or "darwin" in ua: return "macOS"
    if "android" in ua: return "Android"
    if "iphone" in ua or "ipad" in ua: return "iOS"
    if "linux" in ua: return "Linux"
    return ""


def _parse_browser(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if "edg" in ua: return "Edge"
    if "chrome" in ua: return "Chrome"
    if "firefox" in ua: return "Firefox"
    if "safari" in ua: return "Safari"
    return ""


def create_login_device(user_id: int, device_token: str, user_agent: str, ip: str) -> None:
    with get_db("auth") as conn:
        cur = conn.cursor()
        ua = (user_agent or "").lower()
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            device_type = "mobile"
        elif "ipad" in ua or "tablet" in ua:
            device_type = "tablet"
        else:
            device_type = "desktop"
        os_name = _parse_os(user_agent)
        browser = _parse_browser(user_agent)
        cur.execute(
            "INSERT INTO login_devices (device_token, user_id, device_type, os, browser, ip, user_agent, last_active_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP) "
            "ON DUPLICATE KEY UPDATE ip = VALUES(ip), user_agent = VALUES(user_agent), "
            "last_active_at = CURRENT_TIMESTAMP, is_revoked = 0",
            (device_token, user_id, device_type, os_name, browser, ip, (user_agent or "")[:500])
        )
        conn.commit()


def touch_login_device(device_token: str, ip: Optional[str] = None) -> None:
    with get_db("auth") as conn:
        cur = conn.cursor()
        if ip:
            cur.execute(
                "UPDATE login_devices SET last_active_at = CURRENT_TIMESTAMP, ip = %s "
                "WHERE device_token = %s AND is_revoked = 0",
                (ip, device_token)
            )
        else:
            cur.execute(
                "UPDATE login_devices SET last_active_at = CURRENT_TIMESTAMP "
                "WHERE device_token = %s AND is_revoked = 0",
                (device_token,)
            )
        conn.commit()


def get_login_devices(user_id: int) -> list:
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, device_token, device_type, os, browser, ip, user_agent, "
            "last_active_at, created_at, is_revoked "
            "FROM login_devices WHERE user_id = %s ORDER BY last_active_at DESC",
            (user_id,)
        )
        rows = cur.fetchall()
        return [{
            "id": r["id"],
            "device_token": r["device_token"],
            "device_type": r["device_type"],
            "os": r["os"],
            "browser": r["browser"],
            "ip": r["ip"],
            "last_active_at": r["last_active_at"].strftime("%Y-%m-%d %H:%M:%S") if r["last_active_at"] else "",
            "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r["created_at"] else "",
            "is_revoked": bool(r["is_revoked"]),
        } for r in rows]


def revoke_login_device(user_id: int, device_id: int) -> bool:
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE login_devices SET is_revoked = 1 WHERE id = %s AND user_id = %s",
            (device_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0


def revoke_all_other_devices(user_id: int, current_token: str) -> int:
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE login_devices SET is_revoked = 1 "
            "WHERE user_id = %s AND device_token != %s",
            (user_id, current_token)
        )
        conn.commit()
        return cur.rowcount


# ==================== 内部接口：供其他服务调用 ====================

def get_user_role(user_id: int) -> Optional[str]:
    """供 admin_service / user_service 校验权限"""
    with get_db("auth") as conn:
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return row["role"] if row else None
