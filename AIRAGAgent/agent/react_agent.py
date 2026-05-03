from langchain.agents import create_agent
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from prompt_toolkit.shortcuts import input_dialog
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage

from AIRAGAgent.model.local_factory import local_chat_model
from AIRAGAgent.model.factory import chat_model
from AIRAGAgent.utils.prompt_loader import load_system_prompts
from AIRAGAgent.agent.tools.agent_tools import (rag_summarize, get_weather, get_user_location, get_user_id,
                                                get_current_month, fetch_external_data, fill_context_for_report,
                                                get_schedule, get_city_code)
from AIRAGAgent.agent.tools.agent_tools import _get_rag
from AIRAGAgent.agent.tools.file_tools import (auto_fill_word)
from AIRAGAgent.agent.tools.search_tools import (search)
from AIRAGAgent.agent.tools.wx_tools import (send_wx_message)
from AIRAGAgent.agent.tools.middleware import monitor_tool,log_before_model,report_prompt_switch


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


tool_call_limiter = ToolCallLimitMiddleware(run_limit=15, exit_behavior="end")

# 创建智能体
agent = create_agent(
    model=local_chat_model,
    system_prompt=load_system_prompts(),
    tools=[rag_summarize,get_weather,get_user_location,get_city_code,get_user_id,
           get_current_month,fetch_external_data,fill_context_for_report,get_schedule,
           auto_fill_word,search,send_wx_message],
    middleware=[tool_call_limiter, monitor_tool, log_before_model, report_prompt_switch],
)


def call_agent(state: AgentState):
    """调用智能体并返回结果"""
    input_dict = {"messages": state["messages"]}
    result = agent.invoke(
        input_dict,
        config={"recursion_limit": 30},
        context={"report": False},
    )
    return {"messages": result["messages"]}


# 创建LangGraph图
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_agent)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

# 编译图
graph = workflow.compile()


class ReactAgent:
    """ReactAgent类，用于封装智能体功能"""
    def __init__(self):
        self.agent = agent
        self.graph = graph
        _get_rag()
    
    # 执行智能体的流式输出
    def execute_stream(self, query: str):
        """
        Args:
            query: 用户的查询

        Yields:
            dict: {"type": "thinking"|"output", "content": str}
        """
        input_dict = {
            "messages": [
                HumanMessage(content=query),
            ]
        }
        seen_message_ids = set()
        has_entered_tool_phase = False

        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk['messages'][-1]
            msg_id = id(latest_message)

            if msg_id in seen_message_ids:
                continue
            seen_message_ids.add(msg_id)

            has_tool_calls = (
                isinstance(latest_message, AIMessage)
                and latest_message.tool_calls
            )
            is_tool = isinstance(latest_message, ToolMessage)

            if has_tool_calls:
                has_entered_tool_phase = True
                content = latest_message.content or ""
                if latest_message.tool_calls:
                    tool_names = [tc.get("name", "未知工具") for tc in latest_message.tool_calls]
                    tool_info = f"正在调用工具: {', '.join(tool_names)}"
                    if content:
                        content = f"{content}\n{tool_info}"
                    else:
                        content = tool_info
                yield {
                    "type": "thinking",
                    "content": content.strip()
                }
            elif is_tool:
                tool_name = getattr(latest_message, 'name', '未知工具')
                result_preview = _truncate_content(str(latest_message.content))
                yield {
                    "type": "thinking",
                    "content": f"工具 [{tool_name}] 执行完成\n{result_preview}"
                }
            elif isinstance(latest_message, AIMessage) and latest_message.content:
                if has_entered_tool_phase:
                    yield {
                        "type": "thinking_end",
                        "content": ""
                    }
                yield {
                    "type": "output",
                    "content": latest_message.content.strip()
                }


def _truncate_content(content: str, max_len: int = 200) -> str:
    if len(content) <= max_len:
        return content
    return content[:max_len] + "..."


if __name__ == '__main__':
    agent_instance = ReactAgent()

    for chunk in agent_instance.execute_stream("给我生成使用报告"):
        if isinstance(chunk, dict):
            print(f"[{chunk['type']}] {chunk['content']}", flush=True)
        else:
            print(chunk, end="", flush=True)