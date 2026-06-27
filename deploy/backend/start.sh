#!/bin/bash
# ====== 后端启动脚本 (Linux) ======

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 默认值
SERVER_HOST="${SERVER_HOST:-0.0.0.0}"
SERVER_PORT="${SERVER_PORT:-8000}"

echo "========================================"
echo "  自动化办公助手 - 后端服务"
echo "  监听: ${SERVER_HOST}:${SERVER_PORT}"
echo "========================================"

# 安装依赖（使用 uv）
if command -v uv &> /dev/null; then
    echo "[1/2] 安装 Python 依赖..."
    uv sync --frozen
else
    echo "[1/2] uv 未安装，使用 pip 安装依赖..."
    pip install -e . --quiet
fi

# 启动服务
echo "[2/2] 启动 FastAPI 服务..."
python -m uvicorn AIRAGAgent.fastapi_app.main:app \
    --host "$SERVER_HOST" \
    --port "$SERVER_PORT" \
    --log-level info \
    --timeout-keep-alive 300
