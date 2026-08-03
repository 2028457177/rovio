#!/bin/bash
# ====== 微服务多进程启动脚本 (Linux) ======
# 一键启动 6 个微服务进程，各自绑定独立端口
#
# 每个服务已完全解耦：代码自带 core/ 独立库，从自身目录以
#   uvicorn main:app --app-dir .
# 方式启动，不再依赖 services.common 包，可单独拷贝部署。
#
# 端口分配（可用 .env 中的 *_PORT 覆盖）：
#   auth_service  :8001   user_service  :8002   chat_service  :8003
#   kb_service    :8004   admin_service :8005   file_service  :8006

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# 加载环境变量
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    . "$SCRIPT_DIR/.env"
    set +a
fi

echo "========================================"
echo "  lc-course 微服务启动（独立目录模式）"
echo "  项目根: $PROJECT_ROOT"
echo "========================================"

# 安装依赖
if command -v uv &> /dev/null; then
    echo "[1/1] 同步 Python 依赖..."
    uv sync --frozen
fi

# chat/kb 需要引入项目根目录的 AIRAGAgent 引擎
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 启动函数：进入服务自身目录后台启动，日志/PID 仍统一放在 AIRAGAgent/logs/
start_service() {
    local name=$1
    local port=$2
    echo "  → 启动 $name (:$port)..."
    (
        cd "$PROJECT_ROOT/services/$name"
        nohup python -m uvicorn main:app --app-dir . \
            --host 0.0.0.0 --port "$port" \
            --log-level info \
            > "$PROJECT_ROOT/AIRAGAgent/logs/${name}.stdout.log" 2>&1 &
        echo $! > "$PROJECT_ROOT/AIRAGAgent/logs/${name}.pid"
    )
}

start_service "auth_service"  "${AUTH_PORT:-8001}"
start_service "user_service"  "${USER_PORT:-8002}"
start_service "chat_service"  "${CHAT_PORT:-8003}"
start_service "kb_service"    "${KB_PORT:-8004}"
start_service "admin_service" "${ADMIN_PORT:-8005}"
start_service "file_service"  "${FILE_PORT:-8006}"

echo ""
echo "全部服务已启动。PID 文件在 AIRAGAgent/logs/*.pid"
echo "查看日志: tail -f AIRAGAgent/logs/<service_name>_<date>.log"
echo "停止: bash $SCRIPT_DIR/stop_microservices.sh"
