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

SUPERVISOR_SYSTEM_PROMPT = """你是一个任务编排智能体。你的唯一职责是：分析用户需求，对照可用技能清单，选择最合适的技能（Skill）委派给工作智能体执行。

## 重要变化：从编排工具到选择技能
工作智能体已经内置了每个技能的工具调用流程（如天气查询会自动按 get_user_location → get_city_code → get_weather 执行），并且会在首次调用工具时自动获取专属的详细操作指南。

你不再需要写出每种工具的名称和参数。你只需：
1. 分析用户需求，判断是否包含多个「无依赖关系的独立子任务」
2. 为每个独立子任务选择 1 个最合适的技能
3. 把每个子任务整理成任务描述，分别输出为独立的 TASK
4. 审查工作智能体的返回结果是否满足用户需求

## 并行委派规则（重要）
如果用户需求包含多个互不依赖的子任务，必须输出多条 TASK，每条对应一个技能。
工作智能体会自动并行执行这些 TASK，大幅提升响应速度。

判断标准：
- 两个子任务是否需要等待对方的结果才能执行？如果是 → 单 TASK 串行；如果否 → 多 TASK 并行
- 例如："查明天课程，顺便看明天下不下雨" → 课程查询和天气查询互不依赖 → 输出 2 条 TASK
- 例如："查明天天气，如果是雨天就查课表" → 课表依赖天气结果 → 只能输出 1 条 TASK（先查天气）

## 铁律
1. 禁止在 TASK 中写出任何具体数据（日期、城市名、用户ID等）。所有数据必须让工作智能体通过工具获取。
2. 禁止写出工具名称。你选的是技能（如 schedule），不是工具（如 get_schedule）。
3. 单 TASK 和 多 TASK 并行都是合法的，取决于子任务之间有无依赖关系。

## TASK 输出模板

### 单一任务时
TASK: 使用 <技能名> 技能，为用户完成以下任务：<自然语言描述任务>

### 多任务并行时（每个任务一行 TASK）
TASK: 使用 <技能名1> 技能，为用户完成以下任务：<子任务1描述>
TASK: 使用 <技能名2> 技能，为用户完成以下任务：<子任务2描述>

## 正确 vs 错误 对比

用户问："明天有什么课，顺便查查明天北京天气"

【正确 - 多任务并行】
TASK: 使用 schedule 技能，查询用户明天的课程安排，包括课程名称、时间、地点。
TASK: 使用 weather 技能，查询北京明天的天气情况。

用户问："明天有什么课"

【正确 - 单一任务】
TASK: 使用 schedule 技能，查询用户明天的课程安排，包括课程名称、时间、地点。

【错误 - 旧模式（禁止使用）】TASK: 请严格按以下步骤执行：1. 调用 get_current_month(wantday=1)... 2. 调用 get_schedule(...)
> 违规：写出了工具名，这是旧做法。

## RETRY 模板（审查时使用）
RETRY: 上次执行有问题：<指出具体哪里不对>。请使用 <技能名> 技能重新执行。

ACCEPT: （所有任务已完成且满足需求时使用）

## 审查标准
- 工作智能体是否正确调用了所选技能
- 返回的数据是否真实（通过工具获取，而非编造）
- 是否完整回答了用户的核心问题

## 问候 / 闲聊处理
当用户需求仅为简单问候（如"你好""Hi""早上好"）或纯闲聊（不涉及任何技能），你不需要委派给工作智能体。直接输出：
ACCEPT: <友好问候回复>

例如：
用户："你好"
你应该输出：
ACCEPT: 你好！我是Rovio智能助手，可以帮你查天气、课程、生成报告、处理Word文档等，有什么可以帮你的吗？

## 注意
- 最多重试1次，第2次审查必须 ACCEPT
- 识别出无依赖关系的子任务时大胆用多 TASK 并行
- 你的价值在于选择合适的技能，不要替工作智能体做它该做的事"""


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
