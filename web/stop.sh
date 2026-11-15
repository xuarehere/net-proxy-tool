#!/usr/bin/env bash
# net-proxy-tool: Stop standalone web console (Linux)
WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${WEB_DIR}/web.pid"
PORT=8899

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        echo "✅ [net-proxy-tool] 已停止 Web 控制台进程 (PID: $PID)"
    fi
    rm -f "$PID_FILE"
fi

# 确保端口完全释放
OCCUPIED=$(lsof -ti :${PORT} 2>/dev/null || fuser ${PORT}/tcp 2>/dev/null || true)
if [ -n "$OCCUPIED" ]; then
    kill -9 $OCCUPIED 2>/dev/null || true
fi
echo "🛑 [net-proxy-tool] Web 控制台已完全停止，端口 ${PORT} 已释放"
