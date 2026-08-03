#!/bin/bash
# ====== auth_service 独立启动 ======
# 服务已完全解耦，可单独拷贝本目录到任意位置运行（无需项目根）。
# 环境变量可通过 deploy/backend/.env 或系统环境设置，未设置时用默认值。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${AUTH_PORT:-8001}"
export LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"

exec python -m uvicorn main:app --app-dir . --host 0.0.0.0 --port "$PORT" --log-level info
