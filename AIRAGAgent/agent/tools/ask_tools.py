"""学生互动提问工具（ask_student）：让 SubAgent 在信息不足时向学生发可交互选项面板。

机制（仿 ZCode 的 AskUserQuestion）：
1. SubAgent 调用 ask_student(question, options, ...) 工具；
2. 工具抛出 AskStudentInterrupt 异常，SubAgentRunner 捕获后以 {"type": "ask_user", ...}
   事件结束本次 agent 运行（不继续生成）；
3. Orchestrator 把 ask_user 事件（含 question_id）推给前端，前端渲染选项面板，
   随后阻塞等待学生作答（Redis BLPOP 轮询 + 心跳保活 SSE）；
4. 学生点击选项 → POST /api/chat/answer → 答案写入本模块的答案总线；
5. Orchestrator 拿到答案后，把"学生补充的信息"注入任务描述重跑该步骤，同一轮流内继续执行。

答案总线：Redis 为主（跨进程安全），Redis 不可用时退化为进程内存（单进程部署同样可用）。
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Optional

from langchain_core.tools import tool

from AIRAGAgent.utils.logger_handler import logger

# 学生作答等待时长（秒），超时本轮结束并提示
ASK_ANSWER_TIMEOUT = int(os.getenv("ASK_USER_TIMEOUT", "300"))
# 问题登记的 Redis 键过期时间（含等待 + 前端可回看的窗口）
_QUESTION_TTL = ASK_ANSWER_TIMEOUT + 600
# BLPOP 单片时长：与 redis 连接池 socket_timeout=5 对齐，避免长阻塞被连接层掐断
_POLL_SLICE = 4


class AskStudentInterrupt(Exception):
    """ask_student 工具抛出的中断：携带问题面板数据，由 Runner/Orchestrator 接管。"""

    def __init__(self, question: str, options: list, header: str, multi_select: bool):
        self.question = question
        self.options = options or []
        self.header = header or "补充信息"
        self.multi_select = bool(multi_select)
        self.question_id = f"q_{uuid.uuid4().hex[:12]}"
        super().__init__(f"ask_student: {question[:60]}")


# ── 答案总线（Redis 主 + 内存兜底） ───────────────────────

_mem_questions: dict = {}    # qid -> {"user_id": int, "ts": float}
_mem_events: dict = {}       # qid -> {"event": Event, "answer": Optional[str]}
_mem_lock = threading.Lock()


def _redis():
    """取 Redis 客户端；chat_service 环境返回 core 副本，否则返回 None（用内存兜底）。"""
    try:
        from core.redis_client import get_redis_client
        return get_redis_client()
    except Exception:
        return None


def publish_question(question_id: str, user_id: int, payload: dict) -> None:
    """登记一个待回答的问题（校验归属用），带 TTL。"""
    body = dict(payload)
    body["user_id"] = user_id
    body["ts"] = time.time()
    r = _redis()
    if r is not None:
        try:
            r.setex(f"ask:{question_id}", _QUESTION_TTL, json.dumps(body, ensure_ascii=False))
            return
        except Exception as e:
            logger.warning(f"[ask_student] Redis 登记问题失败，转内存: {e}")
    with _mem_lock:
        _mem_questions[question_id] = body
        _mem_events[question_id] = {"event": threading.Event(), "answer": None}


def poll_answer_once(question_id: str) -> Optional[str]:
    """非阻塞地取一次答案：有答案返回字符串，暂无返回 None。

    供 Orchestrator 的等待循环调用（循环里穿插 SSE 心跳）。内存兜底用短等待，
    避免空转烧 CPU。
    """
    r = _redis()
    if r is not None:
        try:
            item = r.blpop(f"ask_answer:{question_id}", timeout=_POLL_SLICE)
            if item:
                _, raw = item
                try:
                    data = json.loads(raw)
                    return str(data.get("answer", ""))
                except Exception:
                    return str(raw)
            return None
        except Exception as e:
            logger.warning(f"[ask_student] Redis 取答案异常，转内存: {e}")
    with _mem_lock:
        slot = _mem_events.get(question_id)
    if slot is None:
        # Redis 路径登记的问题落到这里说明混合状态：注册一个内存槽继续等
        with _mem_lock:
            slot = _mem_events.setdefault(question_id, {"event": threading.Event(), "answer": None})
    slot["event"].wait(timeout=_POLL_SLICE)
    if slot["answer"] is not None:
        return str(slot["answer"])
    return None


def submit_answer(question_id: str, user_id: int, answer: str) -> tuple[bool, str]:
    """学生提交答案（由 /api/chat/answer 调用）。返回 (是否成功, 提示信息)。"""
    answer = (answer or "").strip()
    if not answer:
        return False, "答案不能为空"

    r = _redis()
    if r is not None:
        try:
            raw = r.get(f"ask:{question_id}")
            if raw:
                info = json.loads(raw)
                if int(info.get("user_id", -1)) != int(user_id):
                    return False, "无权回答该问题"
                r.rpush(f"ask_answer:{question_id}",
                        json.dumps({"user_id": user_id, "answer": answer}, ensure_ascii=False))
                r.expire(f"ask_answer:{question_id}", 600)
                r.delete(f"ask:{question_id}")
                return True, "ok"
            # Redis 里没有：可能在内存兜底里，继续往下尝试
        except Exception as e:
            logger.warning(f"[ask_student] Redis 提交答案异常，转内存: {e}")

    with _mem_lock:
        info = _mem_questions.get(question_id)
        slot = _mem_events.get(question_id)
    if info is None or slot is None:
        return False, "问题不存在或已过期"
    if int(info.get("user_id", -1)) != int(user_id):
        return False, "无权回答该问题"
    slot["answer"] = answer
    slot["event"].set()
    with _mem_lock:
        _mem_questions.pop(question_id, None)
    return True, "ok"


# ── 面向 SubAgent 的工具 ──────────────────────────────────

@tool(description="""向学生发一个可交互的选项面板，用于关键信息不足、无法继续执行时向学生确认。

适用：学生的问题缺少必要参数（如没说哪一周/哪门课/什么格式），且你能给出 2-4 个具体候选选项。
不适用：能合理默认就别问；一次任务最多问 1-2 轮，问多了体验差。

options 传 JSON 数组字符串，每项 {"label": "选项文案", "description": "一句话说明"}，2-4 个；
留空则学生自由输入。调用后任务会暂停等学生选择，学生答案会注入后自动继续，无需自己处理。""")
def ask_student(question: str, options: str = "", header: str = "补充信息", multi_select: bool = False) -> str:
    """向学生发起互动提问（选项面板）。

    Args:
        question: 要问学生的问题，一句话说清楚缺什么信息（如"你想查询哪一周的课表？"）
        options: JSON 数组字符串 [{"label":"...","description":"..."}]，2-4 个选项；留空则学生自由输入
        header: 面板标题（简短，如"选择周次"、"输出格式"），默认"补充信息"
        multi_select: 是否允许多选，默认 False
    """
    question = (question or "").strip()
    if not question:
        return "[ask_student 失败] question 不能为空"
    parsed: list = []
    if options and options.strip():
        try:
            parsed = json.loads(options)
            if not isinstance(parsed, list):
                parsed = []
            parsed = [
                {"label": str(o.get("label", ""))[:60], "description": str(o.get("description", ""))[:120]}
                for o in parsed if isinstance(o, dict) and o.get("label")
            ][:4]
        except Exception as e:
            return f"[ask_student 失败] options 不是合法 JSON 数组: {e}"
    raise AskStudentInterrupt(question, parsed, header, multi_select)


ASK_TOOLS = [ask_student]
