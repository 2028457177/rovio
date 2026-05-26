from typing import Dict, Optional, List

from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict, Annotated, Sequence
import operator

from AIRAGAgent.agent.react_agent import ReactAgent
from AIRAGAgent.model.factory import chat_model
from AIRAGAgent.utils.logger_handler import logger

SUPERVISOR_SYSTEM_PROMPT = """你是一个任务监督智能体，你的职责是协调工作智能体完成用户任务。

## 工作流程
1. 分析用户的原始需求
2. 将任务委派给工作智能体执行
3. 审查工作智能体的执行结果，判断是否满足用户需求
4. 如果满足要求，生成最终的专业回复给用户
5. 如果不满足要求，提出具体的改进建议，让工作智能体重新执行

## 输出格式
你必须严格按照以下格式输出，用一个英文冒号开头的指令标记你的决策：

【初次委派阶段】
如果没有工作智能体的执行结果，直接输出委派的任务描述：
TASK: <委派给工作智能体的任务描述>

【审查阶段】
当收到工作智能体的执行结果后：

如果结果满足用户需求：
ACCEPT: <直接写给用户的最终回复内容>

如果结果不满足需求（信息缺失、逻辑不连贯、未回答问题核心等）：
RETRY: <具体改进建议，告诉工作智能体哪里不足，需要补充什么>

## 审查标准
- 是否完整回答了用户的核心问题
- 信息是否准确、充分
- 逻辑是否连贯、专业
- 格式是否清晰易读

## 注意事项
- 最多允许重试1次，第2次审查时必须给出ACCEPT决策
- 用户的原始需求始终是你的最终判断依据"""


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

    def _supervisor_decide(
        self,
        user_query: str,
        worker_result: str = None,
        retry_count: int = 0,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, str]:
        history_context = self._format_history(chat_history)
        if worker_result is None:
            messages = [
                SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"用户原始需求：\n{user_query}\n\n"
                        f"{history_context}"
                        f"请分析需求并委派任务给工作智能体。"
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
                SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
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
