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
    logger.info("所有模型加载完毕，服务就绪")
    yield
    logger.info("项目关闭")

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

conversations_store: List[dict] = []


class ChatRequest(BaseModel):
    message: str
    session_id: str = None
    stream: bool = True


class ConversationSaveRequest(BaseModel):
    id: str
    title: str
    messages: List[dict]
    time: str = ""


def generate_sse_stream(message: str, session_id: str = None):
    for chunk in agent_service.agent.execute_stream(message):
        if isinstance(chunk, dict):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        else:
            content = chunk.strip()
            if content:
                yield f"data: {json.dumps({'type': 'output', 'content': content}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if request.stream:
        return StreamingResponse(
            generate_sse_stream(request.message, request.session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    response_chunks = []
    for chunk in agent_service.agent.execute_stream(request.message):
        if isinstance(chunk, dict):
            if chunk["type"] == "output":
                response_chunks.append(chunk["content"])
        else:
            content = chunk.strip()
            if content:
                response_chunks.append(content)

    return JSONResponse(content={
        "content": "".join(response_chunks),
        "session_id": request.session_id,
    })


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "自动化办公助手"}


@app.get("/api/conversations")
async def get_conversations():
    return JSONResponse(content={"conversations": conversations_store})


@app.post("/api/conversations")
async def save_conversation(request: ConversationSaveRequest):
    existing = next((c for c in conversations_store if c["id"] == request.id), None)
    if existing:
        existing["title"] = request.title
        existing["messages"] = request.messages
        existing["time"] = request.time
    else:
        conversations_store.insert(0, {
            "id": request.id,
            "title": request.title,
            "messages": request.messages,
            "time": request.time
        })
    return JSONResponse(content={"status": "ok"})


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    global conversations_store
    conversations_store = [c for c in conversations_store if c["id"] != conversation_id]
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
