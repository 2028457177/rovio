"""admin_service 微服务。

职责：
- 管理员用户管理（用户列表 / 会话查看 / 注销 / 重置密码）
- 数据看板统计（概览 / 趋势 / 工具分布 / 错误率 / Top 用户 / Top 提问）

独立数据库：lc_admin（仅含统计副本表，由 Redis 事件总线同步写入）
- rate_limit_events(user_id, ip, limit_type, identifier, created_at)
- api_call_logs(user_id, session_id, ip, endpoint, duration_ms,
                prompt_tokens, completion_tokens, total_tokens,
                is_success, error_msg, created_at)
- tool_call_logs(user_id, session_id, tool_name, duration_ms,
                 is_success, error_msg, created_at)

事件订阅（lifespan 启动时注册，落库到 lc_admin）：
- events:chat.completed → api_call_logs
- events:tool.called    → tool_call_logs
- events:rate.limited   → rate_limit_events

跨服务依赖：
- auth_service：用户列表 / 重置密码 / 用户名补全 / 概览的用户统计
- user_service：用户资料（display_name / avatar_url）补全、注销清理
- chat_service：用户会话查询
"""
