#!/bin/bash
# ====== 停止全部微服务 ======
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT/AIRAGAgent/logs"

for pidfile in *_service.pid; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        name="${pidfile%.pid}"
        if kill -0 "$pid" 2>/dev/null; then
            echo "停止 $name (PID $pid)..."
            kill "$pid"
        else
            echo "$name (PID $pid) 已不在运行"
        fi
        rm -f "$pidfile"
    fi
done
echo "全部微服务已停止"
