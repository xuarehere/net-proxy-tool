#!/usr/bin/env python3
"""
net-proxy-tool: Universal Cross-Platform Ephemeral Proxy Runner (v1.3.0)
Supports multi-gateway resolution, on-the-fly gateway override (--gateway),
and zero-pollution ephemeral process sandboxing (pure Python 3 standard library).
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
EXAMPLE_CONFIG_PATH = BASE_DIR / "config.example.json"


def load_config():
    default_cfg = {
        "version": "1.3.0",
        "active_gateway_id": "gw-default",
        "gateways": [
            {
                "id": "gw-default",
                "name": "局域网代理工作站",
                "host": "192.168.1.100",
                "port": 7890,
                "protocol": "http",
                "is_default": True
            },
            {
                "id": "gw-local-win",
                "name": "本机开发代理端口",
                "host": "127.0.0.1",
                "port": 7897,
                "protocol": "http",
                "is_default": False
            }
        ],
        "no_proxy": "localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,*.local"
    }

    target_cfg_file = None
    if CONFIG_PATH.exists():
        target_cfg_file = CONFIG_PATH
    elif EXAMPLE_CONFIG_PATH.exists():
        # 自愈机制: 首次克隆若无 config.json，自动从 config.example.json 拷贝
        try:
            shutil.copy2(EXAMPLE_CONFIG_PATH, CONFIG_PATH)
            target_cfg_file = CONFIG_PATH
        except Exception:
            target_cfg_file = EXAMPLE_CONFIG_PATH

    if target_cfg_file and target_cfg_file.exists():
        try:
            with open(target_cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception:
            pass

    return default_cfg


def resolve_gateway(cfg, explicit_gw=None):
    """解析目标代理网关 host 与 port"""
    if explicit_gw:
        if ":" in explicit_gw:
            parts = explicit_gw.split(":")
            return parts[0], int(parts[1])
        # 若为 gateway_id
        for gw in cfg.get("gateways", []):
            if gw.get("id") == explicit_gw:
                return gw.get("host"), int(gw.get("port"))
        return explicit_gw, 7890

    # 环境变量覆盖
    env_gw = os.environ.get("NET_PROXY_GATEWAY")
    if env_gw:
        return resolve_gateway(cfg, env_gw)

    # 查表匹配 active_gateway_id
    active_id = cfg.get("active_gateway_id")
    for gw in cfg.get("gateways", []):
        if gw.get("id") == active_id:
            return gw.get("host"), int(gw.get("port"))

    # 寻找默认标记
    for gw in cfg.get("gateways", []):
        if gw.get("is_default"):
            return gw.get("host"), int(gw.get("port"))

    # 兼容老配置 proxy_host / proxy_port
    if "proxy_host" in cfg:
        return cfg["proxy_host"], int(cfg.get("proxy_port", 7890))

    return "127.0.0.1", 7890


def check_gateway(host: str, port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def main():
    raw_args = sys.argv[1:]
    if not raw_args:
        print("net-proxy-tool: 跨平台通用代理沙箱执行器 (v1.3.0)")
        print("用法: python with_proxy.py [--gateway host:port] [--no-check] <命令> [参数...]")
        print("示例:")
        print("  python with_proxy.py curl -I https://www.google.com")
        print("  python with_proxy.py --gateway 192.168.1.100:7890 git clone https://github.com/octocat/Hello-World.git")
        print("  python with_proxy.py --no-check pip install openai httpx")
        sys.exit(1)

    explicit_gw = None
    skip_check = False
    cmd = []
    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        if arg in ("--gateway", "-g") and i + 1 < len(raw_args):
            explicit_gw = raw_args[i + 1]
            i += 2
        elif arg.startswith("--gateway="):
            explicit_gw = arg.split("=", 1)[1]
            i += 1
        elif arg in ("--no-check", "-n"):
            skip_check = True
            i += 1
        else:
            cmd = raw_args[i:]
            break

    if not cmd:
        print("[net-proxy-tool 错误] 未指定待执行命令！", file=sys.stderr)
        sys.exit(1)

    cfg = load_config()
    host, port = resolve_gateway(cfg, explicit_gw)

    if not skip_check and not check_gateway(host, port):
        print(
            f"[net-proxy-tool 错误] 代理网关 {host}:{port} 不可达！请检查该代理工作站状态。",
            file=sys.stderr
        )
        sys.exit(101)

    proxy_url = f"http://{host}:{port}"
    socks_url = f"socks5://{host}:{port}"
    no_proxy = cfg.get("no_proxy", "")

    # 隔离构建子进程环境变量，绝不污染系统环境
    env = os.environ.copy()
    env["http_proxy"] = proxy_url
    env["https_proxy"] = proxy_url
    env["HTTP_PROXY"] = proxy_url
    env["HTTPS_PROXY"] = proxy_url
    env["all_proxy"] = socks_url
    env["ALL_PROXY"] = socks_url
    env["no_proxy"] = no_proxy
    env["NO_PROXY"] = no_proxy

    try:
        ret = subprocess.run(cmd, env=env)
        sys.exit(ret.returncode)
    except KeyboardInterrupt:
        sys.exit(130)
    except FileNotFoundError:
        print(f"[net-proxy-tool 错误] 找不到命令: {cmd[0]}", file=sys.stderr)
        sys.exit(127)
    except Exception as e:
        print(f"[net-proxy-tool 错误] 执行失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
