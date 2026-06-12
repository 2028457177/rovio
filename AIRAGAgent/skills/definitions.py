"""
各领域 Skill 定义

将原有的原子工具按领域分组，每个 Skill 封装相关的工具 + 专属 system prompt。
Skill 激活后，其 system prompt 会被注入到 worker 的上下文中。
"""
from AIRAGAgent.skills.base import Skill, SkillRegistry

# ── 导入所有原始工具函数 ──
from AIRAGAgent.agent.tools.agent_tools import (
    rag_summarize,
    get_weather,
    get_user_location,
    get_city_code,
    get_user_id,
    get_current_month,
    fetch_external_data,
    fill_context_for_report,
    get_schedule,
)
from AIRAGAgent.agent.tools.file_tools import auto_fill_word
from AIRAGAgent.agent.tools.search_tools import search
from AIRAGAgent.agent.tools.wx_tools import send_wx_message


# ═══════════════════════════════════════════════
# 各 Skill 的领域 System Prompt
# ═══════════════════════════════════════════════

WEATHER_SKILL_PROMPT = """你正在执行【天气查询】任务。
**重要**：直接输出天气数据，禁止输出内部推理过程。

## 工具流程
1. get_user_location() → 获取用户省市
2. get_city_code(city_name) → 提取纯城市名
3. get_weather(city_name) → 获取天气预报

## 规则
- 用户已说城市名时跳过步骤1
- 如实展示，不编造数据

## 输出
仅返回用户关心的天气数据（日期、天气、温度、风力），一行一条，不加多余解释。"""


SCHEDULE_SKILL_PROMPT = """你正在执行【课表/日程查询】任务。
**重要**：直接输出课程数据，禁止输出内部推理过程。

## 工具流程
1. get_current_month(wantday) → 获取日期/周次/星期
2. get_schedule(week, day) → 查询课程

## 规则
- 必须用 get_current_month 获取准确值，不自推算
- 如实展示课表

## 输出
列出课程名、时间、节次、地点。无课则一句话说明。不加多余分析。"""


REPORT_SKILL_PROMPT = """你正在执行【工作报告生成】任务。

## 工具流程（严格顺序）
1. get_user_id()
2. fill_context_for_report()
3. 确定月份（用户指定或用 get_current_month(0)）
4. fetch_external_data(user_id, month)

## 规则
- fill_context_for_report 不可跳过
- 按"特征、效率、耗材、对比"四维度整理
- 无数据则直接告知

## 输出
结构化列出四维度数据，各维度一行总结。"""


KNOWLEDGE_SKILL_PROMPT = """你正在执行【知识库检索】任务。

## 工具
rag_summarize(query) — query 用核心关键词

## 输出
检索结果 + 简明实用建议，不展开无关知识点。"""


DOCUMENT_SKILL_PROMPT = """你正在执行【文档处理】任务。

## 工具
auto_fill_word(template_path)

## 规则
template_path 为用户上传后的服务器文件路径。

## 输出
告知处理完成，附下载链接。"""


COMMUNICATION_SKILL_PROMPT = """你正在执行【微信消息发送】任务。

## 工具
send_wx_message(contact_name, message)

## 规则
contact_name 用微信昵称/备注，需微信桌面版已登录。

## 输出
告知发送成功或失败。"""


SEARCH_SKILL_PROMPT = """你正在执行【联网搜索】任务。

## 工具
search(content)

## 输出
整理搜索结果，标注来源，简洁回答。"""


# ═══════════════════════════════════════════════
# Skill 注册
# ═══════════════════════════════════════════════

def register_all_skills():
    """注册所有 Skill 到全局注册中心"""
    registry = SkillRegistry()

    registry.register(Skill(
        name="weather",
        description="天气查询。获取任意城市的未来几天天气预报（含温度、风力、天气状况）。如用户未指定城市会自动定位。",
        tools=[get_user_location, get_city_code, get_weather],
        system_prompt=WEATHER_SKILL_PROMPT,
        workflow_hint="get_user_location → get_city_code → get_weather",
    ))

    registry.register(Skill(
        name="schedule",
        description="课表/日程查询。查询指定日期的课程安排（课程名、时间、节次、地点）。",
        tools=[get_current_month, get_schedule],
        system_prompt=SCHEDULE_SKILL_PROMPT,
        workflow_hint="get_current_month → get_schedule",
    ))

    registry.register(Skill(
        name="report",
        description="工作报告生成。检索指定用户指定月份的工作记录，生成包含效率、特征、耗材、对比四个维度的办公效率报告。",
        tools=[get_user_id, get_current_month, fill_context_for_report, fetch_external_data],
        system_prompt=REPORT_SKILL_PROMPT,
        workflow_hint="get_user_id → fill_context_for_report → fetch_external_data",
    ))

    registry.register(Skill(
        name="knowledge",
        description="知识库检索。从办公效率专业知识库检索软件操作指南、效率提升方法、文档处理技巧等专业资料。",
        tools=[rag_summarize],
        system_prompt=KNOWLEDGE_SKILL_PROMPT,
    ))

    registry.register(Skill(
        name="document",
        description="Word文档处理。用户上传Word模板文件后，AI自动填充占位标签并返回下载链接。",
        tools=[auto_fill_word],
        system_prompt=DOCUMENT_SKILL_PROMPT,
    ))

    registry.register(Skill(
        name="communication",
        description="微信消息发送。通过微信桌面版向指定联系人自动发送消息。",
        tools=[send_wx_message],
        system_prompt=COMMUNICATION_SKILL_PROMPT,
    ))

    registry.register(Skill(
        name="search",
        description="联网搜索。搜索互联网获取实时资讯、最新信息、外部知识。",
        tools=[search],
        system_prompt=SEARCH_SKILL_PROMPT,
    ))

    logger = __import__("AIRAGAgent.utils.logger_handler", fromlist=["logger"]).logger
    logger.info(f"[Skills] 共注册 {len(registry.get_all_skills())} 个 Skill")
