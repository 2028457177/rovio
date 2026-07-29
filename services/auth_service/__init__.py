"""认证微服务。

职责：
- 用户注册 / 登录 / 找回密码
- 修改密码 / 密保问题
- 登录设备管理
- JWT 签发（其他服务只验签）

独立数据库：lc_auth
- users(id, username, password_hash, role, created_at, last_password_changed)
- security_questions(user_id, question, answer_hash)
- login_devices(...)
"""
