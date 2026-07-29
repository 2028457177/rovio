#!/bin/bash
# ====== 微服务多进程启动脚本 (Linux) ======
# 一键启动 6 个微服务进程，各自绑定独立端口
#
# 端口分配：
#   auth_service  :8001   user_service  :8002   chat_service  :8003
#   kb_service    :8004   admin_service :8005   file_service  :8006

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# 加载环境变量
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

echo "========================================"
echo "  lc-course 微服务启动"
echo "  项目根: $PROJECT_ROOT"
echo "========================================"

# 安装依赖
if command -v uv &> /dev/null; then
    echo "[1/1] 同步 Python 依赖..."
    uv sync --frozen
fi

# 启动函数：后台启动服务，日志重定向到 logs/
start_service() {
    local name=$1
    local module=$2
    local port=$3
    echo "  → 启动 $name (:$port)..."
    nohup python -m uvicorn "$module" \
        --host 0.0.0.0 --port "$port" \
        --log-level info \
        > "AIRAGAgent/logs/${name}.stdout.log" 2>&1 &
    echo $! > "AIRAGAgent/logs/${name}.pid"
}

start_service "auth_service"  "services.auth_service.main:app"  8001
start_service "user_service"  "services.user_service.main:app"  8002
start_service "chat_service"  "services.chat_service.main:app"  8003
start_service "kb_service"    "services.kb_service.main:app"    8004
start_service "admin_service" "services.admin_service.main:app" 8005
start_service "file_service"  "services.file_service.main:app"  8006

echo ""
echo "全部服务已启动。PID 文件在 AIRAGAgent/logs/*.pid"
echo "查看日志: tail -f AIRAGAgent/logs/<service_name>_<date>.log"
echo "停止: bash $SCRIPT_DIR/stop_microservices.sh"
