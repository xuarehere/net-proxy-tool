"""Shared diagnostics for the Web console and the MCP server.

Both entry points must describe a gateway and a node in the same words, so the
aggregation lives here once. The module reads the configuration and never writes
it, and it never returns a credential.

The network probes are passed in as callables: the console supplies its own
checks, the MCP server supplies the same ones, and a test supplies a fake.
"""
import ipaddress
import time
from concurrent.futures import ThreadPoolExecutor

from sdk.config import proxy_url, resolve_gateway_info

DEFAULT_TARGET_WORKERS = 7

LOOPBACK_GATEWAY_WARNING = "绑定的网关在本机回环地址上，远程节点无法访问；请改用节点可达的网关地址。"
MISSING_BINDING_WARNING = "此节点尚未保存网关绑定，开启代理前必须先绑定网关。"
MISSING_GATEWAY_WARNING = "绑定的网关已不存在，请重新选择并保存。"


def is_loopback_host(host):
    """True when the host names the loopback interface of this machine."""
    name = str(host or "").strip().lower()
    if not name:
        return False
    if name == "localhost":
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def gateway_report(cfg, gateway_id=None, tcp_probe=None):
    """Return the gateway section of a status report, or None when none is selected."""
    gateway = resolve_gateway_info(cfg, gateway_id)
    if not gateway:
        return None
    host = str(gateway.get("host") or "")
    try:
        port = int(gateway.get("port") or 0)
    except (TypeError, ValueError):
        port = 0
    report = {"id": gateway.get("id"), "name": gateway.get("name"), "host": host, "port": port,
              "online": False, "tcp_ok": False, "path_verified": False,
              "latency_ms": None, "error": None}
    protocol = str(gateway.get("protocol", "http")).strip().lower()
    if protocol != "http":
        report["error"] = "请使用 HTTP 或 mixed 代理监听端口"
        return report
    if tcp_probe:
        reachable, detail = tcp_probe(host, port)
        report["tcp_ok"] = bool(reachable)
        report["latency_ms"] = detail if reachable else None
        report["error"] = None if reachable else str(detail)
    return report


def targets_report(cfg, proxy, target_probe=None, workers=DEFAULT_TARGET_WORKERS):
    """Probe every configured diagnostic target through the selected proxy."""
    targets = cfg.get("diagnostic_targets") or {}
    if not target_probe or not targets:
        return []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(targets)))) as pool:
        futures = [pool.submit(target_probe, name, info, proxy) for name, info in targets.items()]
        return [future.result() for future in futures]


def node_summary(cfg, node, gateway_resolver=None):
    """Return the public summary of one node, with the proxy it would use."""
    resolver = gateway_resolver or resolve_gateway_info
    try:
        port = int(node.get("port") or 22)
    except (TypeError, ValueError):
        port = 22
    summary = {
        "id": node.get("id"),
        "name": node.get("name"),
        "host": node.get("host"),
        "port": port,
        "access_mode": node.get("access_mode", "ssh"),
        "auth_type": node.get("auth_type", "key"),
        "bound_gateway_id": node.get("bound_gateway_id") or "",
        "is_proxy_enabled": bool(node.get("is_proxy_enabled")),
        "managed_state": node.get("managed_state", "unknown"),
        "verification": node.get("verification") or {"verified": False, "status": "unknown"},
        "effective_proxy": None,
        "gateway": None,
        "warnings": [],
    }
    local = summary["access_mode"] == "local"
    bound = summary["bound_gateway_id"]
    if not bound:
        if not local:
            summary["warnings"].append(MISSING_BINDING_WARNING)
        return summary
    gateway = resolver(cfg, bound)
    if not gateway:
        summary["warnings"].append(MISSING_GATEWAY_WARNING)
        return summary
    host = str(gateway.get("host") or "")
    try:
        gateway_port = int(gateway.get("port") or 0)
    except (TypeError, ValueError):
        gateway_port = 0
    summary["gateway"] = {"id": gateway.get("id"), "name": gateway.get("name"),
                           "host": host, "port": gateway_port}
    if host and gateway_port:
        summary["effective_proxy"] = proxy_url(host, gateway_port)
    if not local and is_loopback_host(host):
        summary["warnings"].append(LOOPBACK_GATEWAY_WARNING)
    return summary


def status_report(cfg, gateway_id=None, tcp_probe=None, target_probe=None,
                  workers=DEFAULT_TARGET_WORKERS):
    """Return the complete status report for the selected gateway."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    report = gateway_report(cfg, gateway_id, tcp_probe)
    if report is None:
        return {"gateway": None, "targets": [], "timestamp": timestamp}
    results = []
    if report["tcp_ok"] and report["host"] and report["port"]:
        results = targets_report(cfg, proxy_url(report["host"], report["port"]), target_probe, workers)
    report["online"] = any(item.get("http_ok") for item in results)
    report["path_verified"] = any(item.get("path_verified") for item in results)
    return {"gateway": report, "targets": results, "timestamp": timestamp}
