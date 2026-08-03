#!/bin/bash
# ====== kb_service 独立启动 ======
# 依赖 AIRAGAgent 引擎：默认从项目根目录 (../..) 引入，可用 AGENT_HOME 覆盖。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

AGENT_HOME="${AGENT_HOME:-$SCRIPT_DIR/../..}"
export PYTHONPATH="$AGENT_HOME:$PYTHONPATH"

PORT="${KB_PORT:-8004}"
export LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"

exec python -m uvicorn main:app --app-dir . --host 0.0.0.0 --port "$PORT" --log-level info
