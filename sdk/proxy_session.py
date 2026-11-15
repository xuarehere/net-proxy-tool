"""
net-proxy-tool: Python Native Proxy Context Manager (v2.0)
Supports dynamic gateway switching and multi-node routing.
Zero external dependencies. Works on Windows, Linux, and macOS.
"""
import contextlib
import functools
import json
import os
from pathlib import Path
import socket
from typing import Generator, Optional

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.example.json"

PROXY_KEYS = [
    "http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
    "all_proxy", "ALL_PROXY", "no_proxy", "NO_PROXY"
]


def load_config():
    default_cfg = {
        "active_gateway_id": "gw-primary",
        "gateways": [
            {
                "id": "gw-primary",
                "name": "Primary Proxy Gateway",
                "host": "192.168.1.100",
                "port": 7890,
                "is_default": True
            }
        ],
        "no_proxy": "localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,*.local"
    }
    target_path = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception:
            pass
    return default_cfg


def resolve_gateway(cfg, gateway: Optional[str] = None):
    if gateway:
        if ":" in gateway:
            parts = gateway.split(":")
            return parts[0], int(parts[1])
        for gw in cfg.get("gateways", []):
            if gw.get("id") == gateway:
                return gw.get("host"), int(gw.get("port"))
        return gateway, 7890

    active_id = cfg.get("active_gateway_id")
    for gw in cfg.get("gateways", []):
        if gw.get("id") == active_id:
            return gw.get("host"), int(gw.get("port"))

    for gw in cfg.get("gateways", []):
        if gw.get("is_default"):
            return gw.get("host"), int(gw.get("port"))

    if "proxy_host" in cfg:
        return cfg["proxy_host"], int(cfg.get("proxy_port", 7890))

    return "192.168.1.100", 7890


def is_gateway_alive(gateway: Optional[str] = None, timeout: float = 0.5) -> bool:
    cfg = load_config()
    host, port = resolve_gateway(cfg, gateway)
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


@contextlib.contextmanager
def ProxySession(
    gateway: Optional[str] = None,
    check: bool = True,
    timeout: float = 0.5
) -> Generator[str, None, None]:
    """
    按需代理上下文管理器：
    进入上下文时注入当前进程代理环境变量；
    离开代码块（无论是正常完成还是抛出任何异常）通过 finally 强制销毁代理环境变量，彻底还原初始环境。
    """
    cfg = load_config()
    host, port = resolve_gateway(cfg, gateway)

    if check and not is_gateway_alive(gateway=f"{host}:{port}", timeout=timeout):
        raise ConnectionError(f"Proxy gateway {host}:{port} is unreachable.")

    proxy_url = f"http://{host}:{port}"
    socks_url = f"socks5://{host}:{port}"
    no_proxy = cfg.get("no_proxy", "")

    saved_env = {k: os.environ.get(k) for k in PROXY_KEYS}

    try:
        os.environ["http_proxy"] = proxy_url
        os.environ["https_proxy"] = proxy_url
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        os.environ["all_proxy"] = socks_url
        os.environ["ALL_PROXY"] = socks_url
        os.environ["no_proxy"] = no_proxy
        os.environ["NO_PROXY"] = no_proxy
        yield proxy_url
    finally:
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def with_proxy(gateway: Optional[str] = None):
    """函数装饰器形式的即启即销"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ProxySession(gateway=gateway):
                return func(*args, **kwargs)
        return wrapper
    return decorator
