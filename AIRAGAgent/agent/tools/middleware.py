from typing import Callable
from AIRAGAgent.utils.prompt_loader import load_system_prompts,load_report_prompts
from langchain.agents import AgentState
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command
from AIRAGAgent.utils.logger_handler import logger


@wrap_tool_call
def monitor_tool(
        #请求的数据封装
        request: ToolCallRequest,
        #调用的函数
        handler: Callable[[ToolCallRequest], ToolMessage |  Command]
) -> ToolMessage | Command:
    logger.info(f"[tool monitor]执行工具:{request.tool_call['name']}")
    logger.info(f"[tool monitor]工具参数:{request.tool_call['args']}")

    try:
        result = handler(request)
        logger.info(f"[tool monitor]工具{request.tool_call['name']}调用成功")
        return  result
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
def report_prompt_switch(request:ModelRequest):     #每一次在生成提示词之前，调用此函数
    is_report = request.runtime.context.get("report", False)
    if is_report:       # 是报告生成场景，返回报告生成提示词内容
        return load_report_prompts()

    return load_system_prompts()