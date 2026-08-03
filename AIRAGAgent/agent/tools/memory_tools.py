"""DeepAgent 记忆工具：让 Agent 能主动记住 / 召回用户长期事实。

记忆类型：
- fact：客观事实（如"用户是 Python 开发者"）
- preference：偏好（如"回答时偏好简洁，不要表格"）
- project：项目状态（如"用户在做 lc-course 改造"）
- schedule：日程类（如"每周五例会"）

ContextVar 依赖 user_id_var（由 chat_service 在调用前设置）。
"""
from typing import List, Dict, Optional
from langchain_core.tools import tool

from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.agent.tools.agent_tools import user_id_var
from AIRAGAgent.database import (
    save_memory as _save_memory,
    recall_memories as _recall_memories,
    get_memory as _get_memory,
    deactivate_memory as _deactivate_memory,
)


def _uid() -> int:
    uid = user_id_var.get()
    if uid is None:
        raise RuntimeError("当前请求未设置 user_id_var，无法操作记忆")
    return int(uid)


@tool(description="""记住一条关于用户的长期信息，下次会话也能用到。

适用场景：
- 用户告诉你他的身份/职业/项目/偏好（如"我是后端开发"、"在做 lc-course 项目"）
- 用户明确让你记住某事（"记一下我下周要出差"）
- 你判断某信息跨会话有价值（如"用户喜欢简洁回答"）

不要记的：
- 一次性的临时问题（"今天天气"）
- 已经在对话历史里的内容
- 推测而非确认的信息""")
def remember(key_name: str, value: str, memory_type: str = "fact",
             confidence: float = 1.0) -> str:
    """
    Args:
        key_name: 记忆的键名，简短且唯一（如 "职业"、"项目.lc-course.技术栈"）。同名 key 会覆盖。
        value: 记忆内容，自然语言描述即可。
        memory_type: fact(事实) / preference(偏好) / project(项目) / schedule(日程)，默认 fact
        confidence: 置信度 0-1，默认 1.0
    """
    try:
        uid = _uid()
        mid = _save_memory(uid, memory_type, key_name, value, source="agent", confidence=confidence)
        logger.info(f"[memory] remember user={uid} key={key_name} type={memory_type}")
        return f"已记住：{key_name} = {value}（类型: {memory_type}, id: {mid}）"
    except Exception as e:
        return f"记忆写入失败：{e}"


@tool(description="召回用户已记住的长期信息。可按类型或关键词过滤。无参数则返回最近所有记忆。")
def recall(keyword: str = "", memory_type: str = "", limit: int = 20) -> str:
    """
    Args:
        keyword: 关键词过滤（匹配 key 或 value）。空字符串表示不过滤。
        memory_type: 类型过滤：fact / preference / project / schedule。空字符串表示不过滤。
        limit: 最多返回几条，默认 20
    """
    try:
        uid = _uid()
        rows = _recall_memories(
            uid,
            memory_type=memory_type or None,
            keyword=keyword or None,
            limit=int(limit),
        )
        if not rows:
            return "暂无相关记忆"
        lines = [f"共召回 {len(rows)} 条记忆："]
        for r in rows:
            lines.append(f"- [{r['type']}] {r['key']}: {r['value']}（置信度 {r['confidence']}, 更新于 {r['updated_at']}）")
        return "\n".join(lines)
    except Exception as e:
        return f"召回失败：{e}"


@tool(description="精确读取某个 key 的记忆值。找不到返回空字符串。")
def recall_one(key_name: str) -> str:
    """Args: key_name: 记忆的键名"""
    try:
        uid = _uid()
        v = _get_memory(uid, key_name)
        return v if v else f"未找到记忆：{key_name}"
    except Exception as e:
        return f"读取失败：{e}"


@tool(description="删除一条记忆（软删除，不再被召回）。传入 key_name 或 id 都可。")
def forget(key_name: str = "", memory_id: int = 0) -> str:
    if not key_name and not memory_id:
        return "请提供 key_name 或 memory_id"
    try:
        uid = _uid()
        affected = _deactivate_memory(uid, key_name=key_name or None, memory_id=memory_id or None)
        return f"已遗忘 {affected} 条记忆" if affected else "未找到对应记忆"
    except Exception as e:
        return f"删除失败：{e}"


MEMORY_TOOLS = [remember, recall, recall_one, forget]
