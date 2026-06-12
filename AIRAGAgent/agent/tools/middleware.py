"""
中间件：监控 + 日志 + 动态 prompt 切换（含 Skill 感知）

改造点：
- smart_prompt_switch 不再按已调用工具名注入 tool 详情，改为识别当前激活的 Skill 并注入其专属 prompt
- 新增 SkillTrackingMiddleware：跟踪 tool 调用，根据调用的 tool 反查所属 Skill 并自动激活
"""
from typing import Callable, Optional
from AIRAGAgent.utils.prompt_loader import load_identity_prompts, load_report_prompts
from langchain.agents import AgentState
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command
from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.infrastructure.rate_limiter import get_tool_rate_limiter


@wrap_tool_call
def monitor_tool(
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command]
) -> ToolMessage | Command:
    tool_name = request.tool_call['name']
    limiter = get_tool_rate_limiter()
    allowed, remaining = limiter.is_allowed(tool_name)
    if not allowed:
        logger.warning(f"[tool monitor] 工具 {tool_name} 被限流")
        return ToolMessage(
            content=f"工具调用过于频繁（{limiter.max_requests}次/{limiter.window_seconds}秒），请稍后再试",
            tool_call_id=request.tool_call["id"],
        )

    logger.info(f"[tool monitor]执行工具:{tool_name}")
    logger.info(f"[tool monitor]工具参数:{request.tool_call['args']}")

    try:
        result = handler(request)
        logger.info(f"[tool monitor]工具{request.tool_call['name']}调用成功")
        return result
    except Exception as e:
        logger.error(f"工具{request.tool_call['name']}调用失败，原因:{str(e)}")
        if request.tool_call['name'] == "fill_context_for_report":
            request.runtime.context["report"] = True
        raise e


@wrap_tool_call
def skill_aware_monitor(
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command]
) -> ToolMessage | Command:
    """
    增强版 monitor：在调用工具时，自动识别工具所属 Skill 并激活。
    对后续的 smart_prompt_switch 注入 skill prompt 提供依据。
    """
    from AIRAGAgent.skills.base import SkillRegistry

    tool_name = request.tool_call['name']
    limiter = get_tool_rate_limiter()
    allowed, remaining = limiter.is_allowed(tool_name)
    if not allowed:
        logger.warning(f"[skill monitor] 工具 {tool_name} 被限流")
        return ToolMessage(
            content=f"工具调用过于频繁（{limiter.max_requests}次/{limiter.window_seconds}秒），请稍后再试",
            tool_call_id=request.tool_call["id"],
        )

    # ── Skill 感知：当任意 tool 被调用时，激活其所属 Skill（线程安全，使用 runtime context）──
    registry = SkillRegistry()
    skill = registry.find_skill_by_tool(tool_name)
    if skill and hasattr(request, 'runtime') and request.runtime:
        existing = request.runtime.context.get("active_skills", [])
        if skill.name not in existing:
            existing.append(skill.name)
            request.runtime.context["active_skills"] = existing
            logger.info(f"[skill monitor] 自动激活 skill [{skill.name}]（runtime context），因为调用了工具 {tool_name}")

    logger.info(f"[skill monitor]执行工具:{tool_name}")
    logger.info(f"[skill monitor]工具参数:{request.tool_call['args']}")

    try:
        result = handler(request)
        logger.info(f"[skill monitor]工具{request.tool_call['name']}调用成功")
        return result
    except Exception as e:
        logger.error(f"工具{request.tool_call['name']}调用失败，原因:{str(e)}")
        if request.tool_call['name'] == "fill_context_for_report":
            request.runtime.context["report"] = True
        raise e


@before_model
def log_before_model(
        state: AgentState,
        runtime: Runtime,
):
    logger.info(f"[log_before_model]即将调用模型，带有{len(state['messages'])}条消息。")

    if state['messages']:
        last_message = state['messages'][-1]
        if isinstance(last_message.content, str):
            content_str = last_message.content.strip()
        elif isinstance(last_message.content, list):
            content_str = str(last_message.content)
        else:
            content_str = str(last_message.content)

        logger.debug(f"[log_before_model]{type(last_message).__name__} | {content_str}")
    else:
        logger.debug("[log_before_model]消息列表为空")

    return None


@dynamic_prompt
def smart_prompt_switch(request: ModelRequest):
    """
    Skill 感知版 prompt 切换：
    - 从 runtime context 读取激活的 skills（线程安全，每请求独立）
    - 将对应 skill 的 system_prompt 注入 identity prompt 之后
    - 同时保留 report 场景的特殊 prompt 切换
    """
    from AIRAGAgent.skills.base import SkillRegistry

    # report 场景特殊处理
    is_report = request.runtime.context.get("report", False)
    if is_report:
        return load_report_prompts()

    identity = load_identity_prompts()

    # ── Skill 感知：从 runtime context 读取当前激活的 Skill（线程安全）──
    registry = SkillRegistry()
    active_skill_names = request.runtime.context.get("active_skills", [])
    prompts = []
    for name in active_skill_names:
        skill = registry.get_skill(name)
        if skill and skill.system_prompt:
            prompts.append(f"<!-- 已激活技能 [{name}] -->\n{skill.system_prompt}")

    if prompts:
        logger.info(f"[smart_prompt_switch] 注入 {len(prompts)} 个活跃 skill 的 prompt（来源: runtime context）")
        return identity + "\n\n" + "\n\n---\n\n".join(prompts)

    # 兼容旧逻辑：如果没有通过 skill 激活，回退到按已调用工具注入详情
    state = request.state
    messages = state.get("messages", [])
    called_tools = set()
    for msg in messages:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name", "")
                if name:
                    called_tools.add(name)

    if called_tools:
        from AIRAGAgent.utils.prompt_loader import load_tool_details
        tool_details = load_tool_details(list(called_tools))
        return identity + "\n\n### 已调用工具的详细使用指南\n" + tool_details

    return identity
