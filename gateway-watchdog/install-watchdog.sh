#!/usr/bin/env bash
# ==============================================================================
# net-proxy-tool: Install Gateway Watchdog
# Zero sudo requirement. Runs as unprivileged user.
# ==============================================================================
set -euo pipefail

DEST_DIR="${HOME}/.local/bin"
mkdir -p "$DEST_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "${SCRIPT_DIR}/watchdog.sh" "${DEST_DIR}/clash-watchdog.sh"
chmod +x "${DEST_DIR}/clash-watchdog.sh"

# 终止可能存在的旧 watchdog
pkill -f "clash-watchdog.sh" 2>/dev/null || true
sleep 1

# 后台启动
nohup "${DEST_DIR}/clash-watchdog.sh" </dev/null >/dev/null 2>&1 &
echo "✅ [网关节点] 看门狗已在后台启动 (PID: $!)"

# 加入用户 crontab (@reboot 自动保活)
CRON_CMD="@reboot ${DEST_DIR}/clash-watchdog.sh"
(crontab -l 2>/dev/null | grep -v "clash-watchdog.sh" ; echo "$CRON_CMD") | crontab -
echo "✅ [网关节点] 用户级开机自启已配置 (@reboot crontab)"
