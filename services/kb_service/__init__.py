"""知识库微服务。

职责：
- 知识库 CRUD（全局 / 个人）
- 文档管理（上传 / 删除 / 替换 / 批量删除）
- 向量索引（分块预览 / 重建索引 / 增量更新）
- 检索测试 playground
- 供 chat_service 的 RAG 检索调用内部接口

独立数据库：lc_kb
- knowledge_bases(id, name, scope, owner_user_id, biz_line, description, is_enabled, is_default, ...)
- kb_documents(id, kb_id, filename, stored_path, file_ext, file_size, file_md5, version, source, uploader_id, status, chunk_count, ...)

向量存储：ChromaDB kb_store 集合（与 AIRAGAgent 共用持久化目录，通过 kb_id 元数据隔离）。

复用 AIRAGAgent.kb 模块的业务逻辑，仅将数据库重定向到 lc_kb。
"""
