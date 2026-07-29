"""file_service FastAPI 入口。

路由：
- POST /api/upload-word       上传 Word 文件
- GET  /api/download/{filename}   下载 Word 文件
"""
from __future__ import annotations

import os
import uuid

from fastapi import UploadFile, File
from fastapi.responses import FileResponse, JSONResponse

from services.common import create_app, logger
from services.common.paths import UPLOAD_DIR

app = create_app("file_service", version="1.0.0")

# 上传目录确保存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的 Word 文件后缀
ALLOWED_EXTS = (".docx", ".doc")
# Word 下载的 media_type
WORD_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@app.post("/api/upload-word")
async def upload_word(file: UploadFile = File(...)):
    """上传 Word 文件到服务器"""
    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTS):
        return JSONResponse(status_code=400, content={"error": "仅支持 .docx 和 .doc 格式的文件"})

    # 生成唯一文件名，保留原始扩展名
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"[file_service] 文件已上传: {file.filename} -> {file_path}")
    return JSONResponse(content={
        "success": True,
        "filename": unique_name,
        "original_name": file.filename,
        "server_path": file_path,
    })


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """下载 Word 文件"""
    # 防路径穿越：只取文件名，并校验解析后的真实路径在 UPLOAD_DIR 内
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name != filename:
        return JSONResponse(status_code=400, content={"error": "非法的文件名"})

    file_path = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.realpath(file_path).startswith(os.path.realpath(UPLOAD_DIR) + os.sep):
        return JSONResponse(status_code=400, content={"error": "非法的文件名"})

    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "文件不存在"})

    return FileResponse(
        path=file_path,
        filename=safe_name,
        media_type=WORD_MEDIA_TYPE,
    )


if __name__ == "__main__":
    import uvicorn
    from services.common.config import SERVICE_REGISTRY
    port = SERVICE_REGISTRY["file"]["port"]
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
