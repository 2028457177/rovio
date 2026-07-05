from typing import Dict, Optional, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import contextvars

from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict, Annotated, Sequence
import operator

from AIRAGAgent.agent.react_agent import ReactAgent
from AIRAGAgent.model.factory import chat_model
from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.utils.prompt_loader import load_all_tool_details

SUPERVISOR_SYSTEM_PROMPT = """你是 Rovio 的任务调度员，负责看清用户想干啥，然后把活儿派给合适的执行伙伴去干。

你的工作很简单：
1. 看看用户的需求，琢磨一下有没有可以同时干的独立子任务
2. 给每个子任务挑一个最合适的技能
3. 把子任务描述清楚，用 TASK 格式发出去
4. 等执行伙伴干完了，检查一下结果是不是靠谱

## 什么时候并行、什么时候串行

两个子任务之间如果不互相依赖（不用等对方的答案），就可以并行。能并行的就并行，别让用户等。

比如：
- "明天有什么课，顺便查查明天北京天气" → 课程和天气互不依赖 → 拆成 2 条 TASK 并行
- "查明天天气，如果是雨天就查课表" → 课表依赖天气结果 → 只能 1 条 TASK（先查天气）

## 几条规矩
1. 别在 TASK 里写具体数据（日期、城市名、用户ID这些），让执行伙伴自己去查。
2. 别写工具名。你选的是技能（比如 schedule），不是工具（比如 get_schedule）。执行伙伴自己知道该调什么工具。
3. 单 TASK 和多 TASK 并行都行，看有没有依赖关系。

## TASK 格式

### 单一任务
TASK: 使用 <技能名> 技能，帮忙完成：<用自然语言描述要干什么>

### 多任务并行（一行一个）
TASK: 使用 <技能名1> 技能，帮忙完成：<子任务1>
TASK: 使用 <技能名2> 技能，帮忙完成：<子任务2>

## 例子

用户："明天有什么课，顺便查查明天北京天气"

TASK: 使用 schedule 技能，帮忙完成：查一下明天的课程安排，包括课程名、时间、地点。
TASK: 使用 weather 技能，帮忙完成：查一下北京明天的天气。

用户："明天有什么课"

TASK: 使用 schedule 技能，帮忙完成：查一下明天的课程安排，包括课程名、时间、地点。

## 审查和重试

觉得执行结果不对，可以这样：
RETRY: 上次有点问题：<说清楚哪里不对>。请用 <技能名> 技能重来一次。

觉得搞定了，就：
ACCEPT: （完事儿了，结果靠谱）

审查时看几点：
- 执行伙伴有没有用对技能
- 数据是不是真实查来的（不是编的）
- 有没有真正回答用户想问的

## 闲聊和打招呼

用户只是打个招呼或者纯闲聊，不用派任务。直接回：
ACCEPT: <友好的回复>

比如用户说"你好"，你就回：
ACCEPT: 你好呀！我是 Rovio，可以帮你查天气、看课表、写报告、处理文档，有什么需要吗？

## 记住
- 最多重试 1 次，第 2 次不管怎样都 ACCEPT
- 没有依赖关系的任务，大胆拆成多条 TASK 并行
- 你的活儿是选技能，别替执行伙伴操心该怎么干"""


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

    def _parse_supervisor_response(self, text: str) -> Dict[str, Any]:
        import re
        
        # 先检测 RETRY / ACCEPT（优先级高于 TASK）
        for keyword, action, key_name in [
            ("RETRY:", "retry", "feedback"),
            ("ACCEPT:", "accept", "final_answer"),
        ]:
            match = re.search(r"\b" + re.escape(keyword), text)
            if match:
                after = text[match.end():].strip()
                return {"action": action, key_name: after}

        # 兜底 RETRY / ACCEPT 不带冒号
        for keyword, action, key_name in [
            ("RETRY", "retry", "feedback"),
            ("ACCEPT", "accept", "final_answer"),
        ]:
            match = re.search(r"\b" + re.escape(keyword) + r"\b", text)
            if match:
                after = text[match.end():].strip().lstrip(":").strip()
                return {"action": action, key_name: after}
        
        # 查找所有 TASK: 行（支持单任务和多任务并行）
        task_pattern = r"TASK:\s*使用\s+(\w+)\s+技能[，,]?\s*为用户完成以下任务[：:]\s*(.+?)(?=\nTASK:|\nRETRY|\nACCEPT|\n\n\S|\Z)"
        task_matches = re.findall(task_pattern, text, re.DOTALL)
        
        if task_matches:
            tasks = []
            for skill_name, description in task_matches:
                tasks.append({
                    "skill": skill_name.strip(),
                    "description": description.strip().rstrip(".")
                })
            logger.info(f"[Supervisor] 解析到 {len(tasks)} 个并行任务: {[t['skill'] for t in tasks]}")
            return {"action": "delegate", "tasks": tasks}

        # 兜底：匹配不带冒号的 TASK（如 "TASK" 后跟换行的内容）
        match = re.search(r"\bTASK\b", text, re.IGNORECASE)
        if match:
            after = text[match.end():].strip().lstrip(":").strip()
            return {"action": "delegate", "task": after}
        
        # 兜底：如果 LLM 返回了类似"请提供xxx"的废话，通过 ACCEPT 返回给用户
        # 这种情况通常是 LLM 没有按格式输出 TASK/RETRY/ACCEPT
        logger.warning(f"[Supervisor] 解析失败，LLM 返回内容未被识别为 TASK/RETRY/ACCEPT: {text[:200]}")
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
        """构建完整 system prompt，含可用技能清单"""
        from AIRAGAgent.skills.base import SkillRegistry
        registry = SkillRegistry()
        skill_descriptions = registry.get_all_descriptions()
        return SUPERVISOR_SYSTEM_PROMPT + "\n\n" + skill_descriptions

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
        """执行工作智能体，thinking 进度直接透传，output 流式输出给用户"""
        output_parts = []
        for chunk in self.worker.execute_stream(task, chat_history):
            if isinstance(chunk, dict) and chunk["type"] == "output":
                output_parts.append(chunk["content"])
                yield chunk  # 流式输出，用户无需等待审查结束
            else:
                yield chunk
        return "".join(output_parts)

    def _run_single_worker(self, task_desc: str, chat_history: Optional[List[Dict[str, str]]]) -> tuple:
        """在线程中执行单个 worker 任务，使用独立 agent 实例保证线程安全"""
        # 每个并行 worker 创建独立的 agent，避免共享全局 agent 导致 stream 干扰
        worker = ReactAgent.create_standalone()
        thinking_chunks = []
        output_parts = []
        try:
            for chunk in worker.execute_stream(task_desc, chat_history):
                if isinstance(chunk, dict):
                    if chunk["type"] == "output":
                        output_parts.append(chunk["content"])
                    elif chunk["type"] == "thinking":
                        thinking_chunks.append(chunk)
            result = "".join(output_parts)
            logger.info(f"[Supervisor] 并行任务 [{task_desc[:30]}...] 完成，结果长度: {len(result)}")
            return (task_desc, result, thinking_chunks)
        except Exception as e:
            logger.error(f"[Supervisor] 并行任务 [{task_desc[:30]}...] 失败: {e}")
            return (task_desc, f"[执行失败: {e}]", thinking_chunks)

    def _execute_parallel_tasks(
        self,
        tasks: List[Dict[str, str]],
        chat_history: Optional[List[Dict[str, str]]] = None,
    ):
        """并行执行多个独立任务，yield 进度信息，最终 yield 合并结果"""
        task_count = len(tasks)
        yield {
            "type": "supervisor_action",
            "content": f"检测到 {task_count} 个独立子任务，并行执行中...",
        }

        # 捕获当前上下文（此时已通过上层 ctx.run 恢复 user_ip/lat/lon 等 ContextVar），
        # 为每个 worker 生成独立副本，避免 ThreadPoolExecutor 子线程拿不到 ContextVar 值，
        # 也避免多 worker 共用同一 Context 对象导致 set() 互相干扰。
        worker_contexts = [contextvars.copy_context() for _ in tasks]

        results = []
        with ThreadPoolExecutor(max_workers=min(task_count, 5)) as executor:
            futures = {}
            for i, t in enumerate(tasks):
                worker_ctx = worker_contexts[i]
                future = executor.submit(
                    lambda desc=t["description"], c=worker_ctx: c.run(
                        self._run_single_worker, desc, chat_history
                    )
                )
                futures[future] = (i, t)

            completed_count = 0
            for future in as_completed(futures):
                task_desc, result, thinking_chunks = future.result()
                idx, task_info = futures[future]
                completed_count += 1
                results.append((idx, result, task_info))

                yield {
                    "type": "supervisor_thinking",
                    "content": f"并行任务进度: {completed_count}/{task_count} 已完成",
                }

        # 按原始顺序排列结果
        results.sort(key=lambda x: x[0])

        # 合并结果
        merged_parts = []
        for i, (idx, result, task_info) in enumerate(results):
            skill_name = task_info.get("skill", "未知")
            merged_parts.append(f"### {skill_name} 技能结果\n{result.strip()}")

        merged_result = "\n\n".join(merged_parts)
        logger.info(f"[Supervisor] 并行任务全部完成，开始美化格式...")
        
        yield {
            "type": "supervisor_thinking",
            "content": "并行任务全部完成，正在整理结果...",
        }

        yield {"type": "output", "content": merged_result}

    def execute_stream(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None):
        logger.info(f"[Supervisor] 收到用户任务: {query[:100]}...")

        yield {"type": "supervisor_thinking", "content": "监督智能体正在分析任务需求..."}

        decision = self._supervisor_decide(query, chat_history=chat_history)

        if decision.get("action") != "delegate":
            # 流式输出：将回答按小段拆分，逐段推送
            answer = decision.get("final_answer", "")
            chunk_size = max(1, len(answer) // 20) if len(answer) > 20 else len(answer)
            for i in range(0, len(answer), chunk_size):
                yield {"type": "output", "content": answer[i:i + chunk_size]}
            return

        # ── 检测是否为并行多任务 ──
        tasks = decision.get("tasks")
        if tasks:
            if len(tasks) > 1:
                # 多任务并行模式
                yield from self._execute_parallel_tasks(tasks, chat_history)
                return
            else:
                # 单任务（从 tasks 列表中提取）
                worker_task = tasks[0]["description"]
        else:
            # ── 单任务模式（兼容旧逻辑）──
            worker_task = decision.get("task", query)
        yield {
            "type": "supervisor_action",
            "content": "任务已委派给工作智能体执行",
        }

        # yield thinking 进度，output 由 generator return 值收集
        worker_gen = self._yield_worker_chunks(worker_task, chat_history)
        while True:
            try:
                chunk = next(worker_gen)
                yield chunk
            except StopIteration as e:
                worker_result = e.value or ""
                break

        for retry_count in range(self.MAX_RETRIES + 1):
            yield {
                "type": "supervisor_thinking",
                "content": "监督智能体正在审查工作成果...",
            }

            review = self._supervisor_decide(query, worker_result, retry_count, chat_history)

            if review.get("action") == "accept":
                # 输出已经流式推送给用户了，审查通过后直接结束，不重复输出
                return

            if retry_count >= self.MAX_RETRIES:
                # 输出已经流式推送给用户了，即使审查不满意也接受当前结果
                return

            yield {
                "type": "supervisor_action",
                "content": f"工作成果需要改进：{review.get('feedback', '请重新执行')}",
            }

            # 重试：thinking 和 output 都透传给用户
            retry_gen = self._yield_worker_chunks(
                review.get("feedback", query), chat_history
            )
            while True:
                try:
                    chunk = next(retry_gen)
                    yield chunk
                except StopIteration as e:
                    worker_result = e.value or ""
                    break

    def execute(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        output_parts = []
        for chunk in self.execute_stream(query, chat_history):
            if isinstance(chunk, dict) and chunk["type"] == "output":
                output_parts.append(chunk["content"])
        return "".join(output_parts)
