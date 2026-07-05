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

WEATHER_SKILL_PROMPT = """你现在帮用户查天气。别啰嗦，直接干：

1. get_user_location() 看看用户在哪儿
2. get_city_code(city_name) 把省市名变纯城市名
3. get_weather(city_name) 拿天气数据

用户已经说了城市的话，跳过第1步。拿到数据直接告诉用户就行了——日期、天气、温度、风力，一条一行，别加戏。"""


SCHEDULE_SKILL_PROMPT = """你现在帮用户查课表。步骤很简单：

1. get_current_month(wantday) 看看那天是第几周、星期几
2. get_schedule(week, day) 拿课表

别自己推算日期，老老实实调工具查。拿到课表直接列出来：课程名、时间、节次、地点。没课就说没课，别瞎分析。"""


REPORT_SKILL_PROMPT = """你现在帮用户写工作报告。按顺序来，别跳：

1. get_user_id()
2. fill_context_for_report()（这步不能省）
3. 确认月份（用户说了就用用户说的，没说就用 get_current_month(0)）
4. fetch_external_data(user_id, month)

数据到手后，从特征、效率、耗材、对比四个角度整理。没数据就直说。"""


KNOWLEDGE_SKILL_PROMPT = """你现在帮用户搜一下内部资料库。调 rag_summarize(query)，query 用核心关键词就行。搜到了就总结一下，顺手给点实用建议，别跑题。"""


DOCUMENT_SKILL_PROMPT = """你现在帮用户填 Word 文档。调 auto_fill_word(template_path)，template_path 就是用户上传后服务器给的路径。处理完了告诉用户，别忘了附上下载链接。"""


COMMUNICATION_SKILL_PROMPT = """你现在帮用户发微信消息。调 send_wx_message(contact_name, message)，联系人是微信昵称或备注名。前提是微信桌面版得开着。发完告诉用户成功没成功。"""


SEARCH_SKILL_PROMPT = """你现在帮用户上网搜东西。调 search(content)，搜完了把结果整理一下，标注来源，简要回答就行。"""


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
