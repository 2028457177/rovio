from typing import Dict, Optional, List

from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict, Annotated, Sequence
import operator

from AIRAGAgent.agent.react_agent import ReactAgent
from AIRAGAgent.model.factory import chat_model
from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.utils.prompt_loader import load_all_tool_details

SUPERVISOR_SYSTEM_PROMPT = """你是一个任务编排智能体。你的唯一职责是：分析用户需求，对照可用工具清单，将任务拆解成具体的工具调用步骤，交给工作智能体执行。

工作智能体是一个只会按指令调用工具的执行者，它不会自行判断该调什么工具。所以你必须在委派任务中明确写出每一步要调用的工具名称和参数，不能只说"查询一下课表"这种模糊的话。

## 铁律（违反任何一条都算失败）
1. 禁止在TASK/RETRY中写出任何具体数据（日期、城市名、用户ID等）。所有数据必须通过调用工具获取。写"假设今天是X月X日"就是违规。
2. 禁止使用模糊描述替代工具名。写"查询课表工具"就是违规，必须写 get_schedule。
3. TASK 中每个步骤必须包含「调用 工具名(参数=值)」格式，不允许"步骤1：获取用户ID"这种没有工具名的写法。
4. 每次先想清楚用哪些工具、顺序是什么，再写 TASK。不确定的工具去"可用工具详细清单"里找。

## TASK 输出模板（必须原样套用，不可省略任何部分）
TASK: 请严格按以下步骤执行，不要跳过或合并任何步骤：
1. 调用 <工具名>(<参数名>=<参数值>) — <说明该步骤目的>
2. 用第1步返回的 <字段名>，调用 <工具名>(<参数名>=<第1步的字段名>) — <说明该步骤目的>
N. 将以上工具返回的数据整理成清晰的格式，输出给用户。

## 正确 vs 错误 对比
用户问："明天有什么课"

【错误 - 绝对禁止】TASK: 查询用户明天（2026年5月27日，星期三）的课程安排，包括课程名称、时间、地点。
> 违规：自己写了具体日期，且没有写工具名，worker 不知道该调什么。

【正确 - 必须这样写】TASK: 请严格按以下步骤执行：
1. 调用 get_current_month(wantday=1) — 获取明天的日期、学期周次和星期几。
2. 用第1步返回的 week 和 day，调用 get_schedule(week=<第1步的week>, day=<第1步的day>) — 查询明天的课程。
3. 将第2步返回的课程列表（时间段、课程名、节次、地点）整理成清晰的格式输出。

## RETRY 模板（也必须写出具体工具名和步骤）
RETRY: 上次执行有问题：<指出具体哪里不对>。请重新按以下步骤执行：
1. 调用 <工具名>(<参数名>=<参数值>)
2. 调用 <工具名>(<参数名>=<第1步的xxx>)
...

## 审查标准
- 工作智能体是否按你编排的步骤逐一调用了正确的工具
- 返回的数据是否真实（通过工具获取，而非编造）
- 是否完整回答了用户的核心问题

## 注意
- 最多重试1次，第2次审查必须 ACCEPT
- 你的名字是"任务编排智能体"，你的价值在于编排，不要替工作智能体做它该做的事"""


class SupervisorState(TypedDict):
    messages: Annotated[Sequence, operator.add]
    iteration: int


class SupervisorAgent:
    MAX_RETRIES = 1

    def __init__(self):
        self.worker = ReactAgent()
        self.supervisor_llm = chat_model

    @staticmethod
    def _extract_text(content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)
        return str(content)

    def _parse_supervisor_response(self, text: str) -> Dict[str, str]:
        if text.startswith("TASK:"):
            return {"action": "delegate", "task": text[5:].strip()}
        elif text.startswith("ACCEPT:"):
            return {"action": "accept", "final_answer": text[7:].strip()}
        elif text.startswith("RETRY:"):
            return {"action": "retry", "feedback": text[6:].strip()}
        else:
            first_line = text.split("\n")[0].strip() if text else ""
            if "TASK" in first_line.upper():
                return {
                    "action": "delegate",
                    "task": text.replace("TASK:", "").replace("TASK", "").strip(),
                }
            return {"action": "accept", "final_answer": text}

    @staticmethod
    def _format_history(chat_history: Optional[List[Dict[str, str]]]) -> str:
        """将对话历史格式化为上下文字符串"""
        if not chat_history:
            return ""
        lines = ["## 对话历史上下文"]
        for entry in chat_history:
            role = "用户" if entry.get("role") == "user" else "助手"
            lines.append(f"- {role}: {entry.get('content', '')}")
        lines.append("---")
        return "\n".join(lines)

    def _get_full_system_prompt(self) -> str:
        if not hasattr(self, "_cached_system_prompt"):
            tool_details = load_all_tool_details()
            self._cached_system_prompt = (
                SUPERVISOR_SYSTEM_PROMPT + "\n\n## 可用工具详细清单\n\n" + tool_details
            )
        return self._cached_system_prompt

    def _supervisor_decide(
        self,
        user_query: str,
        worker_result: str = None,
        retry_count: int = 0,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, str]:
        history_context = self._format_history(chat_history)
        full_prompt = self._get_full_system_prompt()
        if worker_result is None:
            messages = [
                SystemMessage(content=full_prompt),
                HumanMessage(
                    content=(
                        f"用户原始需求：\n{user_query}\n\n"
                        f"{history_context}"
                        f"请分析需求、确定需要用到的工具、编排步骤后委派任务给工作智能体。"
                    )
                ),
            ]
        else:
            force_accept_note = (
                "注意：这是最后一次审查机会，必须给出ACCEPT决策。"
                if retry_count >= self.MAX_RETRIES
                else ""
            )
            messages = [
                SystemMessage(content=full_prompt),
                HumanMessage(
                    content=(
                        f"用户原始需求：\n{user_query}\n\n"
                        f"工作智能体执行结果：\n{worker_result}\n\n"
                        f"{history_context}"
                        f"这是第{retry_count + 1}次审查。{force_accept_note}"
                        f"请审查以上结果，判断是否满足用户需求。"
                    )
                ),
            ]

        response = self.supervisor_llm.invoke(messages)
        content = self._extract_text(
            response.content if hasattr(response, "content") else response
        )
        logger.info(f"[Supervisor] 决策内容: {content[:200]}...")

        return self._parse_supervisor_response(content)

    def _yield_worker_chunks(self, task: str, chat_history: Optional[List[Dict[str, str]]] = None):
        output_parts = []
        for chunk in self.worker.execute_stream(task, chat_history):
            yield chunk
            if isinstance(chunk, dict) and chunk["type"] == "output":
                output_parts.append(chunk["content"])
        return "".join(output_parts)

    def execute_stream(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None):
        logger.info(f"[Supervisor] 收到用户任务: {query[:100]}...")

        yield {"type": "supervisor_thinking", "content": "监督智能体正在分析任务需求..."}

        decision = self._supervisor_decide(query, chat_history=chat_history)

        if decision.get("action") != "delegate":
            yield {"type": "output", "content": decision.get("final_answer", "")}
            return

        worker_task = decision.get("task", query)
        yield {
            "type": "supervisor_action",
            "content": "任务已委派给工作智能体执行",
        }

        worker_result = yield from self._yield_worker_chunks(worker_task, chat_history)

        for retry_count in range(self.MAX_RETRIES + 1):
            yield {
                "type": "supervisor_thinking",
                "content": "监督智能体正在审查工作成果...",
            }

            review = self._supervisor_decide(query, worker_result, retry_count, chat_history)

            if review.get("action") == "accept":
                yield {
                    "type": "supervisor_thinking",
                    "content": "审查通过，输出最终回复",
                }
                yield {"type": "output", "content": review.get("final_answer", worker_result)}
                return

            if retry_count >= self.MAX_RETRIES:
                yield {
                    "type": "supervisor_thinking",
                    "content": "已达最大重试次数，输出当前最优结果",
                }
                force_accept = self._supervisor_decide(
                    query, worker_result, retry_count + 1, chat_history
                )
                yield {
                    "type": "output",
                    "content": force_accept.get("final_answer", worker_result),
                }
                return

            yield {
                "type": "supervisor_action",
                "content": f"工作成果需要改进：{review.get('feedback', '请重新执行')}",
            }

            worker_result = yield from self._yield_worker_chunks(
                review.get("feedback", query), chat_history
            )

    def execute(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        output_parts = []
        for chunk in self.execute_stream(query, chat_history):
            if isinstance(chunk, dict) and chunk["type"] == "output":
                output_parts.append(chunk["content"])
        return "".join(output_parts)
