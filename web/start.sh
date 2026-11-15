#!/usr/bin/env bash
# net-proxy-tool: Start standalone web console (Linux)
set -e
WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WEB_DIR"

PID_FILE="${WEB_DIR}/web.pid"
PORT=8899

# 检查是否已在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "[net-proxy-tool] Web 控制台已在运行中 (PID: $PID)"
        echo "访问地址: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '127.0.0.1'):${PORT}"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# 检查端口占用
OCCUPIED=$(lsof -ti :${PORT} 2>/dev/null || fuser ${PORT}/tcp 2>/dev/null || true)
if [ -n "$OCCUPIED" ]; then
    echo "[net-proxy-tool 警告] 端口 ${PORT} 已被进程 $OCCUPIED 占用，正在停止旧进程..."
    kill -9 $OCCUPIED 2>/dev/null || true
    sleep 1
fi

PYTHON_CMD="python3"
if ! command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi

nohup $PYTHON_CMD server.py </dev/null >web.log 2>&1 &
echo $! > "$PID_FILE"

IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
echo "=================================================="
echo "✅ net-proxy-tool 独立微型 Web 控制台已在后台启动"
echo "PID: $(cat "$PID_FILE")"
echo "本机访问: http://127.0.0.1:${PORT}"
echo "局域网访问: http://${IP}:${PORT}"
echo "=================================================="
