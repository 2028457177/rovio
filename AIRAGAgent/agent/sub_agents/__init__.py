"""SubAgent 包：注册所有内置 SubAgent。

import 本包即触发注册（与旧 skills/definitions.py 行为一致）。
"""
from AIRAGAgent.agent.sub_agents.builtin import register_all_subagents

# 模块加载时已自动注册，这里再调一次是幂等的（_initialized 守卫）
register_all_subagents()

__all__ = ["register_all_subagents"]
