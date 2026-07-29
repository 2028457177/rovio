"""lc-course 微服务架构包。

包含 6 个独立服务 + 共享库 common/：
- auth_service  (:8001)  认证 / 登录设备 / 密保
- user_service  (:8002)  用户资料 / 头像 / 课表
- chat_service  (:8003)  聊天 / 会话 / Agent / 反馈
- kb_service    (:8004)  知识库 / 文档 / 向量检索
- admin_service (:8005)  管理员 / 数据看板
- file_service  (:8006)  文件上传下载

nginx 作为网关按路径前缀路由到各服务。
"""
