from langchain.agents import create_agent
from prompt_toolkit.shortcuts import input_dialog
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage

from AIRAGAgent.model.local_factory import local_chat_model
from AIRAGAgent.model.factory import chat_model
from AIRAGAgent.utils.prompt_loader import load_system_prompts
from AIRAGAgent.agent.tools.agent_tools import (rag_summarize, get_weather, get_user_location, get_user_id,
                                                get_current_month, fetch_external_data, fill_context_for_report,
                                                get_schedule)
from AIRAGAgent.agent.tools.file_tools import (auto_fill_word)
from AIRAGAgent.agent.tools.search_tools import (search)
from AIRAGAgent.agent.tools.middleware import monitor_tool,log_before_model,report_prompt_switch


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


# 创建智能体
agent = create_agent(
    model=local_chat_model,
    system_prompt=load_system_prompts(),
    tools=[rag_summarize,get_weather,get_user_location,get_user_id,
           get_current_month,fetch_external_data,fill_context_for_report,get_schedule,
           auto_fill_word,search],
    middleware=[monitor_tool,log_before_model,report_prompt_switch],
)


def call_agent(state: AgentState):
    """调用智能体并返回结果"""
    input_dict = {"messages": state["messages"]}
    result = agent.invoke(input_dict, context={"report": False})
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
    
    # 执行智能体的流式输出
    def execute_stream(self, query: str):
        """
        Args:
            query: 用户的查询
        """
        # 构建输入字典
        input_dict = {
            "messages":[
                HumanMessage(content=query),
            ]
        }
        # 第三个参数context就是上下文runtime中的信息，就是我们做提示词切换的标记
        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk['messages'][-1]
            if latest_message.content:
                yield latest_message.content.strip()+"\n"


if __name__ == '__main__':
    agent_instance = ReactAgent()

    for chunk in agent_instance.execute_stream("给我生成使用报告"):
        print(chunk, end="", flush=True)