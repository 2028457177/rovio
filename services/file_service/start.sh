#!/bin/bash
# ====== file_service 独立启动 ======
# 服务已完全解耦，可单独拷贝本目录到任意位置运行（无需项目根）。
# 注意：UPLOAD_DIR / WORKSPACE_DIR 默认指向本服务 data/ 下，
# 生产环境（nginx 共享）请显式设置两个环境变量。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${FILE_PORT:-8006}"
export LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"
export UPLOAD_DIR="${UPLOAD_DIR:-$SCRIPT_DIR/data/uploads}"
export WORKSPACE_DIR="${WORKSPACE_DIR:-$SCRIPT_DIR/data/workspace}"

exec python -m uvicorn main:app --app-dir . --host 0.0.0.0 --port "$PORT" --log-level info
