#!/usr/bin/env bash
# net-proxy-tool: 用户级免污染命令行安装助手
# 在 ~/.local/bin/ 下建立软链接，使可以在终端任意目录下直接调用 proxy-on / proxy-off / with-proxy / docker-proxy
set -e

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${TOOL_DIR}/bin"
TARGET_DIR="${HOME}/.local/bin"

mkdir -p "$TARGET_DIR"

echo "=================================================="
echo " 🚀 Net-Proxy-Tool: 快捷命令安装助手"
echo " 安装目标: $TARGET_DIR"
echo " 绝不修改系统文件，仅在当前用户目录创建快捷软链"
echo "=================================================="

# 软链接各个命令
ln -sf "${BIN_DIR}/with-proxy" "${TARGET_DIR}/with-proxy"
ln -sf "${BIN_DIR}/proxy-on" "${TARGET_DIR}/proxy-on"
ln -sf "${BIN_DIR}/proxy-off" "${TARGET_DIR}/proxy-off"
ln -sf "${BIN_DIR}/docker-proxy" "${TARGET_DIR}/docker-proxy"

echo "✅ 软链接已就绪:"
echo "   - with-proxy   -> ${TARGET_DIR}/with-proxy"
echo "   - proxy-on     -> ${TARGET_DIR}/proxy-on"
echo "   - proxy-off    -> ${TARGET_DIR}/proxy-off"
echo "   - docker-proxy -> ${TARGET_DIR}/docker-proxy"

# 检查 PATH 是否包含 ~/.local/bin
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    echo ""
    echo "⚠️ 提示: 您的环境变量 PATH 中未包含 $TARGET_DIR"
    echo "建议在 ~/.bashrc 中追加: export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "或者直接使用别名:"
    echo "alias proxy-on='source ${BIN_DIR}/proxy-on'"
    echo "alias proxy-off='source ${BIN_DIR}/proxy-off'"
fi

echo "=================================================="
echo "🎉 安装完成！在任意目录直接输入即可调用！"
