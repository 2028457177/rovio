"""admin_service 数据访问层。

操作独立数据库 lc_admin，仅含三张统计副本表（由 Redis 事件同步）：
- rate_limit_events
- api_call_logs
- tool_call_logs

注意：lc_admin 不含 users / messages / conversations 表，故对原
AIRAGAgent/database/models.py 中的看板查询做如下适配：
- get_dashboard_overview：DAU/WAU/MAU 直接查 api_call_logs；
  新增用户 / 总用户数 / 次日留存依赖 users 表，由 main 层从 auth_service
  拉取用户列表后通过 users 参数传入计算。
- get_dashboard_top_users：去掉与 users 的 JOIN，只返回 user_id，
  用户名由 main 层调 auth_service 补全。
- get_dashboard_top_questions：依赖 messages / conversations（属 chat_service），
  lc_admin 无此数据，返回空列表，如需启用应由 chat_service 提供内部接口。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from core.db import get_db


# ==================== 数据统计：埋点写入 ====================

def log_api_call(user_id: int, session_id: str, ip: str, endpoint: str,
                 duration_ms: int, prompt_tokens: int = 0, completion_tokens: int = 0,
                 is_success: bool = True, error_msg: str = "") -> None:
    """记录一次 API 调用（用于统计调用量 / Token / 响应时长 / 错误率）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO api_call_logs
                    (user_id, session_id, ip, endpoint, duration_ms,
                     prompt_tokens, completion_tokens, total_tokens, is_success, error_msg)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, session_id or "", ip or "", endpoint or "chat", int(duration_ms or 0),
                 int(prompt_tokens or 0), int(completion_tokens or 0),
                 int(prompt_tokens or 0) + int(completion_tokens or 0),
                 1 if is_success else 0, (error_msg or "")[:1000])
            )
            conn.commit()
    except Exception:
        # 埋点失败不影响主流程
        pass


def log_tool_call(user_id: int, session_id: str, tool_name: str,
                  duration_ms: int, is_success: bool = True, error_msg: str = "") -> None:
    """记录一次工具调用（用于工具分布统计）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tool_call_logs
                    (user_id, session_id, tool_name, duration_ms, is_success, error_msg)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, session_id or "", tool_name or "", int(duration_ms or 0),
                 1 if is_success else 0, (error_msg or "")[:1000])
            )
            conn.commit()
    except Exception:
        pass


def log_rate_limit_event(user_id: int, ip: str, limit_type: str, identifier: str) -> None:
    """记录一次限流触发事件"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO rate_limit_events (user_id, ip, limit_type, identifier)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id or 0, ip or "", limit_type or "chat", (identifier or "")[:200])
            )
            conn.commit()
    except Exception:
        pass


# ==================== 数据统计：看板查询 ====================

def _parse_dt(value) -> datetime | None:
    """将字符串/datetime 解析为 datetime，失败返回 None"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return None


def get_dashboard_overview(users: list | None = None) -> dict:
    """看板概览：DAU / WAU / MAU / 新增用户 / 次日留存。

    lc_admin 无 users 表，故用户相关统计（新增 / 总数 / 留存）由 main 层
    从 auth_service 拉取用户列表后通过 users 参数传入。
    users: list[{id, username, role, created_at}]，为 None 时这些字段返回 0。
    """
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # DAU：今日活跃用户（去重 user_id，排除匿名 user_id<=0）
        cursor.execute(
            "SELECT COUNT(DISTINCT user_id) AS cnt FROM api_call_logs "
            "WHERE DATE(created_at) = %s AND user_id > 0",
            (today,)
        )
        dau = cursor.fetchone()["cnt"]

        # WAU：近 7 天活跃
        cursor.execute(
            "SELECT COUNT(DISTINCT user_id) AS cnt FROM api_call_logs "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) AND user_id > 0"
        )
        wau = cursor.fetchone()["cnt"]

        # MAU：近 30 天活跃
        cursor.execute(
            "SELECT COUNT(DISTINCT user_id) AS cnt FROM api_call_logs "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) AND user_id > 0"
        )
        mau = cursor.fetchone()["cnt"]

        new_users_today = 0
        new_users_week = 0
        total_users = 0
        retention_rate = 0.0

        if users:
            non_admin = [u for u in users if u.get("role") != "admin"]
            total_users = len(non_admin)
            week_cutoff = now - timedelta(days=7)
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            yesterday_new_ids: list = []
            for u in non_admin:
                dt = _parse_dt(u.get("created_at"))
                if not dt:
                    continue
                date_str = dt.strftime("%Y-%m-%d")
                if date_str == today:
                    new_users_today += 1
                if dt >= week_cutoff:
                    new_users_week += 1
                if date_str == yesterday and u.get("id"):
                    yesterday_new_ids.append(u.get("id"))

            # 次日留存：昨日新增用户中，今日有调用的用户数占比
            if yesterday_new_ids:
                placeholders = ",".join(["%s"] * len(yesterday_new_ids))
                cursor.execute(
                    f"SELECT COUNT(DISTINCT user_id) AS cnt FROM api_call_logs "
                    f"WHERE DATE(created_at) = %s AND user_id IN ({placeholders})",
                    [today] + yesterday_new_ids
                )
                retained = cursor.fetchone()["cnt"]
                retention_rate = round(retained / len(yesterday_new_ids) * 100, 2)

        return {
            "dau": dau,
            "wau": wau,
            "mau": mau,
            "new_users_today": new_users_today,
            "new_users_week": new_users_week,
            "total_users": total_users,
            "retention_rate": retention_rate,
        }


def get_dashboard_trends(days: int = 30) -> dict:
    """趋势图：每日调用量 / Token 消耗 / 平均响应时长"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                DATE(created_at) AS date,
                COUNT(*) AS call_count,
                SUM(prompt_tokens) AS prompt_tokens,
                SUM(completion_tokens) AS completion_tokens,
                SUM(total_tokens) AS total_tokens,
                AVG(duration_ms) AS avg_duration_ms
            FROM api_call_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at) ASC
            """,
            (int(days),)
        )
        rows = cursor.fetchall()
        dates = []
        call_counts = []
        prompt_tokens = []
        completion_tokens = []
        total_tokens = []
        avg_durations = []
        for row in rows:
            d = row["date"]
            dates.append(d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d))
            call_counts.append(row["call_count"])
            prompt_tokens.append(int(row["prompt_tokens"] or 0))
            completion_tokens.append(int(row["completion_tokens"] or 0))
            total_tokens.append(int(row["total_tokens"] or 0))
            avg_durations.append(round(float(row["avg_duration_ms"] or 0), 2))
        return {
            "dates": dates,
            "call_counts": call_counts,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "avg_durations": avg_durations,
        }


def get_dashboard_tool_distribution(days: int = 30) -> list:
    """工具调用分布：哪个工具最常用"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT tool_name, COUNT(*) AS cnt, SUM(is_success) AS success_cnt
            FROM tool_call_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY tool_name
            ORDER BY cnt DESC
            """,
            (int(days),)
        )
        return [
            {
                "tool_name": row["tool_name"],
                "count": row["cnt"],
                "success_count": int(row["success_cnt"] or 0),
                "success_rate": round(int(row["success_cnt"] or 0) / row["cnt"] * 100, 2) if row["cnt"] else 0,
            }
            for row in cursor.fetchall()
        ]


def get_dashboard_error_stats(days: int = 30) -> dict:
    """错误率 + 限流触发次数"""
    with get_db() as conn:
        cursor = conn.cursor()
        # API 错误率
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_success = 0 THEN 1 ELSE 0 END) AS errors
            FROM api_call_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """,
            (int(days),)
        )
        row = cursor.fetchone()
        total_calls = row["total"] or 0
        error_calls = row["errors"] or 0
        error_rate = round(error_calls / total_calls * 100, 2) if total_calls else 0.0

        # 工具调用错误率
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_success = 0 THEN 1 ELSE 0 END) AS errors
            FROM tool_call_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """,
            (int(days),)
        )
        trow = cursor.fetchone()
        t_total = trow["total"] or 0
        t_errors = trow["errors"] or 0
        tool_error_rate = round(t_errors / t_total * 100, 2) if t_total else 0.0

        # 限流触发次数
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM rate_limit_events "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)",
            (int(days),)
        )
        rate_limit_count = cursor.fetchone()["cnt"]

        # 按日分组的限流事件
        cursor.execute(
            """
            SELECT DATE(created_at) AS date, COUNT(*) AS cnt
            FROM rate_limit_events
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at) ASC
            """,
            (int(days),)
        )
        rl_trend = [
            {
                "date": (row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])),
                "count": row["cnt"],
            }
            for row in cursor.fetchall()
        ]

        return {
            "total_calls": total_calls,
            "error_calls": error_calls,
            "error_rate": error_rate,
            "tool_total_calls": t_total,
            "tool_error_calls": t_errors,
            "tool_error_rate": tool_error_rate,
            "rate_limit_count": rate_limit_count,
            "rate_limit_trend": rl_trend,
        }


def get_dashboard_top_users(days: int = 30, limit: int = 10) -> list:
    """Top 用户：按调用量排序（只返回 user_id，用户名由 main 层调 auth_service 补全）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                user_id,
                COUNT(*) AS call_count,
                SUM(total_tokens) AS total_tokens,
                AVG(duration_ms) AS avg_duration_ms
            FROM api_call_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
              AND user_id > 0
            GROUP BY user_id
            ORDER BY call_count DESC
            LIMIT %s
            """,
            (int(days), int(limit))
        )
        return [
            {
                "user_id": row["user_id"],
                "call_count": row["call_count"],
                "total_tokens": int(row["total_tokens"] or 0),
                "avg_duration_ms": round(float(row["avg_duration_ms"] or 0), 2),
            }
            for row in cursor.fetchall()
        ]


def get_dashboard_top_questions(days: int = 30, limit: int = 10) -> list:
    """Top 提问：按用户提问频次排序。

    lc_admin 不含 messages / conversations 表（属 chat_service），无此数据，
    此处返回空列表。如需启用，应由 chat_service 提供内部统计接口，
    或新增事件频道把提问内容同步到 lc_admin。
    """
    return []
