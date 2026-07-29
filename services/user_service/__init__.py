"""用户微服务。

职责：
- 用户资料管理（昵称 / 邮箱 / 头像）
- 课表上传与管理（Excel + 开学日期）
- 注销账号时清理 user 侧数据

独立数据库：lc_user
- user_profiles(user_id BIGINT PK, display_name VARCHAR(100), email VARCHAR(100), avatar_url VARCHAR(255), updated_at DATETIME)
- user_schedules(user_id BIGINT PK, file_path VARCHAR(255), start_date DATE NULL, uploaded_at DATETIME NULL)
"""
