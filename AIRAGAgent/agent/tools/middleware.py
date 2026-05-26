from typing import Callable
from AIRAGAgent.utils.prompt_loader import load_identity_prompts, load_report_prompts, load_tool_details
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


@before_model
def log_before_model(
        state:AgentState,       # 整个Agent智能体中的状态记录
        runtime:Runtime,        # 记录了整个执行过程中的上下文信息

):      # 在模型执行前输出日志
    logger.info(f"[log_before_model]即将调用模型，带有{len(state['messages'])}条消息。")

    # 检查消息列表是否为空，避免索引错误
    if state['messages']:
        last_message = state['messages'][-1]
        # 处理消息内容，可能是字符串或列表
        if isinstance(last_message.content, str):
            content_str = last_message.content.strip()
        elif isinstance(last_message.content, list):
            # 如果是列表，转换为字符串表示
            content_str = str(last_message.content)
        else:
            content_str = str(last_message.content)
        
        logger.debug(f"[log_before_model]{type(last_message).__name__} | {content_str}")
    else:
        logger.debug("[log_before_model]消息列表为空")

    return None

@dynamic_prompt
def smart_prompt_switch(request: ModelRequest):
    is_report = request.runtime.context.get("report", False)
    if is_report:
        return load_report_prompts()

    identity = load_identity_prompts()

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
        tool_details = load_tool_details(list(called_tools))
        return identity + "\n\n### 已调用工具的详细使用指南\n" + tool_details

    return identity