"""
FastAPI 应用入口 - 提供 API 接口 + 挂载 Vue 前端
"""
import sys
import os
import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional

from services.agent_service import AgentService
from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.database import init_db, close_pool
from AIRAGAgent.infrastructure.rate_limiter import get_chat_rate_limiter
from AIRAGAgent.infrastructure.task_queue import register_default_handlers
from AIRAGAgent.infrastructure.redis_client import close_redis


async def _warm_up_models():
    """预热本地模型，在项目启动时将模型加载到 Ollama 显存中"""
    from AIRAGAgent.model.local_factory import local_chat_model, local_embed_model

    logger.info("正在预热本地聊天模型 (qwen3:4b)...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: local_chat_model.invoke("Hi"),
    )
    logger.info("本地聊天模型预热完成")

    logger.info("正在预热本地嵌入模型 (nomic-embed-text)...")
    await loop.run_in_executor(
        None,
        lambda: local_embed_model.embed_query("warmup"),
    )
    logger.info("本地嵌入模型预热完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("项目启动中，开始加载本地模型...")
    await _warm_up_models()
    logger.info("正在初始化MySQL数据库...")
    await asyncio.get_event_loop().run_in_executor(None, init_db)
    logger.info("正在注册任务队列处理器...")
    await asyncio.get_event_loop().run_in_executor(None, register_default_handlers)
    logger.info("数据库初始化完成，服务就绪")
    yield
    logger.info("项目关闭")
    close_pool()
    close_redis()

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"

app = FastAPI(title="自动化办公助手 API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_service = AgentService()


class ChatRequest(BaseModel):
    message: str
    session_id: str = None
    stream: bool = True


class ConversationSaveRequest(BaseModel):
    id: str
    title: str
    messages: List[dict]
    time: str = ""


async def generate_sse_stream(message: str, session_id: str = None):
    async for chunk in agent_service._stream_response(message, session_id):
        if isinstance(chunk, dict):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        else:
            content = chunk.strip()
            if content:
                yield f"data: {json.dumps({'type': 'output', 'content': content}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/api/chat")
async def chat(chat_req: ChatRequest, req: Request):
    client_ip = req.client.host if req.client else "unknown"
    limiter = get_chat_rate_limiter()
    allowed, remaining = limiter.is_allowed(client_ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "请求过于频繁，请稍后再试", "detail": f"每 {limiter.window_seconds} 秒最多 {limiter.max_requests} 次请求"},
        )

    if chat_req.stream:
        return StreamingResponse(
            generate_sse_stream(chat_req.message, chat_req.session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-RateLimit-Limit": str(limiter.max_requests),
                "X-RateLimit-Remaining": str(remaining),
            },
        )

    response_chunks = []
    async for chunk in agent_service._stream_response(chat_req.message, chat_req.session_id):
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
    return {"status": "ok", "service": "自动化办公助手", "redis": redis_status}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    from AIRAGAgent.infrastructure.task_queue import get_task_status as queue_get_status
    result = await asyncio.get_event_loop().run_in_executor(None, queue_get_status, task_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": "任务未找到"})
    return JSONResponse(content=result)


@app.get("/api/conversations")
async def get_conversations():
    from AIRAGAgent.database import get_conversations as db_get_conversations
    conversations = await asyncio.get_event_loop().run_in_executor(None, db_get_conversations)
    return JSONResponse(content={"conversations": conversations})


@app.post("/api/conversations")
async def save_conversation(request: ConversationSaveRequest):
    from AIRAGAgent.database import save_conversation_full as db_save_conversation_full

    def _save():
        db_save_conversation_full(request.id, request.title, request.messages)
    await asyncio.get_event_loop().run_in_executor(None, _save)
    return JSONResponse(content={"status": "ok"})


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    from AIRAGAgent.database import delete_conversation as db_delete_conversation
    await asyncio.get_event_loop().run_in_executor(None, db_delete_conversation, conversation_id)
    return JSONResponse(content={"status": "ok"})


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{path:path}")
async def spa_fallback(path: str):
    target = STATIC_DIR / path
    if target.exists() and target.is_file():
        return FileResponse(target)
    return FileResponse(STATIC_DIR / "index.html")
