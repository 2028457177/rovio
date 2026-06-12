"""
FastAPI 应用入口 - 提供 API 接口 + 挂载 Vue 前端
"""
from __future__ import annotations
import sys
import os
import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid

from services.agent_service import AgentService
from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.database import init_db, close_pool
from AIRAGAgent.infrastructure.rate_limiter import get_chat_rate_limiter
from AIRAGAgent.infrastructure.task_queue import register_default_handlers
from AIRAGAgent.infrastructure.redis_client import close_redis
from AIRAGAgent.agent.tools.agent_tools import user_ip_var, user_lat_var, user_lon_var, user_id_var


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("项目启动中...")
    logger.info("正在初始化MySQL数据库...")
    await asyncio.get_event_loop().run_in_executor(None, init_db)
    logger.info("正在清理30天前的旧会话...")
    from AIRAGAgent.database import cleanup_old_conversations as db_cleanup
    deleted = await asyncio.get_event_loop().run_in_executor(None, db_cleanup, 30)
    if deleted:
        logger.info(f"已清理 {deleted} 个旧会话")
    logger.info("正在注册任务队列处理器...")
    await asyncio.get_event_loop().run_in_executor(None, register_default_handlers)
    logger.info("数据库初始化完成，服务就绪")
    yield
    logger.info("项目关闭")
    close_pool()
    close_redis()

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
SERVE_STATIC = os.getenv("SERVE_STATIC", "true").lower() == "true"

# 文件上传目录（服务器上存储上传的Word文件和生成的文档）
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Rovio API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_service = AgentService()

from .auth import create_access_token, get_current_user, get_admin_user, get_client_ip, ADMIN_ALLOWED_IPS


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


# ==================== 认证 API ====================


@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    """注册新用户"""
    from AIRAGAgent.database import create_user as db_create_user

    if not req.username or not req.password:
        return JSONResponse(status_code=400, content={"error": "用户名和密码不能为空"})
    if len(req.username) < 3 or len(req.username) > 50:
        return JSONResponse(status_code=400, content={"error": "用户名长度应为 3-50 个字符"})
    if len(req.password) < 6:
        return JSONResponse(status_code=400, content={"error": "密码长度不能少于 6 个字符"})

    user = await asyncio.get_event_loop().run_in_executor(
        None, db_create_user, req.username, req.password, req.display_name
    )
    if user is None:
        return JSONResponse(status_code=409, content={"error": "用户名已存在"})

    token = create_access_token(user["id"], user["username"], "user")
    return JSONResponse(content={
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "display_name": user["display_name"], "role": "user"}
    })


@app.post("/api/auth/login")
async def login(req: LoginRequest, request: Request):
    """用户登录"""
    from AIRAGAgent.database import get_user_by_username as db_get_user, verify_password as db_verify_password

    if not req.username or not req.password:
        return JSONResponse(status_code=400, content={"error": "用户名和密码不能为空"})

    user = await asyncio.get_event_loop().run_in_executor(None, db_get_user, req.username)
    if user is None:
        return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})

    if not db_verify_password(req.password, user["password_hash"]):
        return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})

    # 管理员登录 IP 白名单检查
    if user["role"] == "admin" and ADMIN_ALLOWED_IPS:
        client_ip = get_client_ip(request)
        if client_ip not in ADMIN_ALLOWED_IPS:
            return JSONResponse(status_code=403, content={"error": "无权访问管理后台"})

    token = create_access_token(user["id"], user["username"], user["role"])
    return JSONResponse(content={
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "display_name": user["display_name"], "role": user["role"]}
    })


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    from AIRAGAgent.database import get_user_by_id as db_get_user_by_id

    full_user = await asyncio.get_event_loop().run_in_executor(None, db_get_user_by_id, user["id"])
    if full_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return JSONResponse(content={"user": full_user})


class ChatRequest(BaseModel):
    message: str
    session_id: str = None
    stream: bool = True
    latitude: float | None = None
    longitude: float | None = None
    uploaded_file_path: str | None = None      # 用户上传的 Word 文件路径


class ConversationSaveRequest(BaseModel):
    id: str
    title: str
    messages: List[dict]
    time: str = ""


async def generate_sse_stream(user_id: int, message: str, session_id: str = None):
    async for chunk in agent_service._stream_response(user_id, message, session_id):
        if isinstance(chunk, dict):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        else:
            content = chunk.strip()
            if content:
                yield f"data: {json.dumps({'type': 'output', 'content': content}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/api/chat")
async def chat(chat_req: ChatRequest, req: Request, user: dict = Depends(get_current_user)):
    # 获取用户真实 IP（nginx 代理后需从 header 读取）
    client_ip = (
        req.headers.get("X-Real-IP")
        or (req.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        or (req.client.host if req.client else None)
        or "unknown"
    )
    user_id = user["id"]
    # 存入 contextvar，供工具函数使用
    user_ip_var.set(client_ip)
    user_lat_var.set(chat_req.latitude)
    user_lon_var.set(chat_req.longitude)
    user_id_var.set(user_id)

    limiter = get_chat_rate_limiter()
    allowed, remaining = limiter.is_allowed(client_ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "请求过于频繁，请稍后再试", "detail": f"每 {limiter.window_seconds} 秒最多 {limiter.max_requests} 次请求"},
        )

    if chat_req.stream:
        # 如果有上传文件，将文件路径信息附在消息前
        enhanced_message = chat_req.message
        if chat_req.uploaded_file_path:
            enhanced_message = (
                f"[用户已上传Word文件，服务器路径为：{chat_req.uploaded_file_path}] "
                f"{chat_req.message}"
            )

        return StreamingResponse(
            generate_sse_stream(user_id, enhanced_message, chat_req.session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-RateLimit-Limit": str(limiter.max_requests),
                "X-RateLimit-Remaining": str(remaining),
            },
        )

    # 非流式模式也需要处理上传文件路径
    enhanced_message = chat_req.message
    if chat_req.uploaded_file_path:
        enhanced_message = (
            f"[用户已上传Word文件，服务器路径为：{chat_req.uploaded_file_path}] "
            f"{chat_req.message}"
        )

    response_chunks = []
    async for chunk in agent_service._stream_response(user_id, enhanced_message, chat_req.session_id):
        if isinstance(chunk, dict):
            if chunk["type"] == "output":
                response_chunks.append(chunk["content"])
        else:
            content = chunk.strip()
            if content:
                response_chunks.append(content)

    return JSONResponse(content={
        "content": "".join(response_chunks),
        "session_id": chat_req.session_id,
    })


@app.get("/api/health")
async def health_check():
    from AIRAGAgent.infrastructure.redis_client import is_redis_available
    redis_status = "connected" if is_redis_available() else "disconnected"
    return {"status": "ok", "service": "Rovio", "redis": redis_status}


@app.post("/api/upload-word")
async def upload_word(file: UploadFile = File(...)):
    """上传 Word 文件到服务器"""
    if not file.filename.lower().endswith(('.docx', '.doc')):
        return JSONResponse(status_code=400, content={"error": "仅支持 .docx 和 .doc 格式的文件"})

    # 生成唯一文件名，保留原始扩展名
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_name

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"文件已上传: {file.filename} -> {file_path}")
    return JSONResponse(content={
        "success": True,
        "filename": unique_name,
        "original_name": file.filename,
        "server_path": str(file_path),
    })


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """下载已填写的 Word 文件"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": "文件不存在"})

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    from AIRAGAgent.infrastructure.task_queue import get_task_status as queue_get_status
    result = await asyncio.get_event_loop().run_in_executor(None, queue_get_status, task_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": "任务未找到"})
    return JSONResponse(content=result)


@app.get("/api/conversations")
async def get_conversations(user: dict = Depends(get_current_user)):
    from AIRAGAgent.database import get_conversations as db_get_conversations
    conversations = await asyncio.get_event_loop().run_in_executor(None, db_get_conversations, user["id"])
    return JSONResponse(content={"conversations": conversations})


@app.post("/api/conversations")
async def save_conversation(request: ConversationSaveRequest, user: dict = Depends(get_current_user)):
    from AIRAGAgent.database import save_conversation_full as db_save_conversation_full

    def _save():
        db_save_conversation_full(user["id"], request.id, request.title, request.messages)
    await asyncio.get_event_loop().run_in_executor(None, _save)
    return JSONResponse(content={"status": "ok"})


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user: dict = Depends(get_current_user)):
    from AIRAGAgent.database import delete_conversation as db_delete_conversation
    await asyncio.get_event_loop().run_in_executor(None, db_delete_conversation, user["id"], conversation_id)
    return JSONResponse(content={"status": "ok"})


# ==================== 管理员 API ====================

@app.get("/api/admin/users")
async def admin_get_users(admin: dict = Depends(get_admin_user)):
    """管理员获取所有用户列表"""
    from AIRAGAgent.database import get_all_users as db_get_all_users
    users = await asyncio.get_event_loop().run_in_executor(None, db_get_all_users)
    return JSONResponse(content={"users": users})


@app.get("/api/admin/users/{user_id}/conversations")
async def admin_get_user_conversations(user_id: int, admin: dict = Depends(get_admin_user)):
    """管理员查看任意用户的会话列表"""
    from AIRAGAgent.database import get_user_conversations_admin as db_get_user_conv
    conversations = await asyncio.get_event_loop().run_in_executor(None, db_get_user_conv, user_id)
    return JSONResponse(content={"conversations": conversations})


class ResetPasswordRequest(BaseModel):
    password: str = "123456789"


@app.post("/api/admin/users/{user_id}/delete")
async def admin_delete_user(user_id: int, admin: dict = Depends(get_admin_user)):
    """管理员注销用户（删除用户及其全部数据）"""
    from AIRAGAgent.database import delete_user_admin as db_delete_user
    success = await asyncio.get_event_loop().run_in_executor(None, db_delete_user, user_id)
    if not success:
        return JSONResponse(status_code=400, content={"error": "用户不存在或无法删除管理员"})
    return JSONResponse(content={"status": "ok"})


@app.post("/api/admin/users/{user_id}/reset-password")
async def admin_reset_user_password(user_id: int, req: ResetPasswordRequest, admin: dict = Depends(get_admin_user)):
    """管理员重置用户密码"""
    if len(req.password) < 6:
        return JSONResponse(status_code=400, content={"error": "密码长度不能少于 6 个字符"})
    from AIRAGAgent.database import reset_user_password as db_reset_pw
    success = await asyncio.get_event_loop().run_in_executor(None, db_reset_pw, user_id, req.password)
    if not success:
        return JSONResponse(status_code=400, content={"error": "用户不存在或无法修改管理员"})
    return JSONResponse(content={"status": "ok"})


@app.get("/")
async def root():
    if SERVE_STATIC and (STATIC_DIR / "index.html").exists():
        with open(STATIC_DIR / "index.html", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(
            content=html_content,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
    return JSONResponse(content={"service": "Rovio API", "status": "running"})


if SERVE_STATIC:
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{path:path}")
async def spa_fallback(path: str):
    if SERVE_STATIC and STATIC_DIR.exists():
        target = STATIC_DIR / path
        if target.exists() and target.is_file():
            return FileResponse(target)
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            with open(index_path, encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(
                content=html_content,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                }
            )
    return JSONResponse(status_code=404, content={"error": "Not found"})
