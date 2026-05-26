from langchain.agents import create_agent
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from prompt_toolkit.shortcuts import input_dialog
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence, Optional, List, Dict
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk, ToolMessage

from AIRAGAgent.model.local_factory import local_chat_model
from AIRAGAgent.model.factory import chat_model
from AIRAGAgent.utils.prompt_loader import load_identity_prompts
from AIRAGAgent.agent.tools.agent_tools import (rag_summarize, get_weather, get_user_location, get_user_id,
                                                get_current_month, fetch_external_data, fill_context_for_report,
                                                get_schedule, get_city_code)
from AIRAGAgent.agent.tools.agent_tools import _get_rag
from AIRAGAgent.agent.tools.file_tools import (auto_fill_word)
from AIRAGAgent.agent.tools.search_tools import (search)
from AIRAGAgent.agent.tools.wx_tools import (send_wx_message)
from AIRAGAgent.agent.tools.middleware import monitor_tool,log_before_model,smart_prompt_switch


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


tool_call_limiter = ToolCallLimitMiddleware(run_limit=15, exit_behavior="end")

# 创建智能体
agent = create_agent(
    model=local_chat_model,
    system_prompt=load_identity_prompts(),
    tools=[rag_summarize,get_weather,get_user_location,get_city_code,get_user_id,
           get_current_month,fetch_external_data,fill_context_for_report,get_schedule,
           auto_fill_word,search,send_wx_message],
    middleware=[tool_call_limiter, monitor_tool, log_before_model, smart_prompt_switch],
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
    
    @staticmethod
    def _history_to_messages(chat_history: Optional[List[Dict[str, str]]]) -> list:
        """将聊天历史转换为LangChain消息列表"""
        if not chat_history:
            return []
        messages = []
        for entry in chat_history:
            role = entry.get("role", "")
            content = entry.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    def execute_stream(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None):
        """
        Args:
            query: 用户的查询
            chat_history: 历史对话记录，格式为 [{"role": "user"/"assistant", "content": "..."}]

        Yields:
            dict: {"type": "thinking"|"thinking_end"|"output", "content": str}
        """
        history_messages = self._history_to_messages(chat_history)
        input_messages = history_messages + [HumanMessage(content=query)]
        input_dict = {"messages": input_messages}
        seen_tool_ids = set()
        reported_tool_results = set()
        has_entered_tool_phase = False

        for msg, metadata in self.agent.stream(
            input_dict,
            stream_mode="messages",
            subgraphs=False,
            context={"report": False},
        ):
            if isinstance(msg, AIMessageChunk):
                has_tool_calls = bool(msg.tool_calls) if hasattr(msg, 'tool_calls') else False

                if has_tool_calls:
                    for tc in msg.tool_calls:
                        tc_id = tc.get("id", "")
                        tc_name = tc.get("name", "")
                        if tc_id and tc_name and tc_id not in seen_tool_ids:
                            seen_tool_ids.add(tc_id)
                            has_entered_tool_phase = True
                            yield {
                                "type": "thinking",
                                "content": f"正在调用工具: {tc_name}"
                            }

                if msg.content:
                    if has_entered_tool_phase:
                        yield {
                            "type": "thinking_end",
                            "content": ""
                        }
                        has_entered_tool_phase = False
                    yield {
                        "type": "output",
                        "content": msg.content
                    }

            elif isinstance(msg, ToolMessage):
                tool_name = getattr(msg, 'name', '未知工具')
                if tool_name not in reported_tool_results:
                    reported_tool_results.add(tool_name)
                    result_preview = _truncate_content(str(msg.content))
                    yield {
                        "type": "thinking",
                        "content": f"工具 [{tool_name}] 执行完成\n{result_preview}"
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