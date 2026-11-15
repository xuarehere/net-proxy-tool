#!/usr/bin/env bash
# ==============================================================================
# net-proxy-tool: Gateway Watchdog
# Runs as unprivileged user. Ensures 7890 stays bound to *:7890.
# ==============================================================================
set -euo pipefail

PORT=7890
CONFIG_FILE="${HOME}/.local/share/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml"
WORKDIR="${HOME}/.local/share/io.github.clash-verge-rev.clash-verge-rev"
SOCK="/tmp/verge/verge-mihomo.sock"
LOG_FILE="${HOME}/.local/share/clash-watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

check_and_heal() {
    # 检查 7890 是否监听在全部网络接口 (* 或 0.0.0.0)
    if ! ss -tlpn 2>/dev/null | grep -qE "(\*|0\.0\.0\.0):${PORT}"; then
        log "WARNING: Port ${PORT} not bound to all interfaces (*:7890). Triggering auto-heal..."
        
        # 1. 确保配置文件中 allow-lan 为 true
        if [ -f "$CONFIG_FILE" ]; then
            sed -i 's/^allow-lan:.*/allow-lan: true/' "$CONFIG_FILE" 2>/dev/null || true
        fi
        
        # 2. 终止旧的仅监听在 127.0.0.1 的 core 进程
        pkill -f "verge-mihomo.*clash-verge\.yaml" 2>/dev/null || true
        sleep 1
        
        # 3. 重新以局域网全监听模式启动 core
        if [ -x "/usr/bin/verge-mihomo" ] && [ -f "$CONFIG_FILE" ]; then
            nohup /usr/bin/verge-mihomo -d "$WORKDIR" -f "$CONFIG_FILE" -ext-ctl-unix "$SOCK" > /tmp/verge-mihomo-watchdog.log 2>&1 &
            log "SUCCESS: Restarted verge-mihomo with allow-lan=true, PID: $!"
        fi
    fi
}

log "Watchdog started for gateway port ${PORT}"
while true; do
    check_and_heal || true
    sleep 15
done
