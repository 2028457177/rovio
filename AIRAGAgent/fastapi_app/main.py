"""
FastAPI 应用入口 - 提供 API 接口 + 挂载 Vue 前端
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel

from services.agent_service import AgentService

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"

app = FastAPI(title="自动化办公助手 API", version="2.0.0")

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
