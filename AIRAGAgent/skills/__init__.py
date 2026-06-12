"""
Skills 模块 - 将原子工具封装为领域能力包

与纯 Tool 的关键区别：
- 一个 Skill 可包含多个 tool，形成完整的领域工作流
- 每个 Skill 自带专属 system prompt（领域知识+约束+最佳实践）
- 按需激活：只有被选中的 Skill 才会注入详细 prompt，节省 token
- Supervisor 不再逐个编排 tool，改为选择 Skill 委派任务
"""
from AIRAGAgent.skills.base import Skill, SkillRegistry

__all__ = ["Skill", "SkillRegistry"]
