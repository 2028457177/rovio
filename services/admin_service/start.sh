#!/bin/bash
# ====== admin_service 独立启动 ======
# 服务已完全解耦，可单独拷贝本目录到任意位置运行（无需项目根）。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${ADMIN_PORT:-8005}"
export LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"

exec python -m uvicorn main:app --app-dir . --host 0.0.0.0 --port "$PORT" --log-level info
