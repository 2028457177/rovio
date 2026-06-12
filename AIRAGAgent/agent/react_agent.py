from langchain.agents import create_agent
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from prompt_toolkit.shortcuts import input_dialog
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence, Optional, List, Dict
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk, ToolMessage

from AIRAGAgent.model.factory import chat_model
from AIRAGAgent.utils.prompt_loader import load_identity_prompts
from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.agent.tools.agent_tools import _get_rag
from AIRAGAgent.agent.tools.middleware import skill_aware_monitor, log_before_model, smart_prompt_switch

# ── Skill 体系集成 ──
from AIRAGAgent.skills.definitions import register_all_skills
from AIRAGAgent.skills.base import SkillRegistry

# 注册所有 Skill（模块加载时一次性完成，单例保证只注册一次）
register_all_skills()

# 从 SkillRegistry 收集所有工具，不再手动逐个 import 工具函数
registry = SkillRegistry()
all_skill_tools = registry.get_all_tools()


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


tool_call_limiter = ToolCallLimitMiddleware(run_limit=15, exit_behavior="end")

# 创建智能体（工具列表由 SkillRegistry 统一管理）
agent = create_agent(
    model=chat_model,
    system_prompt=load_identity_prompts(),
    tools=all_skill_tools,
    middleware=[tool_call_limiter, skill_aware_monitor, log_before_model, smart_prompt_switch],
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

    @classmethod
    def create_standalone(cls):
        """创建独立的 ReactAgent 实例，拥有独占的 agent（线程安全，用于并行执行）"""
        instance = cls.__new__(cls)
        instance.agent = create_agent(
            model=chat_model,
            system_prompt=load_identity_prompts(),
            tools=all_skill_tools,
            middleware=[
                ToolCallLimitMiddleware(run_limit=15, exit_behavior="end"),
                skill_aware_monitor,
                log_before_model,
                smart_prompt_switch,
            ],
        )
        _get_rag()
        return instance
    
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
        any_tools_called = False
        last_tool_results = {}
        has_user_output = False  # 模型是否产生了面向用户的文本输出

        for msg, metadata in self.agent.stream(
            input_dict,
            stream_mode="messages",
            subgraphs=False,
            context={"report": False},
        ):
            if isinstance(msg, AIMessageChunk):
                has_tool_calls = bool(msg.tool_calls) if hasattr(msg, 'tool_calls') else False

                if has_tool_calls:
                    any_tools_called = True
                    for tc in msg.tool_calls:
                        tc_id = tc.get("id", "")
                        tc_name = tc.get("name", "")
                        if tc_id and tc_name and tc_id not in seen_tool_ids:
                            seen_tool_ids.add(tc_id)
                            has_entered_tool_phase = True
                            yield {
                                "type": "thinking",
                                "content": f"\n正在调用工具: {tc_name}\n"
                            }

                # 提取输出内容（优先 msg.content，回退到 reasoning_content）
                output_text = msg.content or ""
                reasoning = (
                    getattr(msg, 'additional_kwargs', None) or {}
                ).get('reasoning_content', '')

                if reasoning and not output_text:
                    # 纯推理无正文：当作 thinking 展示（原始 delta 连续累积）
                    yield {
                        "type": "thinking",
                        "content": reasoning
                    }
                else:
                    if not output_text and reasoning:
                        output_text = reasoning

                if output_text:
                    if has_entered_tool_phase:
                        yield {
                            "type": "thinking_end",
                            "content": ""
                        }
                        has_entered_tool_phase = False
                    has_user_output = True
                    yield {
                        "type": "output",
                        "content": output_text
                    }

            elif isinstance(msg, ToolMessage):
                tool_name = getattr(msg, 'name', '未知工具')
                last_tool_results[tool_name] = str(msg.content)
                if tool_name not in reported_tool_results:
                    reported_tool_results.add(tool_name)
                    yield {
                        "type": "thinking",
                        "content": f"\n工具 [{tool_name}] 执行完成\n"
                    }

        # 安全兜底：模型调用了工具但未产出文本时，追加原始数据
        if any_tools_called and not has_user_output and last_tool_results:
            fallback_parts = []
            for tname, tresult in last_tool_results.items():
                fallback_parts.append(f"**{tname} 结果**：\n{tresult}\n")
            yield {"type": "output", "content": "\n\n---\n" + "\n".join(fallback_parts)}


if __name__ == '__main__':
    agent_instance = ReactAgent()

    for chunk in agent_instance.execute_stream("给我生成使用报告"):
        if isinstance(chunk, dict):
            print(f"[{chunk['type']}] {chunk['content']}", flush=True)
        else:
            print(chunk, end="", flush=True)