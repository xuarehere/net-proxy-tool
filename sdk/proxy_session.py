"""Temporarily set the current process proxy environment, then restore it."""
import contextlib
import functools
import os
import socket
from typing import Generator, Optional

from .config import load_config, proxy_environment, resolve_gateway

PROXY_KEYS = [
    "http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
    "all_proxy", "ALL_PROXY", "no_proxy", "NO_PROXY"
]


def is_gateway_alive(gateway: Optional[str] = None, timeout: float = 0.5) -> bool:
    try:
        host, port = resolve_gateway(load_config(), gateway)
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (OSError, ValueError):
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

    if check:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                pass
        except OSError as exc:
            raise ConnectionError(f"Proxy gateway {host}:{port} is unreachable.") from exc

    env = proxy_environment(cfg, host, port)
    saved_env = {k: os.environ.get(k) for k in PROXY_KEYS}
    try:
        os.environ.update(env)
        yield env["http_proxy"]
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
