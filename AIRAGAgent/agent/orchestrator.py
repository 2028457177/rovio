"""DeepAgent Orchestrator：规划-执行-反思 主循环。

替代旧的 SupervisorAgent + ReactAgent 两层结构，统一为：
    Planner  →  Executor  →  Reflector  →  Finalizer

核心特性：
1. Plan 作为一等公民：结构化产出 + 持久化 + 全程 SSE 推送
2. function calling：Planner / Reflector 用 with_structured_output 强制结构化
3. SubAgent 调度：每个 step 委派给合适的 SubAgent
4. 依赖感知：无依赖的 step 并行执行
5. 真反思：Reflector 可接受 / 重试 / 修订计划 / 问用户
6. 流式：所有 thinking / output 实时推给前端

SSE 事件协议（与旧协议兼容 + 新增 plan_*）：
    {"type": "thinking",        "content": "..."}            # 兼容旧
    {"type": "thinking_end",    "content": ""}               # 兼容旧
    {"type": "output",          "content": "..."}            # 兼容旧
    {"type": "plan_created",    "plan": {...}}               # 新
    {"type": "step_started",    "step_idx": 0, "subagent": "weather", "description": "..."}
    {"type": "step_thinking",   "step_idx": 0, "content": "..."}
    {"type": "step_output",     "step_idx": 0, "content": "..."}
    {"type": "step_completed",  "step_idx": 0, "success": true}
    {"type": "step_failed",     "step_idx": 0, "error": "..."}
    {"type": "plan_reflecting", "step_idx": 0, "action": "accept"}
    {"type": "plan_revised",    "plan": {...}}
    {"type": "plan_completed",  "plan": {...}}
    {"type": "ask_user",        "question": "..."}           # 需要用户补充信息
"""
from __future__ import annotations

import json
import contextvars
from pathlib import Path
from typing import List, Dict, Optional, Generator, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from AIRAGAgent.model.factory import chat_model, get_user_chat_model
from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.utils.prompt_loader import load_identity_prompts
from AIRAGAgent.agent.plan import (
    Plan, PlanStep, PlanStatus, StepStatus,
    create_plan, update_step_status, replace_plan_steps, update_plan_status,
)
from AIRAGAgent.agent.sub_agent import SubAgentRegistry, SubAgentRunner, run_steps_parallel
from AIRAGAgent.agent.tools.agent_tools import user_id_var
from AIRAGAgent.agent.tools.artifact_tools import (
    current_plan_id_var, current_session_id_var, current_step_idx_var,
)
from AIRAGAgent.utils.paths import get_daily_workspace


# ═══════════════════════════════════════════════
# 结构化输出 Schema（function calling）
# ═══════════════════════════════════════════════

class StepSpec(BaseModel):
    """Planner 产出的单个步骤规约。"""
    description: str = Field(description="自然语言描述这步要干什么，要足够具体让执行者知道怎么做")
    subagent: str = Field(
        description="由哪个 SubAgent 执行。纯闲聊/直接回答留空字符串。"
                    "必须从可用 SubAgent 清单里选 name"
    )
    depends_on: List[int] = Field(
        default_factory=list,
        description="依赖的 step_idx 列表（从0开始）。不依赖任何步骤则留空。"
                    "注意：只有真正需要等前一步结果时才加依赖，独立步骤不要加依赖以并行执行"
    )


class PlanSpec(BaseModel):
    """Planner 产出的完整计划。"""
    goal: str = Field(description="用户目标的简要重述，一句话")
    steps: List[StepSpec] = Field(description="执行步骤列表。简单的问候/闲聊/单点问答可以只给 1 步且 subagent 留空")


class Reflection(BaseModel):
    """Reflector 的评估结果。"""
    action: str = Field(
        description="accept(结果OK，继续) / retry(重试本步，带反馈) / "
                    "revise(需要修订整个计划) / ask_user(信息不足，需要问用户)"
    )
    feedback: str = Field(
        default="",
        description="retry/revise 时说明哪里不对、建议怎么改；ask_user 时写要问用户什么；accept 时留空"
    )


# ═══════════════════════════════════════════════
# Prompts
# ═══════════════════════════════════════════════

PLANNER_SYSTEM_PROMPT = """你是 Rovio 的任务规划器。你的活儿是：看清用户想干什么，拆成可执行的步骤，每步指定一个合适的 SubAgent。

## 拆分原则
1. 简单的问候、闲聊、单点问答 → 只给 1 步，subagent 留空字符串（让 Orchestrator 直接回答）
2. 需要调用工具的任务 → 按子任务拆步，每步指定 SubAgent
3. 两个子任务互不依赖 → 不要加 depends_on，让它们并行
4. 后一步需要前一步的结果 → 加 depends_on（前一步的 step_idx）
5. 步数尽量少，3 步以内能搞定的别拆成 5 步

## 选 SubAgent 的原则
- 只能从下面"可用 SubAgent 清单"里选 name，不要编造
- 不知道选哪个时，优先选最贴切的；实在贴不上就留空让 Orchestrator 自己回答

## description 写法
- 用自然语言把这一步要干什么说清楚
- 不要写具体参数（日期、城市名等），让 SubAgent 自己去查
- 不要写工具名，SubAgent 自己知道该调什么工具

## 特殊场景
- 用户问"明天有什么课，顺便查天气" → 2 步并行：schedule + weather
- 用户问"帮我写本月工作报告" → 1 步：report
- 用户问"你好" → 1 步，subagent 留空
- 用户问"什么是 RAG" → 1 步，subagent 留空（直接回答）或 knowledge（要查知识库）
- 用户说"给 XX 网页/网址截图" → 1 步：browser（用 screenshot_url 工具，**不要选 codexec**）
- 用户说"生成/做一个 Word 文档/报告/调研报告（.docx）" → 末步用 wordgen（**生成 Word 一律选 wordgen，不要选 codexec**）；若需先联网查资料，则拆成 search/browser → wordgen 两步
- 用户说"截个屏"（指本机屏幕） → 1 步：desktop（用 screenshot 工具）
- 用户说"给本地某文件截图" → 1 步：desktop（用 screenshot 工具）
"""

REFLECTOR_SYSTEM_PROMPT = """你是 Rovio 的执行审查员。每一步执行完后，由你判断结果是否满足用户需求。

## 判断维度
1. 这一步是否真的完成了它应该做的事
2. 结果是否真实（不是编造的）
3. 结果是否足以支撑下一步 / 最终回答

## 决策
- accept：结果OK，继续下一步
- retry：结果有问题但本步该换种方式重试（在 feedback 里说清楚哪里不对、建议怎么做）
- revise：本步暴露了原计划的问题，需要重新规划（在 feedback 里说清楚新计划该怎么改）
- ask_user：信息严重不足，需要问用户（在 feedback 里写要问什么）

## 注意
- 大多数情况应该是 accept，只有真的有问题才 retry/revise
- retry 最多 1 次，第 2 次不管怎样都 accept
- 不要因为"结果可以更好"就 retry，只关心"是否满足需求"
"""

FINALIZER_SYSTEM_PROMPT = """你是 Rovio。前面的步骤已经执行完毕，现在你需要基于执行结果给用户一个完整、自然的回答。

要求：
1. 把各步骤的结果整合成一段连贯的回复
2. 用用户的语言（中文/英文）和语气
3. 不要重复"根据步骤1...步骤2..."这种元叙述，直接给答案
4. 如果有失败/未完成的步骤，老实告诉用户哪里没搞定
5. 简洁为主，能列点就列点，不要写大段文字
"""

# ── 结构化输出指令（纯文本 JSON，兼容 DeepSeek thinking 模式，不用 function calling）──
PLANNER_JSON_INSTRUCTION = """

## 输出格式
严格输出如下 JSON（只输出 JSON 本身，不要 markdown 代码块、不要解释）：
{"goal": "用户目标一句话重述", "steps": [{"description": "步骤描述", "subagent": "SubAgent名称或空字符串", "depends_on": []}]}
"""

REFLECTOR_JSON_INSTRUCTION = """

## 输出格式
严格输出如下 JSON（只输出 JSON 本身，不要 markdown 代码块、不要解释）：
{"action": "accept或retry或revise或ask_user", "feedback": "反馈说明"}
"""


def _extract_json(text: str) -> str:
    """从 LLM 文本响应中提取 JSON 字符串。

    兼容三种情况：纯 JSON、```json ... ``` 包裹、前后有解释文字。
    """
    text = text.strip()
    # 去除 markdown code fence
    if text.startswith("```"):
        lines = text.split("\n")
        # 去首行 ```json 和末行 ```
        start = 1
        end = len(lines)
        if lines[-1].strip().startswith("```"):
            end = len(lines) - 1
        text = "\n".join(lines[start:end]).strip()
    # 找第一个 { 到最后一个 } 之间的内容
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return text[first:last + 1]
    return text


# ═══════════════════════════════════════════════
# Orchestrator 主类
# ═══════════════════════════════════════════════

class Orchestrator:
    """DeepAgent 主循环：Planner → Executor → Reflector → Finalizer。"""

    MAX_REVISIONS = 2     # 最多修订计划次数
    MAX_RETRIES = 1       # 单步最多重试次数

    def __init__(self):
        # 触发 SubAgent 注册（幂等）
        from AIRAGAgent.agent.sub_agents import register_all_subagents
        register_all_subagents()
        self.registry = SubAgentRegistry()
        self.llm = chat_model

    def _llm_for(self, user_id: int):
        """解析当前用户的对话模型：用户自配模型优先，否则系统默认。"""
        return get_user_chat_model(user_id)

    # ────────────────────────────────────────
    # 工具方法
    # ────────────────────────────────────────

    @staticmethod
    def _format_history(chat_history: Optional[List[Dict[str, str]]]) -> str:
        if not chat_history:
            return ""
        lines = ["## 对话历史（最近几条）"]
        recent = chat_history[-6:]  # 最近 6 条避免过长
        for entry in recent:
            role = "用户" if entry.get("role") == "user" else "助手"
            lines.append(f"- {role}: {entry.get('content', '')[:200]}")
        return "\n".join(lines) + "\n---\n"

    def _get_subagent_menu(self) -> str:
        return self.registry.descriptions_for_planner()

    @staticmethod
    def _recall_relevant_memory(user_id: int, query: str) -> str:
        """召回与用户查询相关的长期记忆，注入 Planner 上下文。"""
        try:
            from AIRAGAgent.database import recall_memories
            rows = recall_memories(user_id, limit=10)
            if not rows:
                return ""
            lines = ["## 关于该用户的长期记忆（可能影响规划）"]
            for r in rows:
                lines.append(f"- [{r['type']}] {r['key']}: {r['value']}")
            return "\n".join(lines) + "\n---\n"
        except Exception as e:
            logger.debug(f"[Orchestrator] 召回记忆失败（忽略）: {e}")
            return ""

    # ────────────────────────────────────────
    # Planner
    # ────────────────────────────────────────

    def _plan(self, query: str, chat_history: Optional[List[Dict[str, str]]],
              user_id: int, extra_hint: str = "") -> Optional[PlanSpec]:
        """调用 Planner LLM 产出结构化 PlanSpec。失败时返回 None。

        用纯文本 JSON 输出 + 解析，不用 with_structured_output（function calling），
        因为 DeepSeek thinking 模式不支持 tool_choice。
        """
        history_ctx = self._format_history(chat_history)
        memory_ctx = self._recall_relevant_memory(user_id, query)
        menu = self._get_subagent_menu()
        llm = self._llm_for(user_id)

        system = PLANNER_SYSTEM_PROMPT + "\n\n" + menu + PLANNER_JSON_INSTRUCTION
        user_msg = (
            f"用户需求：\n{query}\n\n"
            f"{history_ctx}"
            f"{memory_ctx}"
            f"{extra_hint}"
            f"请制定执行计划。如果这是简单问候或闲聊，给 1 步且 subagent 留空。"
        )

        try:
            resp = llm.invoke([
                SystemMessage(content=system),
                HumanMessage(content=user_msg),
            ])
            raw = getattr(resp, "content", "") or str(resp)
            # DeepSeek thinking 模式可能把 JSON 放在 content 里，也可能有 reasoning_content
            json_str = _extract_json(raw)
            data = json.loads(json_str)
            spec = PlanSpec(**data)
            logger.info(f"[Planner] 产出计划：goal={spec.goal!r}, steps={len(spec.steps)}")
            for i, s in enumerate(spec.steps):
                logger.info(f"[Planner]   step {i}: subagent={s.subagent!r}, deps={s.depends_on}, desc={s.description[:60]}")
            return spec
        except Exception as e:
            logger.error(f"[Planner] 规划失败，回退到单步直接回答: {e}")
            return None

    def _plan_stream(self, query: str, chat_history: Optional[List[Dict[str, str]]],
                     user_id: int, extra_hint: str = "") -> Optional[PlanSpec]:
        """流式版 Planner：把 LLM 的 reasoning_content（思考过程）流式 yield 出去，
        最后解析 JSON 产出 PlanSpec。

        用流式调用让前端能在"正在分析任务..."面板里看到 Planner 的真实推理过程。
        """
        history_ctx = self._format_history(chat_history)
        memory_ctx = self._recall_relevant_memory(user_id, query)
        menu = self._get_subagent_menu()
        llm = self._llm_for(user_id)

        system = PLANNER_SYSTEM_PROMPT + "\n\n" + menu + PLANNER_JSON_INSTRUCTION
        user_msg = (
            f"用户需求：\n{query}\n\n"
            f"{history_ctx}"
            f"{memory_ctx}"
            f"{extra_hint}"
            f"请制定执行计划。如果这是简单问候或闲聊，给 1 步且 subagent 留空。"
        )

        try:
            full_content = ""
            full_reasoning = ""
            for chunk in llm.stream([
                SystemMessage(content=system),
                HumanMessage(content=user_msg),
            ]):
                text = getattr(chunk, "content", "") or ""
                reasoning = ""
                if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
                    reasoning = chunk.additional_kwargs.get("reasoning_content", "") or ""
                if reasoning:
                    full_reasoning += reasoning
                    # 流式推送思考过程给前端
                    yield {"type": "thinking", "content": reasoning}
                if text:
                    full_content += text
            # 解析最终 JSON
            json_str = _extract_json(full_content)
            data = json.loads(json_str)
            spec = PlanSpec(**data)
            logger.info(f"[Planner] 产出计划：goal={spec.goal!r}, steps={len(spec.steps)}, "
                        f"reasoning_len={len(full_reasoning)}")
            for i, s in enumerate(spec.steps):
                logger.info(f"[Planner]   step {i}: subagent={s.subagent!r}, deps={s.depends_on}, desc={s.description[:60]}")
            return spec
        except Exception as e:
            logger.error(f"[Planner] 规划失败，回退到单步直接回答: {e}")
            return None

    def _build_plan(self, spec: PlanSpec, user_id: int, session_id: str) -> Plan:
        """把 PlanSpec 转成持久化的 Plan。"""
        steps = [
            PlanStep(
                step_idx=i,
                description=s.description,
                subagent=s.subagent or "",
                depends_on=list(s.depends_on or []),
            )
            for i, s in enumerate(spec.steps)
        ]
        # 如果 Planner 返回空 steps（不该发生但兜底），加一个直接回答的 step
        if not steps:
            steps = [PlanStep(step_idx=0, description=spec.goal or "直接回答用户", subagent="")]
        return create_plan(user_id, session_id, spec.goal, steps)

    # ────────────────────────────────────────
    # Executor
    # ────────────────────────────────────────

    def _execute_step(self, plan: Plan, step: PlanStep,
                      chat_history: Optional[List[Dict[str, str]]],
                      feedback: str = "",
                      query: str = "") -> Generator[dict, None, str]:
        """执行单个 step，流式产出事件，返回累积 output 文本。

        如果 step.subagent 为空，直接用 LLM 回答；否则委派 SubAgent。
        query 为用户原始问题，直接回答路径用它（而不是 step.description），
        避免 Planner 改写后语义偏移 + 历史复述。
        """
        # 注入 artifact ContextVar，让 create_artifact 能关联到当前 step
        token_plan = current_plan_id_var.set(plan.id)
        token_session = current_session_id_var.set(plan.session_id)
        token_step = current_step_idx_var.set(step.step_idx)

        update_step_status(plan.id, step.step_idx, StepStatus.RUNNING.value,
                           increment_attempts=bool(feedback))

        llm = self._llm_for(plan.user_id)
        subagent_name = step.subagent or ""
        task_desc = step.description if not feedback else f"{step.description}\n\n上次执行有问题，反馈：{feedback}"
        # 注入前序步骤结果（文件路径 + 摘要），修复跨步骤数据交接断点
        task_desc += self._build_step_context(plan, exclude={step.step_idx})

        yield {
            "type": "step_started",
            "step_idx": step.step_idx,
            "subagent": subagent_name or "(orchestrator)",
            "description": step.description,
        }

        output_parts: List[str] = []

        try:
            if not subagent_name:
                # 直接由 Orchestrator LLM 回答（纯闲聊 / 通用问答）
                # 单步 plan 时用前端兼容的 thinking/output 事件类型，让前端能实时流式显示
                is_single_step = len(plan.steps) == 1
                think_type = "thinking" if is_single_step else "step_thinking"
                out_type = "output" if is_single_step else "step_output"
                yield {"type": think_type, "step_idx": step.step_idx,
                       "content": "直接回答用户"}
                identity = load_identity_prompts()
                history_msgs = self._history_to_messages(chat_history)
                # 用原始 query 而不是 step.description（Planner 改写会偏语义）；
                # 多步 plan 的 finalize 阶段用 task_desc（含反馈信息）
                user_content = query if (is_single_step and query) else task_desc
                # 用 stream 真流式
                stream = llm.stream(
                    [SystemMessage(content=identity)] + history_msgs + [HumanMessage(content=user_content)]
                )
                for chunk in stream:
                    text = getattr(chunk, "content", "") or ""
                    reasoning = ""
                    if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
                        reasoning = chunk.additional_kwargs.get("reasoning_content", "") or ""
                    if reasoning and not text:
                        yield {"type": think_type, "step_idx": step.step_idx, "content": reasoning}
                    if text:
                        output_parts.append(text)
                        yield {"type": out_type, "step_idx": step.step_idx, "content": text}
            else:
                # 委派 SubAgent
                sub = self.registry.get(subagent_name)
                if sub is None:
                    err = f"未知 SubAgent: {subagent_name}"
                    yield {"type": "step_failed", "step_idx": step.step_idx, "error": err}
                    update_step_status(plan.id, step.step_idx, StepStatus.FAILED.value, error_msg=err)
                    current_plan_id_var.reset(token_plan)
                    current_session_id_var.reset(token_session)
                    current_step_idx_var.reset(token_step)
                    return ""
                runner = SubAgentRunner(sub, llm=llm)
                for chunk in runner.execute_stream(task_desc, chat_history):
                    if not isinstance(chunk, dict):
                        continue
                    ctype = chunk.get("type")
                    content = chunk.get("content", "")
                    if ctype == "output":
                        output_parts.append(content)
                        yield {"type": "step_output", "step_idx": step.step_idx, "content": content}
                    elif ctype in ("thinking", "thinking_end"):
                        yield {"type": "step_thinking", "step_idx": step.step_idx, "content": content}

            result_text = "".join(output_parts)
            update_step_status(plan.id, step.step_idx, StepStatus.COMPLETED.value, result=result_text[:65000])
            step.status = StepStatus.COMPLETED.value
            step.result = result_text
            self._save_step_result(plan, step)
            yield {"type": "step_completed", "step_idx": step.step_idx, "success": True}
        except Exception as e:
            logger.error(f"[Executor] step {step.step_idx} 失败: {e}", exc_info=True)
            update_step_status(plan.id, step.step_idx, StepStatus.FAILED.value, error_msg=str(e))
            step.status = StepStatus.FAILED.value
            yield {"type": "step_failed", "step_idx": step.step_idx, "error": str(e)}
            result_text = ""
        finally:
            current_plan_id_var.reset(token_plan)
            current_session_id_var.reset(token_session)
            current_step_idx_var.reset(token_step)

        return result_text

    def _execute_steps_parallel(self, plan: Plan, steps: List[PlanStep],
                                chat_history: Optional[List[Dict[str, str]]]) -> Generator[dict, None, None]:
        """并行执行多个独立 step（无 subagent 的 step 不参与并行，留到串行处理）。"""
        # 标记 running
        for s in steps:
            update_step_status(plan.id, s.step_idx, StepStatus.RUNNING.value)

        # 注入 artifact ContextVar（用 plan 级别，step_idx 留空）
        token_plan = current_plan_id_var.set(plan.id)
        token_session = current_session_id_var.set(plan.session_id)

        # 所有 step 都有 subagent 才走并行路径；混有无 subagent 的退化为串行
        if all(s.subagent for s in steps):
            yield {"type": "step_started", "step_idx": -1,
                   "subagent": "parallel", "description": f"并行执行 {len(steps)} 个步骤"}
            batch_indices = {s.step_idx for s in steps}
            specs = []
            for s in steps:
                # 并行批次内互相独立，只注入批次之前已完成步骤的结果上下文
                ctx = self._build_step_context(plan, exclude=batch_indices)
                specs.append({"step_idx": s.step_idx, "subagent": s.subagent,
                              "description": s.description + ctx})
            try:
                results = run_steps_parallel(specs, chat_history,
                                             llm=self._llm_for(plan.user_id))
            finally:
                current_plan_id_var.reset(token_plan)
                current_session_id_var.reset(token_session)

            for r in results:
                idx = r["step_idx"]
                step = plan.get_step(idx)
                if step is None:
                    continue
                if r["success"]:
                    update_step_status(plan.id, idx, StepStatus.COMPLETED.value, result=r["result"][:65000])
                    step.status = StepStatus.COMPLETED.value
                    step.result = r["result"]
                    self._save_step_result(plan, step)
                    yield {"type": "step_output", "step_idx": idx, "content": r["result"]}
                    yield {"type": "step_completed", "step_idx": idx, "success": True}
                else:
                    update_step_status(plan.id, idx, StepStatus.FAILED.value, error_msg=r["result"][:1000])
                    step.status = StepStatus.FAILED.value
                    yield {"type": "step_failed", "step_idx": idx, "error": r["result"]}
        else:
            # 退化为串行
            current_plan_id_var.reset(token_plan)
            current_session_id_var.reset(token_session)
            for s in steps:
                yield from self._execute_step(plan, s, chat_history)

    # ────────────────────────────────────────
    # 跨步骤数据交接：plan_results 落盘 + 下游上下文注入
    # ────────────────────────────────────────

    def _plan_results_dir(self, plan: Plan) -> Path:
        """每个计划独立的步骤结果目录（位于计划专属目录 tasks/<plan_id>/ 下，
        codexec 子进程 cwd 即该目录，可直接相对路径读取）。"""
        return get_daily_workspace(plan.user_id) / "tasks" / plan.id / "plan_results"

    def _save_step_result(self, plan: Plan, step: PlanStep) -> str:
        """把步骤结果落盘到 plan_results/<plan_id>/step_<idx>.md，返回相对路径（失败返回空串）。

        解决长任务断点：search/artifact 等非 codexec 步骤的结果此前只进 DB，
        下游步骤拿不到；落盘后任何子代理（尤其 codexec，其 cwd 即用户当天工作区）都能读取。
        """
        try:
            d = self._plan_results_dir(plan)
            d.mkdir(parents=True, exist_ok=True)
            f = d / f"step_{step.step_idx}.md"
            header = (f"# 步骤 {step.step_idx}（SubAgent: {step.subagent or 'orchestrator'}）\n"
                      f"任务：{step.description}\n\n")
            f.write_text(header + (step.result or "(无结果)"), encoding="utf-8")
            return f"plan_results/{plan.id}/step_{step.step_idx}.md"
        except Exception as e:
            logger.warning(f"[Handoff] 保存步骤 {step.step_idx} 结果失败: {e}")
            return ""

    def _build_step_context(self, plan: Plan, exclude: set) -> str:
        """构造下游步骤可见的前序步骤结果上下文（文件路径 + 摘要）。

        exclude 为本次并行批次内的 step_idx（并行步骤彼此独立，不应互相引用）。
        """
        completed = [s for s in plan.steps
                     if s.status == StepStatus.COMPLETED.value
                     and s.step_idx not in exclude and s.result]
        if not completed:
            return ""
        lines = [
            "\n\n## 前序步骤结果（可直接使用）",
            "以下步骤已执行完成，完整结果已保存到本计划专属目录 tasks/<计划ID>/plan_results/ 下。"
            "请优先读取对应文件获取完整数据（代码执行子进程的当前目录就是 tasks/<计划ID>/，"
            "用相对路径 plan_results/step_<编号>.md 即可），不要凭印象编造；"
            "禁止读取或扫描工作区里其他计划/其他任务的目录（如 ai_coding_tools/、data_pipeline/ 等），"
            "那些与本任务无关：",
        ]
        for s in completed:
            rel = f"plan_results/{plan.id}/step_{s.step_idx}.md"
            abs_path = self._plan_results_dir(plan) / f"step_{s.step_idx}.md"
            summary = (s.result or "").strip().replace("\n", " ")
            if len(summary) > 200:
                summary = summary[:200] + "..."
            lines.append(f"- 步骤 {s.step_idx}（{s.subagent or 'orchestrator'}）结果文件：{abs_path}"
                         f"（相对路径 {rel}）；摘要：{summary}")
        return "\n".join(lines)

    @staticmethod
    def _history_to_messages(chat_history: Optional[List[Dict[str, str]]]) -> list:
        msgs = []
        if not chat_history:
            return msgs
        for entry in chat_history[-6:]:
            role = entry.get("role", "")
            content = entry.get("content", "")
            if role == "user":
                msgs.append(HumanMessage(content=content))
            elif role == "assistant":
                msgs.append(AIMessage(content=content))
        return msgs

    # ────────────────────────────────────────
    # Reflector
    # ────────────────────────────────────────

    def _reflect(self, plan: Plan, step: PlanStep, query: str,
                 chat_history: Optional[List[Dict[str, str]]]) -> Optional[Reflection]:
        """评估单个 step 的结果。"""
        # 不反思直接回答步（subagent 为空）和已完成无失败的步
        if not step.subagent:
            return Reflection(action="accept")
        if step.status == StepStatus.FAILED.value:
            # 失败步：如果还有重试机会就 retry，否则 accept（避免死循环）
            if step.attempts <= self.MAX_RETRIES:
                return Reflection(action="retry", feedback=f"上次执行失败：{step.error_msg}。请换种方式重试。")
            return Reflection(action="accept")

        try:
            history_ctx = self._format_history(chat_history)
            system = REFLECTOR_SYSTEM_PROMPT + REFLECTOR_JSON_INSTRUCTION
            user_msg = (
                f"用户原始需求：\n{query}\n\n"
                f"{history_ctx}"
                f"步骤 {step.step_idx}（SubAgent: {step.subagent}）执行结果：\n{step.result[:2000]}\n\n"
                f"请评估此结果是否满足该步骤的目标。"
            )
            resp = self._llm_for(plan.user_id).invoke([
                SystemMessage(content=system),
                HumanMessage(content=user_msg),
            ])
            raw = getattr(resp, "content", "") or str(resp)
            json_str = _extract_json(raw)
            data = json.loads(json_str)
            ref = Reflection(**data)
            logger.info(f"[Reflector] step {step.step_idx} action={ref.action} feedback={ref.feedback[:100]}")
            return ref
        except Exception as e:
            logger.error(f"[Reflector] 评估失败，默认 accept: {e}")
            return Reflection(action="accept")

    def _revise_plan(self, plan: Plan, query: str,
                     chat_history: Optional[List[Dict[str, str]]],
                     feedback: str) -> Generator[dict, None, Optional[PlanSpec]]:
        """根据反馈重新规划，替换 plan.steps。"""
        yield {"type": "plan_reflecting", "step_idx": -1, "action": "revise", "feedback": feedback}
        hint = f"上一版计划执行中发现问题，需要修订：\n{feedback}\n\n请基于此修订计划。\n"
        spec = self._plan(query, chat_history, plan.user_id, extra_hint=hint)
        if spec is None:
            yield {"type": "plan_reflecting", "step_idx": -1, "action": "revise_failed"}
            return None
        new_steps = [
            PlanStep(
                step_idx=i,
                description=s.description,
                subagent=s.subagent or "",
                depends_on=list(s.depends_on or []),
            )
            for i, s in enumerate(spec.steps)
        ]
        if not new_steps:
            new_steps = [PlanStep(step_idx=0, description=spec.goal or "直接回答", subagent="")]
        replace_plan_steps(plan.id, new_steps)
        plan.steps = new_steps
        # 重置 plan 状态为 executing
        plan.status = PlanStatus.EXECUTING.value
        update_plan_status(plan.id, PlanStatus.EXECUTING.value)
        yield {"type": "plan_revised", "plan": plan.to_dict()}
        return spec

    # ────────────────────────────────────────
    # Finalizer
    # ────────────────────────────────────────

    def _finalize(self, plan: Plan, query: str,
                  chat_history: Optional[List[Dict[str, str]]]) -> Generator[dict, None, str]:
        """汇总所有步骤结果，流式产出最终回答。"""
        # 如果只有 1 步且 subagent 为空（直接回答），step.result 已经是最终答案，不再二次处理
        if len(plan.steps) == 1 and not plan.steps[0].subagent and plan.steps[0].result:
            update_plan_status(plan.id, PlanStatus.COMPLETED.value, final_answer=plan.steps[0].result)
            # output 已在 _execute_step 中流式推送过，这里不重复推
            return plan.steps[0].result

        # 多步：让 LLM 整合
        yield {"type": "thinking", "content": "\n正在整理最终答案...\n"}

        # 检查所有 step 是否都成功
        all_success = all(s.status == StepStatus.COMPLETED.value for s in plan.steps)
        if not all_success and not any(s.status == StepStatus.COMPLETED.value for s in plan.steps):
            # 全失败
            fail_msg = "所有步骤都执行失败了，请稍后重试或换个问法。"
            update_plan_status(plan.id, PlanStatus.FAILED.value, final_answer=fail_msg)
            yield {"type": "output", "content": fail_msg}
            return fail_msg

        # 拼接各步结果给 Finalizer
        results_summary = []
        for s in plan.steps:
            status_label = "✓" if s.status == StepStatus.COMPLETED.value else "✗"
            results_summary.append(
                f"### 步骤 {s.step_idx}（SubAgent: {s.subagent or 'orchestrator'}）[{status_label}]\n"
                f"任务：{s.description}\n"
                f"结果：{s.result[:1500] if s.result else '(无结果)'}"
            )
        results_text = "\n\n".join(results_summary)

        history_ctx = self._format_history(chat_history)
        system = FINALIZER_SYSTEM_PROMPT
        user_msg = (
            f"用户原始需求：\n{query}\n\n"
            f"{history_ctx}"
            f"各步骤执行结果：\n{results_text}\n\n"
            f"请基于以上结果给用户一个完整、自然的回答。"
        )

        output_parts: List[str] = []
        try:
            stream = self._llm_for(plan.user_id).stream([
                SystemMessage(content=system),
                HumanMessage(content=user_msg),
            ])
            for chunk in stream:
                text = getattr(chunk, "content", "") or ""
                reasoning = ""
                if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
                    reasoning = chunk.additional_kwargs.get("reasoning_content", "") or ""
                if reasoning and not text:
                    yield {"type": "thinking", "content": reasoning}
                if text:
                    output_parts.append(text)
                    yield {"type": "output", "content": text}
        except Exception as e:
            logger.error(f"[Finalizer] 流式失败，回退到一次性输出: {e}")
            # 回退：直接拼接各步结果
            fallback = "\n\n".join(s.result for s in plan.steps if s.result)
            if not fallback:
                fallback = "处理完成，但没有可输出的内容。"
            output_parts.append(fallback)
            yield {"type": "output", "content": fallback}

        final_text = "".join(output_parts)
        update_plan_status(plan.id, PlanStatus.COMPLETED.value, final_answer=final_text[:65000])
        return final_text

    # ────────────────────────────────────────
    # 主循环
    # ────────────────────────────────────────

    def execute_stream(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None,
                      user_id: int = 0, session_id: str = "") -> Generator[dict, None, None]:
        """DeepAgent 主循环入口。流式产出 SSE 事件。

        Args:
            query: 用户输入
            chat_history: 会话历史 [{"role": "user"/"assistant", "content": "..."}]
            user_id: 当前用户 ID（用于记忆召回 + plan 持久化归属）
            session_id: 会话 ID（用于 plan 关联会话）
        """
        logger.info(f"[Orchestrator] 收到任务: {query[:100]!r} user={user_id} session={session_id}")

        # ── 1. 规划 ──
        yield {"type": "thinking", "content": "正在分析任务并制定执行计划...\n\n"}
        # _plan_stream 是 generator：流式 yield thinking 事件，返回 PlanSpec
        plan_gen = self._plan_stream(query, chat_history, user_id)
        spec = None
        try:
            while True:
                chunk = next(plan_gen)
                if isinstance(chunk, dict):
                    yield chunk
        except StopIteration as e:
            spec = e.value
        if spec is None:
            # Planner 失败，走单步直接回答
            spec = PlanSpec(goal=query, steps=[StepSpec(description=query, subagent="")])
        plan = self._build_plan(spec, user_id, session_id)
        update_plan_status(plan.id, PlanStatus.EXECUTING.value)
        yield {"type": "thinking_end"}
        yield {"type": "plan_created", "plan": plan.to_dict()}

        # ── 2. 执行 + 反思 ──
        revision_count = 0
        try:
            while not plan.is_all_done():
                ready = plan.get_ready_steps()
                if not ready:
                    # 没有可执行的 step（可能全 blocked），退出
                    logger.warning(f"[Orchestrator] plan {plan.id} 没有可执行步骤，剩余状态: "
                                   f"{[(s.step_idx, s.status) for s in plan.steps]}")
                    break

                # 持久化 blocked 状态
                for s in plan.steps:
                    if s.status == StepStatus.BLOCKED.value:
                        update_step_status(plan.id, s.step_idx, StepStatus.BLOCKED.value,
                                           error_msg=s.error_msg)

                # 执行 ready 步骤
                if len(ready) == 1:
                    # 串行执行 + 流式
                    step = ready[0]
                    yield from self._execute_step(plan, step, chat_history)
                    # 反思
                    ref = self._reflect(plan, step, query, chat_history)
                    if ref:
                        yield {"type": "plan_reflecting", "step_idx": step.step_idx,
                               "action": ref.action, "feedback": ref.feedback}
                        if ref.action == "retry" and step.attempts <= self.MAX_RETRIES:
                            yield from self._execute_step(plan, step, chat_history, feedback=ref.feedback)
                        elif ref.action == "revise" and revision_count < self.MAX_REVISIONS:
                            revision_count += 1
                            new_spec = yield from self._revise_plan(plan, query, chat_history, ref.feedback)
                            if new_spec is not None:
                                continue  # 重新进入 while 循环
                        elif ref.action == "ask_user":
                            yield {"type": "ask_user", "question": ref.feedback}
                            update_plan_status(plan.id, PlanStatus.COMPLETED.value,
                                               final_answer=f"需要用户补充信息：{ref.feedback}")
                            return
                else:
                    # 并行执行
                    yield from self._execute_steps_parallel(plan, ready, chat_history)
                    # 并行 step 不逐个反思（太慢），整体反思失败的 step
                    for step in ready:
                        if step.status == StepStatus.FAILED.value and step.attempts <= self.MAX_RETRIES:
                            yield {"type": "plan_reflecting", "step_idx": step.step_idx,
                                   "action": "retry", "feedback": "并行任务失败，重试一次"}
                            yield from self._execute_step(plan, step, chat_history, feedback="重试")

        except Exception as e:
            logger.error(f"[Orchestrator] 主循环异常: {e}", exc_info=True)
            yield {"type": "thinking", "content": f"\n执行过程出错：{e}\n"}
            update_plan_status(plan.id, PlanStatus.FAILED.value, final_answer=f"执行出错：{e}")
            yield {"type": "output", "content": f"抱歉，执行过程中遇到问题：{e}"}
            return

        # ── 3. 汇总最终答案 ──
        final_text = yield from self._finalize(plan, query, chat_history)
        yield {"type": "plan_completed", "plan": plan.to_dict()}
        logger.info(f"[Orchestrator] plan {plan.id} 完成，final_answer 长度={len(final_text)}")

    def execute(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None,
                user_id: int = 0, session_id: str = "") -> str:
        """同步执行，收集所有 output 拼接返回（兼容旧 execute 接口）。"""
        parts = []
        for chunk in self.execute_stream(query, chat_history, user_id, session_id):
            if isinstance(chunk, dict) and chunk.get("type") == "output":
                parts.append(chunk.get("content", ""))
        return "".join(parts)


# ═══════════════════════════════════════════════
# 单例
# ═══════════════════════════════════════════════

_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
