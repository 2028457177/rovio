#!/bin/bash
# ====== user_service 独立启动 ======
# 服务已完全解耦，可单独拷贝本目录到任意位置运行（无需项目根）。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${USER_PORT:-8002}"
export LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"
export UPLOAD_DIR="${UPLOAD_DIR:-$SCRIPT_DIR/data/uploads}"

exec python -m uvicorn main:app --app-dir . --host 0.0.0.0 --port "$PORT" --log-level info
