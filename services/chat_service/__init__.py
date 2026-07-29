"""聊天 / Agent 微服务。

职责：
- POST /api/chat 流式聊天（SSE）
- 会话管理（列表 / 保存 / 删除 / 元数据 / 搜索 / 分叉）
- 消息反馈（点赞 / 踩）
- 异步任务状态查询
- Agent 执行（复用 AIRAGAgent.agent.SupervisorAgent + 工具链 + RAG）

独立数据库：lc_chat
- conversations, messages, message_feedback
- api_call_logs, tool_call_logs

设计要点：
- 复用 AIRAGAgent 代码（agent / tools / middleware / rag / infrastructure）
- 启动时把 AIRAGAgent.database 重定向到 lc_chat
- log_rate_limit_event 改为发布 Redis 事件（rate_limit_events 表在 lc_admin）
- log_api_call / log_tool_call 写入 lc_chat + 发布 Redis 事件供 admin_service 聚合
"""
