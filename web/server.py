#!/usr/bin/env python3
"""
net-proxy-tool: Lightweight Standalone Web Console (v3.0)
Multi-Gateway, Multi-Node Topology, Dynamic CRUD & Progressive Guided Sandbox Execution.
Zero third-party dependencies (pure Python 3 standard library).
"""
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer as HTTPServer
from socketserver import TCPServer
import argparse
import copy
import hashlib
import hmac
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import threading
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

WEB_DIR = Path(__file__).resolve().parent
TOOL_DIR = WEB_DIR.parent
STATIC_DIR = WEB_DIR / "static"
if __package__ in (None, ""):
    sys.path.insert(0, str(TOOL_DIR))

from sdk.config import (DEFAULT_TEST_URL, VERSION, config_permission_warning, data_dir, load_config,
                        proxy_url, resolve_gateway_info, rotate_log, save_config)
from web import node_probe
from web import node_baseline
from web import diagnostics
from web.ssh_askpass import password_environment

CONFIG_WRITE_LOCK = threading.RLock()
REQUEST_TIMEOUT_SECONDS = 60
MAX_JSON_BODY_BYTES = 1024 * 1024
MAX_SAFE_INTEGER = (1 << 53) - 1
AUDIT_LOG_LIMIT_BYTES = 5 * 1024 * 1024
AUDIT_LOG_GENERATIONS = 3
ACCESS_COOKIE_NAME = "npt_access"
ACCESS_TOKEN_ENV = "NET_PROXY_ACCESS_TOKEN"
# The console access state, resolved once when the server starts.
ACCESS = {"token": "", "required": False, "printed": False}


class RequestError(ValueError):
    """A client error with an explicit public HTTP status."""

    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = int(status_code)


_STRING_FIELD_LIMITS = {
    "id": 128,
    "gateway_id": 128,
    "node_id": 128,
    "bound_gateway_id": 128,
    "name": 255,
    "host": 255,
    "ssh_host": 255,
    "os_type": 32,
    "access_mode": 32,
    "auth_type": 32,
    "ssh_user": 128,
    "ssh_pass": 4096,
    "container_name": 128,
    "description": 4096,
    "no_proxy": 4096,
    "protocol": 32,
    "target_url": 8192,
    "command": 8192,
    "action": 16,
}
_INTEGER_FIELD_RANGES = {
    "port": (1, 65535),
    "node_revision": (-1, MAX_SAFE_INTEGER),
    "binding_revision": (-1, MAX_SAFE_INTEGER),
}
_BOOLEAN_FIELDS = frozenset(("confirm_execution_mode",))


def text_field(value, name, maximum=255, strip=False):
    """Return a bounded JSON string or raise ValueError."""
    if not isinstance(value, str):
        raise ValueError("{} must be a string".format(name))
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("{} must contain valid Unicode".format(name)) from None
    if "\x00" in value or len(value) > maximum:
        raise ValueError("{} must be at most {} characters and contain no NUL".format(name, maximum))
    return value.strip() if strip else value


def integer_field(value, name, minimum=0, maximum=MAX_SAFE_INTEGER):
    """Return a bounded integer; decimal strings are accepted, Booleans are not."""
    if isinstance(value, bool):
        raise ValueError("{} must be an integer".format(name))
    if isinstance(value, str):
        candidate = value.strip()
        if not re.fullmatch(r"[+-]?\d+", candidate):
            raise ValueError("{} must be an integer".format(name))
        value = int(candidate)
    elif not isinstance(value, int):
        raise ValueError("{} must be an integer".format(name))
    if value < minimum or value > maximum:
        raise ValueError("{} must be between {} and {}".format(name, minimum, maximum))
    return value


def boolean_field(value, name):
    if not isinstance(value, bool):
        raise ValueError("{} must be a Boolean".format(name))
    return value


def normalize_protocol(value):
    protocol = text_field(value, "protocol", maximum=32, strip=True).lower()
    if protocol != "http":
        raise ValueError("请使用 HTTP 或 mixed 代理监听端口")
    return protocol


def validate_node_selections(value):
    if not isinstance(value, list) or not value or len(value) > 256:
        raise ValueError("nodes must be a non-empty array of at most 256 objects")
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("each nodes entry must be an object")
        entry = dict(item)
        if "node_id" in entry:
            entry["node_id"] = text_field(entry["node_id"], "node_id", maximum=128)
        for field in ("node_revision", "binding_revision"):
            if field in entry:
                bounds = _INTEGER_FIELD_RANGES[field]
                entry[field] = integer_field(entry[field], field, bounds[0], bounds[1])
        if "gateway_id" in entry:
            entry["gateway_id"] = text_field(entry["gateway_id"], "gateway_id", maximum=128)
        normalized.append(entry)
    return normalized


def validate_api_payload(path, payload):
    """Normalize recognized API fields before any handler can use them."""
    if not isinstance(payload, dict):
        raise ValueError("请求体必须是 JSON 对象")
    normalized = dict(payload)
    for field, maximum in _STRING_FIELD_LIMITS.items():
        if field in normalized:
            normalized[field] = text_field(normalized[field], field, maximum=maximum)
    for field, bounds in _INTEGER_FIELD_RANGES.items():
        if field in normalized:
            normalized[field] = integer_field(normalized[field], field, bounds[0], bounds[1])
    for field in _BOOLEAN_FIELDS:
        if field in normalized:
            normalized[field] = boolean_field(normalized[field], field)
    if "protocol" in normalized:
        normalized["protocol"] = normalize_protocol(normalized["protocol"])
    if "tags" in normalized:
        tags = normalized["tags"]
        if not isinstance(tags, list) or len(tags) > 64:
            raise ValueError("tags must be an array of at most 64 strings")
        normalized["tags"] = [text_field(tag, "tag", maximum=128) for tag in tags]
    if "nodes" in normalized:
        normalized["nodes"] = validate_node_selections(normalized["nodes"])
    return normalized


class ThreadingHTTPServer(HTTPServer):
    def server_bind(self):
        # HTTPServer resolves its own hostname, which can block on reverse DNS
        # even when binding loopback. The console only needs the numeric address.
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


def audit_path():
    return data_dir() / "audit.log"


def write_audit_log(action, node_id="-", status="info", details="", operator_ip="127.0.0.1"):
    """
    Appends an event record to the lightweight audit log in JSON Lines format.
    """
    try:
        path = audit_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        rotate_log(path, AUDIT_LOG_LIMIT_BYTES, AUDIT_LOG_GENERATIONS)
        client = operator_ip or "127.0.0.1"
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "action": action,
            "node_id": node_id or "-",
            "operator_ip": client,
            "client_address": client,
            "status": status,
            "details": str(details or "")
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        print("[Audit Log Warning] {}".format(type(exc).__name__), file=sys.stderr)


def get_audit_logs(limit=60):
    """
    Retrieves the most recent audit log entries in reverse chronological order.
    """
    if not audit_path().exists():
        return []
    records = []
    try:
        with open(audit_path(), "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines[-limit:]):
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return records



def is_local_host(host: str) -> bool:
    """Check local execution addresses without resolving DNS on a configuration read."""
    if not host:
        return False
    name = host.strip().lower()
    if name in ("localhost", socket.gethostname().lower()):
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    if address.is_loopback or address.is_unspecified:
        return True
    family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
    try:
        # Binding a UDP socket checks address ownership locally without sending packets.
        with socket.socket(family, socket.SOCK_DGRAM) as endpoint:
            endpoint.bind((str(address), 0))
        return True
    except OSError:
        return False


def is_loopback_client(address) -> bool:
    """True for a loopback client, including an IPv4-mapped IPv6 address."""
    if not address:
        return False
    name = str(address).strip().lower()
    if name.startswith("::ffff:"):
        name = name[len("::ffff:"):]
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def console_host_names():
    """Names and addresses that identify this machine, without a public DNS lookup.

    The interface addresses are found by connecting an unbound UDP socket, which
    selects a source address and sends no packet.
    """
    names = {"localhost", "127.0.0.1", "::1", socket.gethostname().lower()}
    for family, probe_address in ((socket.AF_INET, "192.0.2.1"), (socket.AF_INET6, "2001:db8::1")):
        try:
            with socket.socket(family, socket.SOCK_DGRAM) as probe:
                probe.connect((probe_address, 9))
                names.add(probe.getsockname()[0])
        except OSError:
            continue
    return names


def allowed_host_names():
    """The Host header names the console accepts.

    A console that is published beyond loopback must also answer for the name
    or address it was published under. A loopback console keeps its strict list.
    """
    names = {"localhost", "127.0.0.1", "::1"}
    if ACCESS["required"]:
        names |= console_host_names()
    return names


def resolve_access_token(bind_host):
    """Return the access token for this console and whether one is required."""
    configured = (os.environ.get(ACCESS_TOKEN_ENV) or "").strip()
    if configured:
        return configured, True
    if is_loopback_client(bind_host):
        return "", False
    return secrets.token_urlsafe(32), True


def access_link_host(bind_host):
    """The address a published console is reached at, for the printed access link."""
    if bind_host not in ("0.0.0.0", "::", ""):
        return bind_host
    for family, probe_address in ((socket.AF_INET, "192.0.2.1"), (socket.AF_INET6, "2001:db8::1")):
        try:
            with socket.socket(family, socket.SOCK_DGRAM) as probe:
                probe.connect((probe_address, 9))
                address = probe.getsockname()[0]
            if not is_loopback_client(address):
                return address
        except OSError:
            continue
    return socket.gethostname().lower()


def redact_access_token(text):
    """Hide the access token in a request line before it is logged."""
    return re.sub(r"([?&]token=)[^&\s]*", r"\1<redacted>", str(text))


def check_tcp_port(host: str, port: int, timeout: float = 1.5):
    t0 = time.time()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            rtt_ms = round((time.time() - t0) * 1000, 1)
            return True, rtt_ms
    except Exception as e:
        return False, str(e)


def diagnostic_url(value):
    if not isinstance(value, str) or len(value) > 8192 or re.search(r"[\x00-\x20\x7f]", value):
        raise ValueError("请输入无空格和控制字符的 HTTP(S) URL")
    target = urllib.parse.urlsplit(value)
    if (target.scheme not in ("http", "https") or not target.hostname
            or target.username is not None or target.password is not None):
        raise ValueError("目标必须是无凭据的 HTTP 或 HTTPS URL")
    if target.port is not None and not 1 <= target.port <= 65535:
        raise ValueError("目标端口必须在 1 至 65535 之间")
    return target._replace(fragment="")


def diagnostic_command(payload):
    """Parse an HTTP GET description without invoking a shell or executable."""
    if not isinstance(payload, dict):
        raise ValueError("请求必须是 JSON 对象")
    if payload.get("target_url") and payload.get("command"):
        raise ValueError("请提供 target_url 或请求文本中的一个")
    text = payload.get("target_url") or payload.get("command", "")
    if not isinstance(text, str):
        raise ValueError("请求必须是 URL 或 curl GET 文本")
    if re.search(r"\$\(|\$\{|\x60|\n|\r", text):
        raise ValueError("请求中不支持 shell 插值或换行，请提供完整的单行 URL")
    text = text.strip()
    if text.startswith(("http://", "https://")):
        return {"url": urllib.parse.urlunsplit(diagnostic_url(text)), "method": "GET"}
    args = shlex.split(text, posix=True)
    if not args or args.pop(0).lower() not in ("curl", "curl.exe"):
        raise ValueError("此面板仅接受 HTTP(S) URL 或 curl GET 请求；其他业务命令请使用 CLI")
    urls = []
    method = "GET"
    options = {"-s", "-S", "-sS", "-L", "--silent", "--show-error", "--location"}
    while args:
        arg = args.pop(0)
        if arg in options:
            continue
        if arg in ("-I", "--head"):
            method = "HEAD"
            continue
        if arg in ("-X", "--request"):
            if not args or args[0] not in ("GET", "HEAD"):
                raise ValueError("仅支持 GET 或 HEAD 请求")
            method = args.pop(0)
            continue
        if arg in ("--url", "--"):
            if len(args) != 1:
                raise ValueError("请求必须包含一个 URL")
            urls.append(args.pop())
        elif arg.startswith(("http://", "https://")):
            urls.append(arg)
        else:
            raise ValueError("仅接受 URL、GET/HEAD 和 -s / -S / -L 显示选项")
    if len(urls) != 1:
        raise ValueError("请求必须包含一个 URL")
    return {"url": urllib.parse.urlunsplit(diagnostic_url(urls[0])), "method": method}


def check_http_target(name: str, target_info, proxy_url: str, timeout: float = 15.0, include_preview=False):
    if isinstance(target_info, dict):
        url = target_info.get("url", "")
        desc = target_info.get("desc", "")
        category = target_info.get("category", "")
    else:
        url = str(target_info)
        desc = ""
        category = ""

    started = time.monotonic()
    result = {"name": name, "url": url, "request_url": url, "final_url": url,
              "desc": desc, "category": category, "status": "offline", "proxy_url": proxy_url,
              "tcp_ok": False, "tcp_latency_ms": None, "path_verified": False, "response_received": False,
              "http_ok": False, "redirects": [], "code": None, "error_type": None,
              "tls_retries": 0, "tls_retry_reason": None, "attempts": [], "first_status": None,
              "final_status": None, "budget_ms": round(timeout * 1000), "budget_expired": False}
    conn = None
    attempt = None
    stage = "validation"

    def remaining_time():
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("代理请求超过总超时")
        return remaining

    try:
        target = diagnostic_url(url)
        proxy = urllib.parse.urlsplit(proxy_url)
        if (proxy.scheme != "http" or not proxy.hostname
                or proxy.username is not None or proxy.password is not None):
            raise ValueError("请使用无凭据的 HTTP 代理入口")
        seen = set()
        for hop in range(6):
            current = urllib.parse.urlunsplit(target)
            result.update(final_url=current, code=None, response_received=False)
            if current in seen:
                result.update(error_type="redirect_loop", error="目标出现重定向循环")
                break
            seen.add(current)
            for attempt_index in range(2):
                # Every hop and TLS retry uses the selected proxy and the same deadline.
                stage = "proxy_tcp"
                attempt_started = time.monotonic()
                attempt = {"hop": hop + 1, "attempt": attempt_index + 1, "url": current, "tcp_ok": False,
                           "connect_status": None, "tls": "not_reached" if target.scheme == "https" else "skipped",
                           "http_status": None, "elapsed_ms": None}
                result["attempts"].append(attempt)
                remaining = remaining_time()
                conn = http.client.HTTPConnection(proxy.hostname, proxy.port, timeout=remaining)
                if target.scheme == "https":
                    conn.set_tunnel(target.hostname, target.port or 443)
                    conn.sock = socket.create_connection((proxy.hostname, proxy.port or 80), remaining)
                else:
                    conn.connect()
                result["tcp_ok"] = True
                attempt["tcp_ok"] = True
                if result["tcp_latency_ms"] is None:
                    result["tcp_latency_ms"] = round((time.monotonic() - attempt_started) * 1000, 1)
                if target.scheme == "https":
                    stage = "proxy_tunnel"
                    conn.sock.settimeout(remaining_time())
                    conn._tunnel()
                    attempt["connect_status"] = 200
                    result["path_verified"] = True
                    stage = "tls"
                    try:
                        context = ssl.create_default_context()
                        conn.sock.settimeout(remaining_time())
                        conn.sock = context.wrap_socket(conn.sock, server_hostname=target.hostname)
                        attempt["tls"] = "passed"
                    except ssl.SSLEOFError as exc:
                        attempt["tls"] = "eof"
                        attempt["elapsed_ms"] = round((time.monotonic() - attempt_started) * 1000, 1)
                        conn.close()
                        conn = None
                        if result["tls_retries"]:
                            raise
                        remaining_time()
                        result.update(tls_retries=1, tls_retry_reason=str(exc))
                        continue
                break
            if target.scheme == "https":
                path = urllib.parse.urlunsplit(("", "", target.path or "/", target.query, ""))
            else:
                path = current
            path = urllib.parse.quote(path, safe="/:%?=&+#@!$'()*;,~-._[]")
            stage = "http_response"
            conn.sock.settimeout(remaining_time())
            conn.request("GET", path, headers={"Host": target.netloc, "User-Agent": "net-proxy-tool/1.4"})
            conn.sock.settimeout(remaining_time())
            response = conn.getresponse()
            attempt["http_status"] = response.status
            attempt["elapsed_ms"] = round((time.monotonic() - attempt_started) * 1000, 1)
            if result["first_status"] is None:
                result["first_status"] = response.status
            result.update(code=response.status, response_received=True, path_verified=True)
            location = response.getheader("Location")
            if response.status in (301, 302, 303, 307, 308) and location:
                result["redirects"].append({"url": current, "code": response.status, "location": location})
                if hop == 5:
                    result.update(error_type="redirect_limit", error="重定向超过 5 次")
                    break
                redirected = diagnostic_url(urllib.parse.urljoin(current, location))
                if target.scheme == "https" and redirected.scheme == "http":
                    result.update(error_type="redirect_downgrade", error="已拒绝 HTTPS 降级到 HTTP")
                    break
                target = redirected
                conn.close()
                conn = None
                continue
            result["final_status"] = response.status
            result["http_ok"] = 200 <= response.status < 300
            if result["http_ok"]:
                result["status"] = "online"
            else:
                result["error_type"] = "proxy_auth" if response.status == 407 else "http_status"
                result["error"] = f"HTTP {response.status} {response.reason}"
            if include_preview:
                stage = "response_body"
                content_type = response.headers.get_content_type()
                result["content_type"] = content_type
                if content_type.startswith("text/") or content_type in ("application/json", "application/xml"):
                    body = response.read(4097)
                    charset = response.headers.get_content_charset() or "utf-8"
                    try:
                        result["preview"] = body[:4096].decode(charset, errors="replace")
                    except LookupError:
                        result["preview"] = body[:4096].decode("utf-8", errors="replace")
                    result["preview_truncated"] = len(body) > 4096
                else:
                    result["preview"] = "二进制响应，未显示内容"
            break
    except ssl.SSLCertVerificationError as exc:
        attempt["tls"] = "certificate_error"
        result.update(error_type="tls_certificate", error=str(exc))
    except (TimeoutError, socket.timeout) as exc:
        result.update(error_type="timeout", error=str(exc))
        if stage == "tls" and attempt["tls"] != "eof":
            attempt["tls"] = "timeout"
    except (ValueError, OSError, http.client.HTTPException) as exc:
        result["error"] = str(exc)
        result["error_type"] = {"validation": "invalid_url", "proxy_tcp": "proxy_connection",
                                "proxy_tunnel": "proxy_tunnel", "tls": "tls_handshake"}.get(stage, "http_protocol")
        tunnel = re.match(r"Tunnel connection failed: (\d{3})\b", str(exc))
        if tunnel:
            result["code"] = int(tunnel[1])
            attempt["connect_status"] = result["code"]
            result["error_type"] = "proxy_auth" if result["code"] == 407 else "proxy_tunnel"
        elif stage == "tls" and attempt["tls"] == "not_reached":
            attempt["tls"] = "failed"
    finally:
        if conn is not None:
            conn.close()
    if result["error_type"] and not result["http_ok"]:
        result["status"] = "offline"
    result["stage"] = stage
    result["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
    if attempt is not None and attempt["elapsed_ms"] is None:
        attempt["elapsed_ms"] = round((time.monotonic() - attempt_started) * 1000, 1)
    result["budget_expired"] = result["error_type"] == "timeout" and time.monotonic() - started >= timeout
    return result


def run_diagnostic_request(request, proxy_url):
    """Run only the system curl with an explicit proxy and bounded read-only options."""
    if os.name == "nt":
        executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "curl.exe"
    else:
        executable = next((p for p in (Path("/usr/bin/curl"), Path("/bin/curl")) if p.is_file()), None)
    if executable is None or not executable.is_file():
        raise ValueError("未找到系统 curl，请使用首页的内置代理请求测试")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="net-proxy-request-") as temp:
        body_path, header_path = Path(temp) / "body", Path(temp) / "headers"
        command = [str(executable), "--disable", "--silent", "--show-error",
                   "--proxy", proxy_url, "--noproxy", "", "--proto", "=http,https",
                   "--proto-redir", "=https" if request["url"].startswith("https:") else "=http,https",
                   "--location", "--max-redirs", "5", "--connect-timeout", "4",
                   "--max-time", "12", "--max-filesize", "65536", "--limit-rate", "64k",
                   "--suppress-connect-headers", "--dump-header", str(header_path), "--output", str(body_path),
                   "--write-out", "%{http_code}\n%{url_effective}\n%{num_redirects}\n%{remote_ip}\n%{http_connect}"]
        if request["method"] == "HEAD":
            command.append("--head")
        command.extend(["--url", request["url"]])
        try:
            completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       timeout=14, shell=False, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return {"status": "offline", "success": False, "error_type": "timeout",
                    "error": "HTTP 请求超过总超时", "url": request["url"], "proxy_url": proxy_url}
        metadata = completed.stdout.decode("utf-8", errors="replace").splitlines()
        code = int(metadata[0]) if metadata and metadata[0].isdigit() and metadata[0] != "000" else None
        headers = header_path.read_bytes()[:16384].decode("iso-8859-1") if header_path.exists() else ""
        body = b""
        if body_path.exists():
            with body_path.open("rb") as stream:
                body = stream.read(4097)
        response_codes = re.findall(r"^HTTP/\S+ ([2-5]\d{2})", headers, flags=re.MULTILINE)
        tunnel_code = int(metadata[4]) if len(metadata) > 4 and metadata[4].isdigit() and metadata[4] != "000" else None
        final_code = code if not completed.returncode or code not in (301, 302, 303, 307, 308) else None
        ok = completed.returncode == 0 and code is not None and 200 <= code < 300
        result = {"status": "online" if ok else "offline", "success": ok, "http_ok": ok,
                  "url": request["url"], "request_url": request["url"],
                  "final_url": metadata[1] if len(metadata) > 1 else request["url"],
                  "proxy_url": proxy_url, "method": request["method"], "code": final_code or (tunnel_code if tunnel_code != 200 else None),
                  "first_status": int(response_codes[0]) if response_codes else None, "final_status": final_code,
                  "connect_status": tunnel_code, "response_received": final_code is not None,
                  "path_verified": bool(headers) or tunnel_code == 200,
                  "tcp_ok": bool(headers or tunnel_code) or bool(len(metadata) > 3 and metadata[3]),
                  "headers": headers, "preview": body[:4096].decode("utf-8", errors="replace"),
                  "preview_truncated": len(body) > 4096,
                  "redirect_count": int(metadata[2]) if len(metadata) > 2 and metadata[2].isdigit() else 0,
                  "exit_code": completed.returncode,
                  "latency_ms": round((time.monotonic() - started) * 1000, 1)}
        if not ok:
            result["error_type"] = {5: "proxy_connection", 7: "proxy_connection", 28: "timeout",
                                    35: "tls_handshake", 60: "tls_certificate", 47: "redirect_limit",
                                    63: "response_too_large"}.get(completed.returncode, "http_status")
            if result["code"] == 407:
                result["error_type"] = "proxy_auth"
            elif tunnel_code and tunnel_code != 200:
                result["error_type"] = "proxy_tunnel"
            result["error"] = completed.stderr[:2048].decode("utf-8", errors="replace").strip() or f"HTTP {code}"
        return result


def validate_host_port(host, port):
    host = text_field(host, "host", maximum=255, strip=True)
    port = integer_field(port, "port", 1, 65535)
    if not host:
        raise ValueError("请输入有效的代理主机名或 IP 地址")
    if ":" in host:
        address, sep, zone = host.partition("%")
        ipaddress.IPv6Address(address)
        if sep and not re.fullmatch(r"[A-Za-z0-9_.-]+", zone):
            raise ValueError("无效的 IPv6 区域标识")
    elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", host):
        raise ValueError("请输入有效的代理主机名或 IP 地址")
    return host, port


def gateway_url(gw):
    if not isinstance(gw, dict) or not gw:
        raise ValueError("请先添加 HTTP 代理网关")
    normalize_protocol(gw.get("protocol", "http"))
    host, port = validate_host_port(gw.get("host"), gw.get("port"))
    return proxy_url(host, port)


def validate_bypass(value):
    value = text_field(value, "no_proxy", maximum=4096)
    if not re.fullmatch(r"[\w.,*:/%\[\]-]*", value):
        raise ValueError("直连列表应为以逗号分隔的主机、IP 或网段")
    return value


def public_data(value):
    if isinstance(value, dict):
        return {key: public_data(child) for key, child in value.items()
                if key.lower() not in {"ssh_pass", "password", "token", "api_key", "private_key", "_node_baseline", "_node_restored_baseline"}}
    if isinstance(value, list):
        return [public_data(child) for child in value]
    return value


def ssh_with_script(command, script, timeout, env=None):
    # Remote sh expects LF regardless of the Windows controller's code page.
    result = subprocess.run(command, input=script.encode("utf-8"), capture_output=True, env=env, timeout=timeout)
    return subprocess.CompletedProcess(command, result.returncode, result.stdout.decode("utf-8", "replace"),
                                       result.stderr.decode("utf-8", "replace"))


def run_remote_ssh_script(host, port, user, auth_type, password, script, timeout=14, *, remote_command="sh"):
    """Authenticate one explicit identity against an already trusted OpenSSH host key."""
    port = int(port or 22)
    auth_type = (auth_type or ("password" if password else "key")).lower()
    validate_host_port(host, port)
    validate_ssh_destination(host, user or "")
    if auth_type not in ("password", "key"):
        raise ValueError("无效的 SSH 认证类型")
    cmd = ["ssh", "-p", str(port), "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=5",
           "-o", "NumberOfPasswordPrompts=1"]
    if auth_type == "password":
        cmd += ["-o", "BatchMode=no", "-o", "PreferredAuthentications=password",
                "-o", "PubkeyAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
                "-o", "PasswordAuthentication=yes", "-o", "ProxyCommand=none", "-o", "ProxyJump=none",
                "-o", "Hostname=" + host, "-o", "CanonicalizeHostname=no", "-o", "ControlPath=none",
                "-o", "ControlMaster=no", "-o", "PermitLocalCommand=no", "-o", "ClearAllForwardings=yes"]
        cmd += [f"{user}@{host}", remote_command]
        with password_environment(password) as env:
            return ssh_with_script(cmd, script, timeout, env)
    cmd += ["-o", "BatchMode=yes", "-o", "PasswordAuthentication=no",
            "-o", "KbdInteractiveAuthentication=no", f"{user}@{host}", remote_command]
    return ssh_with_script(cmd, script, timeout)


def generate_provisioning_script(proxy_url, no_proxy, action="on", owner=""):
    """Deploy a POSIX script with per-file snapshots and conflict detection."""
    if action not in ("on", "off"):
        raise ValueError("Invalid switch action")
    template = (WEB_DIR / "provision.sh").read_text(encoding="utf-8")
    return "action={}\nproxy={}\nbypass={}\n".format(
        action, shlex.quote(proxy_url), shlex.quote(validate_bypass(no_proxy))) + "npt_owner={}\n".format(shlex.quote(owner)) + template


def validate_ssh_destination(host, user, container=None):
    validate_host_port(host, 22)
    user = text_field(user, "ssh_user", maximum=128)
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]*", user):
        raise ValueError("无效的 SSH 用户名")
    if container is not None:
        container = text_field(container, "container_name", maximum=128)
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", container):
            raise ValueError("无效的 Docker 容器名称")


def docker_ssh_command(target, *command):
    host = target.get("ssh_host") or target.get("host") or "127.0.0.1"
    user = target.get("ssh_user") or "ubuntu"
    name = target.get("container_name") or target.get("name") or ""
    port = int(target.get("port") or 22)
    validate_host_port(host, port)
    validate_ssh_destination(host, user, name)
    remote = ["docker", *command, name]
    if command[0] == "exec":
        remote.append("sh")
    # OpenSSH passes the remote command to a shell, even when invoked with argv.
    return ["ssh", "-p", str(port), "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "ConnectTimeout=5", f"{user}@{host}", " ".join(map(shlex.quote, remote))]


def node_ssh_identity(target):
    """The complete destination that a saved credential is allowed to authenticate."""
    mode = (target.get("access_mode") or ("docker_host" if target.get("container_name") and not target.get("port") else "ssh")).lower()
    if mode == "local":
        identity = node_probe.local_identity()
        return ("local", "localhost", 0, identity["user"], identity["home"])
    host = (target.get("ssh_host") or target.get("host")) if mode == "docker_host" else target.get("host")
    user = target.get("ssh_user") or ("root" if mode != "docker_host" and target.get("os_type") == "docker" else "ubuntu")
    return (mode, host, int(target.get("port") or 22), user,
            target.get("container_name", "") if mode == "docker_host" else "")


def run_node_script(target, script, timeout=14):
    """Run a fixed node operation using the same saved identity and SSH trust policy."""
    mode, host, port, user, _ = node_ssh_identity(target)
    if mode == "local":
        if os.name == "nt":
            raise ValueError("Windows 本机请使用单命令或 PowerShell 会话代理")
        return subprocess.run(["sh"], input=script, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    auth_type = target.get("auth_type") or ("password" if target.get("ssh_pass") else "key")
    remote = "sh"
    if mode == "docker_host":
        remote = docker_ssh_command(target, "exec", "-i", "-u", "0")[-1]
    remote = "printf 'NPT_SSH_READY\\n'; " + remote
    return run_remote_ssh_script(host, port, user, auth_type, target.get("ssh_pass"), script,
                                 timeout, remote_command=remote)


def preflight_target(request):
    """Reuse a saved password only for that exact saved node destination."""
    target = dict(request)
    node_id = request.get("node_id") or request.get("id")
    if node_id:
        saved = next((node for node in load_config().get("clients", []) if node.get("id") == node_id), None)
        if saved:
            draft = dict(saved, **request)
            if not request.get("ssh_pass") and node_ssh_identity(draft) != node_ssh_identity(saved):
                raise ValueError("节点地址或身份已更改；请重新输入该目标的密码，不能复用原节点凭据")
            target = draft
            if saved.get("ssh_pass") and not request.get("ssh_pass"):
                target["ssh_pass"] = saved["ssh_pass"]
    return target


class NodeBindingConflict(ValueError):
    pass


def node_revision(target):
    return int(target.get("node_revision", 0))


def require_node_revision(target, request):
    if request.get("node_revision") != node_revision(target):
        raise NodeBindingConflict("节点记录已变化或缺少版本，请刷新后重试。")


def legacy_local_identity(target):
    return (not target.get("identity_version") and node_ssh_identity(target)[0] == "ssh"
            and int(target.get("port") or 22) == 22 and is_local_host(target.get("host")))


def require_execution_identity(target):
    if legacy_local_identity(target):
        raise ValueError("旧节点曾按本机地址推断执行位置；请编辑节点并明确选择本机或 SSH，再进行写入。")


def management_identity(target):
    mode, host, port, user, container = node_ssh_identity(target)
    if mode == "local":
        return mode, user, container
    host = (host or "").lower().rstrip(".")
    return (mode, host, port, container, "root") if mode == "docker_host" else (mode, host, port, user)


def unique_node_identity(target, cfg, excluding=None):
    identity = management_identity(target)
    for other in cfg.get("clients", []):
        if other.get("id") != excluding and management_identity(other) == identity:
            raise NodeBindingConflict("该执行账号/容器已由节点 {} 登记，请编辑现有节点。".format(other.get("id")))


def node_public_state(target):
    result = dict(target)
    if target.get("access_mode") == "local":
        result["os_type"] = "windows" if os.name == "nt" else "macos" if sys.platform == "darwin" else "linux"
    result.setdefault("node_revision", 0)
    result.setdefault("managed_state", "unknown")
    result["identity_confirmation_required"] = legacy_local_identity(target)
    return result


def update_node_outcome(target, action, result):
    target["node_revision"] = node_revision(target) + 1
    target["managed_state"] = result.get("managed_state", "unknown")
    target["verification"] = result.get("verification", {"verified": False, "status": "unknown"})
    if result.get("returncode") == 0:
        target["is_proxy_enabled"] = action == "on"
        target["applied_gateway_id"] = target.get("bound_gateway_id") if action == "on" else None
        target.pop("pending_action", None)
        target["lifecycle_version"] = 1
        if action == "off":
            if result.get("_node_baseline"):
                target["_node_restored_baseline"] = result["_node_baseline"]
            target.pop("_node_baseline", None)
            target.pop("applied_identity", None)
        else:
            target.pop("_node_restored_baseline", None)
    if result.get("_node_baseline") is not None and not (action == "off" and result.get("returncode") == 0):
        target["_node_baseline"] = result["_node_baseline"]


def needs_node_restoration(target):
    return bool(target.get("is_proxy_enabled") or target.get("pending_action") or target.get("_node_baseline")
                or target.get("_node_restored_baseline")
                or target.get("managed_state") == "enabled" or not target.get("lifecycle_version"))


def archived_node(target):
    # Deleted records retain no authentication material, baseline, or environment copy.
    allowed = ("id", "name", "host", "port", "os_type", "access_mode", "ssh_host", "ssh_user",
               "container_name", "bound_gateway_id", "node_revision")
    return {key: copy.deepcopy(target[key]) for key in allowed if key in target}


def selected_node_gateway(target, cfg, request):
    """Reject an action from a page whose saved node selection has changed."""
    bound = target.get("bound_gateway_id") or ""
    if "gateway_id" in request and request["gateway_id"] != bound:
        raise NodeBindingConflict("节点绑定已变化，请刷新并重新保存所选网关。")
    if "gateway_id" in request and not bound:
        raise ValueError("请先选择并保存节点绑定的网关。")
    if "binding_revision" in request and request["binding_revision"] != target.get("binding_revision", 0):
        raise NodeBindingConflict("节点绑定版本已变化，请刷新后重试。")
    return resolve_gateway_info(cfg, bound)


def validate_client(target, cfg=None):
    if not isinstance(target, dict):
        raise ValueError("node must be an object")
    mode = text_field(target.get("access_mode", "ssh"), "access_mode", maximum=32)
    if mode not in ("ssh", "docker_host", "local"):
        raise ValueError("请选择 SSH、Docker 宿主机或明确的本机执行模式。")
    auth_type = text_field(target.get("auth_type", "key"), "auth_type", maximum=32)
    if auth_type not in ("key", "password"):
        raise ValueError("请选择密钥或密码认证。")
    host, port = validate_host_port(target.get("host"), target.get("port", 22))
    if mode == "local" and not is_local_host(host):
        raise ValueError("本机模式仅接受控制台所在机器的地址。")
    if mode == "docker_host":
        ssh_host = target.get("ssh_host") or host
        validate_host_port(ssh_host, port)
        validate_ssh_destination(ssh_host, target.get("ssh_user") or "ubuntu",
                                 target.get("container_name") or "")
    elif mode != "local":
        validate_ssh_destination(host, target.get("ssh_user") or "root")
    if cfg is not None and target.get("bound_gateway_id"):
        bound = text_field(target["bound_gateway_id"], "bound_gateway_id", maximum=128)
        if not resolve_gateway_info(cfg, bound):
            raise ValueError("绑定的网关不存在，请重新选择并保存。")
    return target


def apply_node_proxy(target, action, cfg):
    """Journal the baseline before writing, then verify using the same execution identity."""
    require_execution_identity(target)
    mode = node_ssh_identity(target)[0]
    if mode == "local" and os.name == "nt":
        return {"returncode": 1, "managed_state": "unknown", "error": "Windows 本机请使用单命令或 PowerShell 会话代理"}
    if action not in ("on", "off"):
        raise ValueError("无效的节点操作")
    bound = (target.get("applied_gateway_id") or target.get("bound_gateway_id")) if action == "off" else target.get("bound_gateway_id")
    gateway = resolve_gateway_info(cfg, bound) if bound else {}
    if action == "on" and not gateway:
        raise ValueError("开启前必须选择并保存此节点的网关绑定。")
    result = {"action": action, "node_id": target.get("id"), "access_mode": mode,
              "returncode": 1, "managed_state": "unknown"}
    try:
        if target.get("applied_identity") and tuple(target["applied_identity"]) != node_ssh_identity(target):
            return dict(result, error="已保存的托管执行身份与当前目标不一致；未执行写入，请先恢复原身份。")
        baseline = target.get("_node_baseline")
        restored = None
        known_states = ("enabled", "disabled", "partial", "conflict")
        if baseline:
            if not baseline.get("execution_identity"):
                return dict(result, error="已保存的恢复基线缺少执行身份；未执行配置写入，登记保留。")
            current = node_baseline.capture_node_baseline(target, run_node_script, gateway)
            if not current.get("ok") or current.get("execution_identity") != baseline["execution_identity"]:
                return dict(result, error="实际登录账号、UID、HOME 或 shell 已变化或无法核验；未执行配置写入，原基线保留。")
            current_state = current.get("managed", {}).get("state")
            if current_state not in known_states:
                return dict(result, error="无法确认当前托管状态；未执行配置写入，原基线保留。")
            if action == "off" and current_state == "disabled":
                # The prior off may have committed before its verification failed.
                # Re-check the preserved evidence instead of re-running a legacy guard.
                restored = baseline
        if action == "off" and not baseline:
            restored = target.get("_node_restored_baseline")
        if restored:
            baseline = restored
        if not baseline:
            baseline = node_baseline.capture_node_baseline(target, run_node_script, gateway)
            if not baseline.get("ok"):
                return dict(result, error="无法读取节点基线；尚未执行配置写入。")
            if baseline.get("managed", {}).get("state") not in known_states:
                return dict(result, error="节点托管状态未知；尚未执行配置写入，登记保留。")
            if action == "off" and not (baseline.get("managed", {}).get("state") in ("enabled", "partial", "conflict")
                                      and baseline.get("managed", {}).get("restoration_manifest")):
                return dict(result, error="缺少启用前基线或可核验的旧快照；未写入配置，无法宣称已恢复，登记保留。")
        if not restored:
            result["_node_baseline"] = baseline
            target["_node_baseline"] = baseline
            target["pending_action"] = action
            target["managed_state"] = "unknown"
            target["applied_identity"] = list(node_ssh_identity(target))
            # A failed local save must prevent the remote side effect. On interruption
            # this persisted baseline makes the operation recoverable after restart.
            if any(item is target for item in cfg.get("clients", [])):
                save_config(cfg)
        script = generate_provisioning_script(gateway_url(gateway) if action == "on" else "",
                                             cfg.get("no_proxy", "localhost,127.0.0.1"), action,
                                             owner=target.get("id", ""))
        completed = (subprocess.CompletedProcess([], 0, "", "") if restored else
                     run_node_script(target, node_baseline.wrap_login_script(script), timeout=25))
        if completed.returncode:
            detail = completed.stderr.lower()
            reason = ("目标配置存在人工修改；请保留修改并核对快照。" if "edited since" in detail else
                      "此执行上下文由其它节点持有；未覆盖其配置。" if "owner" in detail else
                      "旧配置没有可用恢复快照；请先核对基线。" if "legacy" in detail else
                      "节点配置操作未完成；保留登记与快照供恢复。")
            return dict(result, error=reason)
        if action == "on":
            observed = node_baseline.inspect_node_state(target, run_node_script, gateway)
            identity_ok = baseline.get("execution_identity") == observed.get("execution_identity")
            owner_ok = observed.get("managed", {}).get("owner_node_id") == target.get("id")
            proxy_variables = observed.get("login", {}).get("proxy_variables", {})
            login_ok = all(proxy_variables.get(key, {}).get("matches_selected_gateway") for key in
                           ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"))
            verified = bool(observed.get("ok") and observed.get("managed", {}).get("state") == "enabled"
                            and identity_ok and owner_ok and login_ok)
            verification = {"verified": verified, "status": "enabled" if verified else "unknown",
                            "verification_scope": "login_and_managed_files", "checks": {"managed_enabled": verified,
                            "identity": identity_ok, "owner": owner_ok, "login_proxy": login_ok}}
            result.update(managed_state="enabled" if verified else "unknown", verification=verification)
        else:
            verification = node_baseline.verify_node_baseline(target, baseline, run_node_script, gateway)
            verified = bool(verification.get("verified"))
            safe_verification = {key: verification.get(key) for key in
                                 ("verified", "status", "verification_scope", "checks")}
            variables = verification.get("observation", {}).get("login", {}).get("proxy_variables", {})
            present = [value for key, value in variables.items() if key.lower() != "no_proxy" and value.get("present")]
            matches = any(value.get("matches_selected_gateway") for value in present)
            environment = {"context": "fresh_login_shell", "proxy_present": bool(present),
                           "matches_selected_gateway": matches, "observed": bool(variables)}
            if matches and gateway:
                environment["matched_gateway"] = {key: gateway[key] for key in ("id", "host", "port") if key in gateway}
            safe_verification["restored_environment"] = environment
            result.update(managed_state="disabled" if verified else "unknown", verification=safe_verification)
        if verified:
            result["returncode"] = 0
            result["_node_baseline"] = baseline
        else:
            result["error"] = "配置脚本已结束，但独立登录核验尚未确认结果；登记与恢复基线已保留。"
    except Exception:
        result["error"] = "无法完成节点操作或核验；未删除登记，恢复信息已保留。"
    return result


def check_node_http(target, gateway=None, target_url=None):
    """Run one curl process so native redirect rules preserve account credentials safely."""
    url = node_probe.validate_url(target_url or DEFAULT_TEST_URL)
    mode = target.get("access_mode") or ("docker_host" if target.get("container_name") and not target.get("port") else "ssh")
    local = mode == "local"
    transport = "local" if local else ("ssh_docker_exec" if mode == "docker_host" else "ssh")
    started = time.monotonic()
    stages = {"ssh": "skipped" if local else "not_reached",
              "docker_exec": "not_reached" if mode == "docker_host" else "skipped",
              "curl": "not_reached", "tcp": "not_reached", "tls": "not_reached", "http": "not_reached"}
    result = {"online": False, "success": False, "http_ok": False, "business_ok": None,
              "business_auth": {"status": "not_checked"}, "latency_ms": None, "transport": transport,
              "request_mode": "explicit_proxy" if gateway else "ordinary_request", "target_url": url,
              "request_url": url, "final_url": node_probe.safe_url(url), "gateway_id": gateway.get("id") if gateway else None,
              "stages": stages, "auth_ok": None, "first_status": None, "final_status": None,
              "code": None, "redirects": [], "hops": [], "error_type": None,
              "execution_identity": {}, "peer": {"ip": None, "port": None}, "connect_status": None,
              "proxy_evidence": {"status": "unknown", "source": "curl_peer"},
              "exit_evidence": {"status": "not_checked"},
              "tls_policy": "curl_defaults" if gateway else "account_configuration",
              "is_proxy_enabled": bool(target.get("is_proxy_enabled"))}
    result["execution_context"] = "controller_process" if local and os.name == "nt" else "fresh_login_shell"
    proxy = gateway_url(gateway) if gateway else None
    if proxy:
        result["proxy_url"] = proxy
    try:
        executable = "curl.exe" if local and os.name == "nt" else "curl"
        if local and os.name == "nt":
            with tempfile.TemporaryDirectory(prefix="npt-curl-headers-") as temporary:
                headers = Path(temporary) / "headers"
                command = node_probe.curl_command(executable, url, proxy, output=os.devnull, headers=str(headers))
                res = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=22)
                if headers.is_file():
                    res.stdout += "\n" + node_probe.filter_headers(headers.read_text(encoding="iso-8859-1"))
            identity = node_probe.local_identity()
        else:
            command = node_probe.curl_command(executable, url, proxy)
            res = run_node_script(target, node_baseline.wrap_login_script(node_probe.remote_script(command)), timeout=30)
            if not local:
                stages["ssh"] = "passed" if "NPT_SSH_READY" in res.stdout else "failed"
                result["auth_ok"] = stages["ssh"] == "passed"
            if mode == "docker_host":
                stages["docker_exec"] = "passed" if "NPT_EXEC_READY" in res.stdout else "failed"
            identity = None
        observed = node_probe.parse_output(res.stdout)
        result.update(exit_code=res.returncode, final_url=observed["final_url"] or node_probe.safe_url(url),
                      code=observed["code"], final_status=observed["code"], peer=observed["peer"],
                      connect_status=observed["connect_status"], ssl_verify_result=observed["ssl_verify_result"])
        result["execution_identity"] = identity if local and os.name == "nt" else observed["execution_identity"]
        result["execution_identity"]["curl_config_loaded"] = bool(
            not gateway and result["execution_identity"].get("curl_config"))
        responses = observed["responses"]
        result["first_status"] = responses[0]["code"] if responses else observed["code"]
        current = node_probe.safe_url(url)
        for index, response in enumerate(responses):
            final = index == len(responses) - 1 and response["code"] == observed["code"]
            result["hops"].append({"url": current, "code": response["code"],
                                   "peer": observed["peer"] if final else {"ip": None, "port": None}})
            if response.get("location") and response["code"] in (301, 302, 303, 307, 308):
                redirected = node_probe.safe_url(urllib.parse.urljoin(current, response["location"]))
                result["redirects"].append({"url": current, "code": response["code"], "location": redirected})
                current = redirected
        stages["curl"] = "passed" if observed["metrics_received"] else "failed"
        stages["tcp"] = "passed" if observed["peer"]["ip"] else "failed" if observed["metrics_received"] else "not_reached"
        error_type = node_probe.curl_error(res.returncode, observed["connect_status"])
        is_https = urllib.parse.urlsplit(result["final_url"]).scheme == "https"
        stages["tls"] = ("failed" if error_type in ("tls_handshake", "tls_certificate") else
                         "skipped" if not is_https else "passed" if observed["code"] else "not_reached")
        stages["http"] = "passed" if observed["code"] else "not_reached"
        if not local and not result["auth_ok"]:
            error_type, message = node_probe.ssh_error(res.stderr)
            result.update(error_type=error_type, error=message)
        elif mode == "docker_host" and stages["docker_exec"] != "passed":
            result.update(error_type="docker_exec", error="容器执行通道未就绪")
        elif res.returncode:
            if res.returncode == 1 and result["redirects"]:
                error_type = "redirect_policy"
            elif res.returncode == 67 and result["redirects"]:
                error_type = "redirect_credentials"
            # curl can include URLs or credentials from account configuration in stderr.
            result.update(error_type=error_type, error="curl 未完成请求 (exit {})".format(res.returncode))
        elif not observed["metrics_received"]:
            result.update(error_type="curl_output", error="curl 未返回可解析的请求结果")
        else:
            result["online"] = bool(observed["code"] and 200 <= observed["code"] < 300)
            if not result["online"]:
                result.update(error_type="proxy_auth" if observed["code"] == 407 else "http_status",
                              error="HTTP " + str(observed["code"] or "无响应"))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result.update(error_type="timeout" if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)) else "execution",
                      error="节点执行超时" if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)) else "无法执行节点探测")
        if not local and stages["ssh"] != "passed":
            stages["ssh"] = "failed"
            result["auth_ok"] = False
    result["success"] = result["http_ok"] = result["online"]
    if result["code"] in (401, 403):
        result["business_ok"] = False
        result["business_auth"] = {"status": "denied"}
    result["proxy_evidence"]["peer"] = result["peer"]
    if gateway:
        result["proxy_evidence"]["expected_proxy"] = {"host": gateway["host"], "port": int(gateway["port"])}
        if result["peer"]["ip"] and result["peer"]["port"] == int(gateway["port"]):
            result["proxy_evidence"]["status"] = "selected_proxy"
    result["status_line"] = ("HTTP " + str(result["code"])) if result["code"] else result.get("error", "未收到 HTTP 响应")
    result["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
    return result

def check_node_requests(target, gateway, target_url):
    gateway = gateway or {}
    ordinary = check_node_http(target, target_url=target_url)
    explicit = check_node_http(target, gateway, target_url) if gateway else {
        "online": False, "success": False, "http_ok": False, "business_ok": None,
        "error": "请先保存节点绑定的网关。", "stages": {}, "request_mode": "explicit_proxy",
        "status_line": "尚未绑定网关", "proxy_evidence": {"status": "unknown"}}
    observed = ordinary.get("peer") or {}
    expected = explicit.get("peer") or {}
    if observed.get("ip") and expected.get("ip") and observed.get("port") and expected.get("port"):
        ordinary.setdefault("proxy_evidence", {}).update(
            status="matches_explicit_peer" if observed == expected else "different_peer",
            source="curl_peer", peer=observed,
            expected_proxy={"host": gateway["host"], "port": int(gateway["port"])})
    return dict(ordinary, success=explicit["online"] and ordinary["online"], node_id=target.get("id"),
                gateway_id=gateway.get("id"), binding_revision=target.get("binding_revision", 0),
                node_revision=node_revision(target), managed_state=target.get("managed_state", "unknown"),
                verification=target.get("verification", {"verified": False, "status": "unknown"}),
                explicit_proxy=explicit, ordinary_request=ordinary,
                message="指定网关请求：{}；节点普通请求：{}".format(explicit["status_line"], ordinary["status_line"]))



class ProxyConsoleHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def setup(self):
        super().setup()
        self.connection.settimeout(REQUEST_TIMEOUT_SECONDS)

    def log_request(self, code="-", size="-"):
        # The access link carries the token in the query string; it must not
        # reach the console log.
        self.log_message('"%s" %s %s', redact_access_token(self.requestline), str(code), str(size))

    def cookie_value(self, name):
        for part in (self.headers.get("Cookie", "") or "").split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return ""

    def send_access_granted(self, token):
        self.send_response(302)
        self.send_header("Location", "/")
        self.send_header("Set-Cookie", "{}={}; HttpOnly; SameSite=Strict; Path=/".format(
            ACCESS_COOKIE_NAME, token))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_access_denied(self):
        body = ("This console requires an access token. Open the access link printed in the "
                "console log, or set NET_PROXY_ACCESS_TOKEN and restart the console.\n"
                "此控制台需要访问令牌。请打开控制台日志中打印的访问链接，"
                "或设置 NET_PROXY_ACCESS_TOKEN 后重启控制台。\n").encode("utf-8")
        self.send_response(401)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorize_access(self):
        """Allow loopback clients; require the access token from everyone else."""
        if not ACCESS["required"]:
            return True
        if is_loopback_client(self.client_address[0]):
            return True
        token = ACCESS["token"]
        cookie = self.cookie_value(ACCESS_COOKIE_NAME)
        if cookie and hmac.compare_digest(cookie, token):
            return True
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("", "/"):
            supplied = (urllib.parse.parse_qs(parsed.query).get("token") or [""])[0]
            if supplied and hmac.compare_digest(supplied, token):
                self.send_access_granted(token)
            else:
                self.send_access_denied()
            return False
        self.send_access_denied()
        return False

    def write_audit(self, action, node_id="-", status="info", details=""):
        """Record an audit entry for the client that made this request."""
        address = getattr(self, "client_address", None)
        write_audit_log(action, node_id, status, details,
                        operator_ip=address[0] if address else "127.0.0.1")

    def end_headers(self):
        # 强制所有静态文件与动态接口下发防缓存头，杜绝浏览器脏缓存假死
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        super().end_headers()

    def send_json(self, data, status_code=200):
        payload = json.dumps(public_data(data), ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_text(self, text, content_type="text/plain; charset=utf-8", status_code=200):
        payload = text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_internal_error(self, exc):
        error_id = secrets.token_hex(8)
        print("[Internal Error {}] {}".format(error_id, type(exc).__name__), file=sys.stderr)
        frames = traceback.format_tb(exc.__traceback__)
        if frames:
            print("".join(frames).rstrip(), file=sys.stderr)
        self.send_json({"success": False, "error": "Internal server error", "error_id": error_id}, 500)

    def read_json_body(self):
        if hasattr(self, "_request_json"):
            return self._request_json
        transfer_encoding = self.headers.get_all("Transfer-Encoding", [])
        if transfer_encoding:
            self.close_connection = True
            raise RequestError(400, "Transfer-Encoding is not supported")
        content_types = self.headers.get_all("Content-Type", [])
        if len(content_types) > 1:
            self.close_connection = True
            raise RequestError(400, "At most one Content-Type header is allowed")
        if not content_types or self.headers.get_content_type() != "application/json":
            self.close_connection = True
            raise RequestError(415, "Content-Type must be application/json")
        length_headers = self.headers.get_all("Content-Length", [])
        if len(length_headers) != 1:
            self.close_connection = True
            raise RequestError(400, "Exactly one Content-Length header is required")
        raw_length = length_headers[0]
        if not re.fullmatch(r"\d+", raw_length.strip()):
            self.close_connection = True
            raise RequestError(400, "Content-Length must be a non-negative integer")
        content_length = int(raw_length)
        if content_length > MAX_JSON_BODY_BYTES:
            self.close_connection = True
            raise RequestError(413, "请求体过大")
        if content_length == 0:
            return {}
        try:
            post_data = self.rfile.read(content_length).decode("utf-8")
        except UnicodeDecodeError:
            raise RequestError(400, "请求体必须是 UTF-8 JSON")
        try:
            data = json.loads(post_data)
        except (ValueError, RecursionError):
            raise RequestError(400, "请求体包含无效 JSON")
        if not isinstance(data, dict):
            raise RequestError(400, "请求体必须是 JSON 对象")
        return data

    def parse_request(self):
        if not super().parse_request():
            return False
        host = self.headers.get("Host", "")
        try:
            parsed = urllib.parse.urlsplit("//" + host)
            if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
                raise ValueError()
            allowed = allowed_host_names() | {self.connection.getsockname()[0]}
            # A published container port can be forwarded from a different local IP.
            if parsed.hostname not in allowed:
                raise ValueError()
            origin = self.headers.get("Origin")
            if origin and origin.lower() not in ("http://" + host.lower(), "https://" + host.lower()):
                raise ValueError()
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                raise ValueError()
        except ValueError:
            self.close_connection = True
            self.send_error(403, "Untrusted Host or Origin")
            return False
        if not self.authorize_access():
            return False
        return True

    def do_GET(self):
        try:
            self.serve_get()
        except RequestError as exc:
            self.send_json({"success": False, "error": str(exc)}, exc.status_code)
        except ValueError as exc:
            self.send_json({"success": False, "error": str(exc)}, 400)
        except (socket.timeout, TimeoutError):
            self.close_connection = True
        except Exception as exc:
            self.send_internal_error(exc)

    def serve_get(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("", "/"):
            self.path = "/index.html"
            return super().do_GET()

        if path in ("/proxy-on", "/proxy-off", "/container-init.sh"):
            # Off also works after the configured gateway has been deleted.
            proxy, bypass = "", ""
            if path != "/proxy-off":
                cfg = load_config()
                proxy = gateway_url(resolve_gateway_info(cfg))
                bypass = validate_bypass(cfg.get("no_proxy", "localhost,127.0.0.1"))
            functions = (WEB_DIR / "session_switch.sh").read_text(encoding="utf-8")
            if path == "/container-init.sh":
                template = (WEB_DIR / "container_helpers.sh").read_text(encoding="utf-8")
                script = template.replace("@FUNCTIONS@", functions)
            else:
                action = "npt_proxy_on" if path == "/proxy-on" else "npt_proxy_off"
                script = functions + "\n" + action + "\nunset -f npt_proxy_on npt_proxy_off\n"
            self.send_text(script.replace("@PROXY@", shlex.quote(proxy)).replace("@BYPASS@", shlex.quote(bypass)))
            return

        if path == "/api/health":
            token = os.environ.get("NET_PROXY_INSTANCE_TOKEN", "")
            self.send_json({"status": "ok", "version": VERSION, "service": "net-proxy-tool",
                            "pid": os.getpid(), "instance_id": hashlib.sha256(token.encode()).hexdigest() if token else ""})
            return

        if path == "/api/config":
            cfg = load_config()
            self.send_json(dict(cfg, clients=[node_public_state(node) for node in cfg.get("clients", [])], default_test_url=DEFAULT_TEST_URL))
            return

        if path == "/api/audit-logs":
            self.send_json({"success": True, "logs": get_audit_logs(60)})
            return

        if path == "/api/status":
            self.handle_api_status(parsed.query)
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        handlers = {
            "/api/config": self.handle_save_config,
            "/api/shutdown": self.handle_shutdown,
            "/api/set-active-gateway": self.handle_set_active_gateway,
            "/api/test-gateway": self.handle_test_gateway,
            "/api/test-host": self.handle_test_host,
            "/api/test-node-preflight": self.handle_test_node_preflight,
            "/api/clients/add": self.handle_client_add,
            "/api/clients/update": self.handle_client_update,
            "/api/clients/delete": self.handle_client_delete,
            "/api/node-switch": self.handle_node_switch,
            "/api/nodes/batch-switch": self.handle_batch_switch,
            "/api/nodes/health-check-all": self.handle_nodes_health_check_all,
            "/api/node-test": self.handle_node_test,
            "/api/gateways/add": self.handle_gateway_add,
            "/api/gateways/update": self.handle_gateway_update,
            "/api/gateways/delete": self.handle_gateway_delete,
            "/api/run": self.handle_api_run
        }

        if path in handlers:
            try:
                self._request_json = validate_api_payload(path, self.read_json_body())
                # Serialize read-modify-write updates, including switch results.
                if path in ("/api/config", "/api/set-active-gateway", "/api/node-switch", "/api/nodes/batch-switch") or path.startswith(("/api/clients/", "/api/gateways/")):
                    with CONFIG_WRITE_LOCK:
                        handlers[path]()
                else:
                    handlers[path]()
            except RequestError as exc:
                self.send_json({"success": False, "error": str(exc)}, status_code=exc.status_code)
            except NodeBindingConflict as exc:
                self.send_json({"success": False, "error": str(exc), "binding_changed": True}, status_code=409)
            except (ValueError, KeyError) as exc:
                self.send_json({"success": False, "error": str(exc)}, status_code=400)
            except (socket.timeout, TimeoutError):
                self.close_connection = True
            except Exception as exc:
                self.send_internal_error(exc)
            finally:
                if hasattr(self, "_request_json"):
                    del self._request_json
            return

        self.send_error(404, "Not Found")

    def handle_shutdown(self):
        self.read_json_body()
        expected = os.environ.get("NET_PROXY_INSTANCE_TOKEN")
        supplied = self.headers.get("X-Net-Proxy-Token", "")
        if not ipaddress.ip_address(self.client_address[0]).is_loopback or not expected or not hmac.compare_digest(supplied, expected):
            self.send_json({"success": False, "error": "Instance token required"}, 403)
            return
        self.send_json({"success": True})
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def handle_api_status(self, query_string):
        query = urllib.parse.parse_qs(query_string)
        gid = query.get("gateway_id", [None])[0]

        cfg = load_config()
        report = diagnostics.status_report(cfg, gid, tcp_probe=check_tcp_port,
                                           target_probe=check_http_target)
        if report["gateway"] is None:
            self.send_json(dict(report, error="未找到网关，请先在首页保存 HTTP 代理网关。"),
                           404 if gid else 200)
            return
        self.send_json(report)

    def handle_save_config(self):
        req_json = self.read_json_body()
        cfg = load_config()
        if set(req_json) != {"no_proxy"}:
            raise ValueError("此接口只接受 no_proxy")
        cfg["no_proxy"] = validate_bypass(req_json["no_proxy"])
        save_config(cfg)
        self.send_json({"success": True, "message": "配置保存成功", "config": cfg})

    def handle_set_active_gateway(self):
        req_json = self.read_json_body()
        gid = req_json.get("gateway_id")
        cfg = load_config()
        if not any(g.get("id") == gid for g in cfg.get("gateways", [])):
            raise ValueError("网关不存在")
        cfg["active_gateway_id"] = gid
        # Update is_default property in gateways list
        for g in cfg.get("gateways", []):
            g["is_default"] = (g.get("id") == gid)
        save_config(cfg)
        self.send_json({"success": True, "active_gateway_id": gid})

    def handle_test_gateway(self):
        req_json = self.read_json_body()
        host, port = validate_host_port(req_json.get("host"), req_json.get("port", 0))
        protocol = normalize_protocol(req_json.get("protocol", "http"))
        proxy = gateway_url({"host": host, "port": port, "protocol": protocol})
        url = req_json.get("target_url") or DEFAULT_TEST_URL
        diagnostic_url(url)
        result = check_http_target("HTTP probe", url, proxy)
        online = result["status"] == "online"
        self.send_json(dict(result, success=online, online=online))

    def handle_test_host(self):
        req_json = self.read_json_body()
        host, port = validate_host_port(req_json.get("host"), req_json.get("port", 22))
        ok, rtt_or_err = check_tcp_port(host, port, timeout=2.0)
        self.send_json({"success": True, "online": ok, "latency_ms": rtt_or_err if ok else None, "error": None if ok else str(rtt_or_err)})

    def handle_test_node_preflight(self):
        """
        Three-stage deep preflight check:
        1. TCP socket connect + RTT measurement
        2. SSH protocol banner handshake
        3. Real credential authentication test (Password via ASKPASS or Key via BatchMode)
        """
        req_json = preflight_target(self.read_json_body())
        host = req_json.get("host", "").strip()
        port = int(req_json.get("port") or 22)
        access_mode = req_json.get("access_mode", "ssh").strip().lower()
        auth_type = (req_json.get("auth_type") or ("password" if req_json.get("ssh_pass") else "key")).strip().lower()
        if auth_type not in ("key", "password"):
            raise ValueError("无效的 SSH 认证类型")
        user = node_ssh_identity(req_json)[3]
        password = req_json.get("ssh_pass", "")
        container_name = req_json.get("container_name", "").strip()
        ssh_host = req_json.get("ssh_host", "").strip() or host

        if access_mode == "local":
            validate_client(dict(req_json, host=host or "localhost", access_mode="local"))
            if os.name == "nt":
                self.send_json({"success": True, "auth_ok": None, "execution_identity": node_probe.local_identity(),
                                "message": "本机模式使用控制台账号，不进行 SSH 登录；Windows 请使用单命令代理。"})
            else:
                observed = node_baseline.capture_node_baseline(req_json, run_node_script)
                self.send_json({"success": observed.get("ok", False), "auth_ok": None,
                                "execution_identity": observed.get("execution_identity", {}),
                                "message": "已核对本机执行账号。" if observed.get("ok") else "无法核对本机登录环境。"})
            return

        if access_mode == "docker_host":
            validate_host_port(ssh_host, port)
            validate_ssh_destination(ssh_host, user, container_name)
            ok, rtt_or_err = check_tcp_port(ssh_host, port, timeout=2.5)
            if not ok:
                self.send_json({
                    "success": False,
                    "tcp_ok": False,
                    "message": f"❌ 宿主机网络不可达 ({ssh_host}:{port}): {rtt_or_err}"
                })
                return
            try:
                cmd = docker_ssh_command(dict(req_json, ssh_host=ssh_host, ssh_user=user), "inspect", "-f", "{{.State.Running}}")
                res = run_remote_ssh_script(ssh_host, port, user, auth_type, password, "", timeout=6, remote_command=cmd[-1])
                if res.returncode == 0 and "true" in res.stdout.lower():
                    self.send_json({
                        "success": True,
                        "tcp_ok": True,
                        "latency_ms": rtt_or_err,
                        "auth_ok": True,
                        "message": f"🟢 宿主机已连通 ({rtt_or_err}ms)，且 Docker 容器【{container_name}】正在健康运行中！"
                    })
                else:
                    detail = res.stderr.strip().splitlines()[-1:] if res.stderr else []
                    if res.returncode == 255:
                        reason = "SSH 连接、主机密钥核验或所选身份认证失败"
                    elif res.returncode:
                        reason = "无法检查容器，请核对名称及远程账号的 Docker 权限"
                    else:
                        reason = "目标容器已停止"
                    self.send_json({
                        "success": False, "tcp_ok": True, "latency_ms": rtt_or_err,
                        "auth_ok": res.returncode != 255, "container_running": False,
                        "message": reason + (" · " + detail[0][:300] if detail else ""),
                    })
            except Exception as e:
                self.send_json({"success": False, "tcp_ok": True, "message": f"⚠️ 容器探测异常: {e}"})
            return

        if not host:
            self.send_json({"success": False, "message": "❌ 请提供主机 IP"}, status_code=400)
            return

        # 1. TCP Connect
        t0 = time.time()
        validate_host_port(host, port)
        validate_ssh_destination(host, user)
        try:
            sock = socket.create_connection((host, port), timeout=3.0)
            rtt_ms = round((time.time() - t0) * 1000, 1)
        except Exception as e:
            self.send_json({
                "success": False,
                "tcp_ok": False,
                "message": f"❌ 网络连接被拒绝 ({host}:{port}): 目标主机离线或端口未映射"
            })
            return

        # 2. SSH Banner check
        ssh_banner = ""
        try:
            sock.settimeout(2.0)
            data = sock.recv(256)
            banner_str = data.decode("utf-8", errors="replace").strip()
            if banner_str.startswith("SSH-"):
                ssh_banner = banner_str.split("\n")[0]
        except Exception:
            pass
        finally:
            try: sock.close()
            except Exception: pass

        # 3. Credential Auth Test
        auth_ok = False
        auth_msg = ""
        try:
            if auth_type == "password":
                res = run_remote_ssh_script(host, port, user, "password", password, "true", timeout=6)
                if res.returncode == 0:
                    auth_ok = True
                    auth_msg = "密码认证成功，预检已完成"
                else:
                    auth_msg = f"初始密码错误或被拒: {res.stderr.strip() or 'Permission denied'}"
            else:
                res = run_remote_ssh_script(host, port, user, "key", None, "true", timeout=5)
                if res.returncode == 0:
                    auth_ok = True
                    auth_msg = "SSH 密钥免密验证通过"
                else:
                    auth_msg = f"免密未生效: {res.stderr.strip() or 'Permission denied (publickey)'}"
        except Exception as e:
            auth_msg = f"SSH 连接探测异常: {e}"

        banner_info = f" [{ssh_banner}]" if ssh_banner else ""
        if auth_ok:
            msg = f"🟢 深度预检完全通过！TCP ({rtt_ms}ms) + SSH协议握手{banner_info} + {auth_msg}"
        else:
            msg = f"⚠️ 物理网络通畅{banner_info}，但{auth_msg}！"

        self.send_json({
            "success": auth_ok,
            "tcp_ok": True,
            "latency_ms": rtt_ms,
            "ssh_banner": ssh_banner,
            "auth_ok": auth_ok,
            "auth_msg": auth_msg,
            "message": msg
        })


    def handle_client_add(self):
        request = self.read_json_body()
        cfg = load_config()
        fields = ("id", "name", "host", "port", "os_type", "access_mode", "auth_type", "ssh_user", "ssh_pass",
                  "ssh_host", "container_name", "bound_gateway_id", "tags", "description")
        target = {key: copy.deepcopy(request[key]) for key in fields if key in request}
        if not target.get("name") or not target.get("host"):
            raise ValueError("节点名称和主机地址不能为空")
        target.setdefault("access_mode", "ssh")
        target.setdefault("auth_type", "key")
        target.setdefault("port", 22)
        target.setdefault("os_type", "linux")
        target.setdefault("bound_gateway_id", "")
        target["port"] = int(target["port"])
        validate_client(target, cfg)
        identity = management_identity(target)
        for existing in cfg.get("clients", []):
            if management_identity(existing) == identity:
                self.send_json({"success": True, "existing": True, "client": node_public_state(existing),
                                "message": "该执行身份已经登记，原记录、绑定和状态均已保留；修改请使用编辑。"})
                return
        archived = next((item for item in cfg.get("archived_clients", [])
                         if management_identity(item) == identity), None)
        if archived:
            current_auth = {key: target[key] for key in ("auth_type", "ssh_user", "ssh_pass") if key in target}
            target = dict(archived_node(archived), **target)
            target["id"] = archived["id"]
            target.update(current_auth)
            if not request.get("bound_gateway_id"):
                previous = archived.get("bound_gateway_id")
                target["bound_gateway_id"] = previous if previous and resolve_gateway_info(cfg, previous) else ""
        if not target.get("id"):
            slug = re.sub(r"[^a-zA-Z0-9-]", "", target["host"].replace(".", "-")) or "local"
            suffix = str(target["port"]) + ("-" + target.get("container_name", "") if target["access_mode"] == "docker_host" else "")
            stem = "node-{}-{}".format(slug, suffix)
            target["id"] = stem
            used = {item.get("id") for item in cfg.get("clients", [])}
            index = 2
            while target["id"] in used:
                target["id"] = stem + "-" + str(index)
                index += 1
        if any(item.get("id") == target["id"] for item in cfg.get("clients", [])):
            raise NodeBindingConflict("节点 ID 已存在，请更换。")
        if target.get("access_mode") == "local" or target.get("auth_type") == "key":
            target.pop("ssh_pass", None)
        if target.get("access_mode") == "local":
            target["auth_type"] = "key"
        if target.get("auth_type") == "password" and not target.get("ssh_pass"):
            raise ValueError("请为当前身份重新输入密码；已删除节点的凭据不会恢复。")
        target.update(identity_version=1, lifecycle_version=1, node_revision=int(target.get("node_revision", -1)) + 1,
                      is_proxy_enabled=False, managed_state="unknown")
        target["verification"] = {"verified": False, "status": "unknown", "verification_scope": "not_checked"}
        cfg.setdefault("clients", []).append(target)
        if archived:
            cfg["archived_clients"] = [item for item in cfg.get("archived_clients", []) if item is not archived]
        save_config(cfg)
        self.write_audit("client_add", target["id"], "success", "节点登记已保存")
        self.send_json({"success": True, "restored_registration": bool(archived), "client": node_public_state(target),
                        "message": "原节点登记和可用绑定已恢复；认证资料使用本次输入。" if archived else "节点登记已保存，尚未开启代理。"})

    def handle_client_update(self):
        request = self.read_json_body()
        cfg = load_config()
        target = next((item for item in cfg.get("clients", []) if item.get("id") == request.get("id")), None)
        if target is None:
            self.send_json({"success": False, "error": "节点不存在"}, 404)
            return
        require_node_revision(target, request)
        draft = copy.deepcopy(target)
        allowed = ("name", "host", "port", "os_type", "access_mode", "auth_type", "ssh_user", "ssh_host",
                   "container_name", "bound_gateway_id", "tags", "description")
        for key in allowed:
            if key in request:
                draft[key] = copy.deepcopy(request[key])
        if request.get("ssh_pass"):
            draft["ssh_pass"] = request["ssh_pass"]
        draft["port"] = int(draft.get("port") or 22)
        validate_client(draft, cfg)
        unique_node_identity(draft, cfg, excluding=target["id"])
        old_identity, new_identity = node_ssh_identity(target), node_ssh_identity(draft)
        if legacy_local_identity(target):
            if not request.get("confirm_execution_mode") or draft.get("access_mode") != "local":
                raise ValueError("此旧记录此前按本机执行。请先明确保存为本机模式并完成恢复，再改为 SSH 身份。")
            if (int(draft.get("port") or 22) != int(target.get("port") or 22)
                    or any(draft.get(key) != target.get(key) for key in ("host", "container_name"))):
                raise ValueError("确认旧本机执行位置时，请先保留原地址与账号字段。")
            if "ssh_user" in target:
                draft["ssh_user"] = target["ssh_user"]
            else:
                draft.pop("ssh_user", None)
            draft["identity_version"] = 1
            old_identity = new_identity
        if draft.get("access_mode") == "local" or draft.get("auth_type") == "key":
            draft.pop("ssh_pass", None)
        if target.get("ssh_pass") and draft.get("auth_type") == "password" and draft.get("access_mode") != "local" and old_identity != new_identity and not request.get("ssh_pass"):
            raise ValueError("节点地址或身份已更改；请重新输入该目标的密码，不能复用原节点凭据")
        if old_identity != new_identity and needs_node_restoration(target):
            result = apply_node_proxy(target, "off", cfg)
            update_node_outcome(target, "off", result)
            save_config(cfg)
            if result.get("returncode") != 0:
                self.send_json({"success": False, "error": result.get("error"), "client": node_public_state(target),
                                "message": "原身份未确认恢复，节点身份没有修改。"}, 502)
                return
            for key in ("_node_baseline", "_node_restored_baseline", "pending_action", "applied_identity", "applied_gateway_id"):
                draft.pop(key, None)
            draft.update(is_proxy_enabled=False, managed_state="unknown", lifecycle_version=1,
                         verification={"verified": False, "status": "unknown"})
        if draft.get("bound_gateway_id", "") != target.get("bound_gateway_id", ""):
            draft["binding_revision"] = target.get("binding_revision", 0) + 1
            draft["managed_state"] = "unknown"
            draft["verification"] = {"verified": False, "status": "unknown", "verification_scope": "binding_changed"}
        draft["node_revision"] = node_revision(target) + 1
        draft.setdefault("identity_version", 1)
        target.clear()
        target.update(draft)
        save_config(cfg)
        self.write_audit("client_update", target["id"], "success", "节点登记已更新")
        self.send_json({"success": True, "client": node_public_state(target), "message": "节点登记已更新。"})

    def handle_client_delete(self):
        request = self.read_json_body()
        cfg = load_config()
        target = next((item for item in cfg.get("clients", []) if item.get("id") == request.get("id")), None)
        if target is None:
            self.send_json({"success": False, "error": "节点不存在"}, 404)
            return
        require_node_revision(target, request)
        if needs_node_restoration(target):
            result = apply_node_proxy(target, "off", cfg)
            update_node_outcome(target, "off", result)
            save_config(cfg)
            if result.get("returncode") != 0:
                self.send_json({"success": False, "error": result.get("error"), "client": node_public_state(target),
                                "message": "恢复未核验通过，节点登记和认证资料仍保留。"}, 502)
                return
        archive = archived_node(target)
        cfg["archived_clients"] = [item for item in cfg.get("archived_clients", []) if item.get("id") != target["id"]] + [archive]
        cfg["clients"] = [item for item in cfg["clients"] if item is not target]
        save_config(cfg)
        self.write_audit("client_delete", target["id"], "success", "节点登记已移除，认证资料已删除")
        self.send_json({"success": True, "id": target["id"], "message": "节点登记已移除，认证资料已删除；仅保留加回所需的非敏感登记信息。"})

    def handle_node_switch(self):
        request = self.read_json_body()
        cfg = load_config()
        target = next((item for item in cfg.get("clients", []) if item.get("id") == request.get("node_id")), None)
        if target is None:
            self.send_json({"success": False, "error": "节点不存在"}, 404)
            return
        require_node_revision(target, request)
        action = request.get("action", "on")
        if action not in ("on", "off"):
            raise ValueError("无效的节点操作")
        if action == "on":
            selected_node_gateway(target, cfg, request)
            if not target.get("bound_gateway_id"):
                raise ValueError("开启前必须保存此节点的网关绑定。")
        result = apply_node_proxy(target, action, cfg)
        update_node_outcome(target, action, result)
        save_config(cfg)
        ok = result.get("returncode") == 0
        self.write_audit("node_switch_" + action, target["id"], "success" if ok else "failed",
                         "节点操作已核验" if ok else "核验未确认，登记保留")
        self.send_json({"success": ok, "node_id": target["id"], "action": action,
                        "node_revision": node_revision(target), "binding_revision": target.get("binding_revision", 0),
                        "gateway_id": target.get("bound_gateway_id"), "is_proxy_enabled": target.get("is_proxy_enabled", False),
                        "managed_state": target["managed_state"], "verification": target["verification"],
                        "dispatch_result": result, "error": result.get("error"),
                        "message": ("已核验托管配置开启。" if action == "on" else "已核验恢复启用前基线，原有代理仍可能生效。") if ok else result.get("error")}, 200 if ok else 502)

    def handle_batch_switch(self):
        request = self.read_json_body()
        action, selections = request.get("action"), request.get("nodes")
        if action not in ("on", "off") or not isinstance(selections, list) or not selections:
            raise ValueError("批量操作必须明确提交节点列表和各自版本。")
        cfg = load_config()
        selected, ids = [], set()
        # Validate the whole selection before the first target can be changed.
        for selection in selections:
            if not isinstance(selection, dict) or selection.get("node_id") in ids:
                raise ValueError("批量节点列表包含无效或重复条目")
            target = next((item for item in cfg.get("clients", []) if item.get("id") == selection.get("node_id")), None)
            if target is None:
                raise NodeBindingConflict("批量列表中的节点已移除，请刷新。")
            require_node_revision(target, selection)
            require_execution_identity(target)
            if action == "on":
                selected_node_gateway(target, cfg, selection)
                if not target.get("bound_gateway_id"):
                    raise ValueError("开启前每个节点都必须保存网关绑定。")
            ids.add(target["id"])
            selected.append(target)
        results = []
        for target in selected:
            try:
                result = apply_node_proxy(target, action, cfg)
            except Exception:
                result = {"returncode": 1, "error": "节点操作未完成，登记保留。", "managed_state": "unknown"}
            update_node_outcome(target, action, result)
            save_config(cfg)
            ok = result.get("returncode") == 0
            results.append({"node_id": target["id"], "name": target.get("name", target["id"]), "success": ok,
                            "managed_state": target["managed_state"], "verification": target["verification"],
                            "node_revision": node_revision(target), "error": result.get("error")})
            self.write_audit("batch_" + action, target["id"], "success" if ok else "failed",
                             "已核验" if ok else "未核验")
        count = sum(item["success"] for item in results)
        self.send_json({"success": count == len(results), "action": action, "results": results,
                        "total": len(results), "success_count": count,
                        "message": "已核验完成 {}/{} 个明确选择节点的操作。".format(count, len(results))})

    def handle_nodes_health_check_all(self):
        """Inspect ordinary and explicitly proxied requests without changing node state."""
        request = self.read_json_body()
        url = node_probe.validate_url(request.get("target_url") or DEFAULT_TEST_URL)
        cfg = load_config()
        clients = cfg.get("clients", [])
        def check_one(target):
            gateway = resolve_gateway_info(cfg, target["bound_gateway_id"]) if target.get("bound_gateway_id") else {}
            return target.get("id"), check_node_requests(target, gateway, url)
        with ThreadPoolExecutor(max_workers=5) as executor:
            health_map = dict(executor.map(check_one, clients))
        current = load_config()
        for target in clients:
            present = next((item for item in current.get("clients", []) if item.get("id") == target.get("id")), None)
            if (present is None or node_revision(present) != node_revision(target) or present.get("bound_gateway_id") != target.get("bound_gateway_id")
                    or present.get("binding_revision", 0) != target.get("binding_revision", 0)
                    or resolve_gateway_info(current, target.get("bound_gateway_id")) != resolve_gateway_info(cfg, target.get("bound_gateway_id"))):
                health_map[target["id"]].update(binding_changed=True, online=False, success=False,
                                                error="巡检期间节点绑定已变化，请重新测试。")
        passed = sum(bool(item.get("success")) for item in health_map.values())
        outcome = "success" if passed == len(clients) else "partial" if passed else "failed"
        self.write_audit("health_check_all", "-", outcome,
                         f"巡检完成，{passed}/{len(clients)} 个节点两路 HTTP 请求成功")
        self.send_json({"success": True, "completed": True, "all_http_ok": passed == len(clients),
                        "health_map": health_map, "target_url": url, "total": len(clients),
                        "http_success_count": sum(bool(item.get("online")) for item in health_map.values()),
                        "both_paths_success_count": passed,
                        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")})


    def handle_node_test(self):
        req_json = self.read_json_body()
        node_id = req_json.get("node_id", "").strip()
        cfg = load_config()
        target = None
        for c in cfg.get("clients", []):
            if c.get("id") == node_id:
                target = c
                break

        if not target:
            self.send_json({"success": False, "error": f"未找到ID为 '{node_id}' 的节点"}, status_code=404)
            return

        gateway = selected_node_gateway(target, cfg, req_json)
        url = node_probe.validate_url(req_json.get("target_url") or DEFAULT_TEST_URL)
        result = check_node_requests(target, gateway, url)
        current = load_config()
        present = next((item for item in current.get("clients", []) if item.get("id") == node_id), None)
        if (present is None or node_revision(present) != node_revision(target) or present.get("bound_gateway_id") != target.get("bound_gateway_id")
                or present.get("binding_revision", 0) != target.get("binding_revision", 0)
                or resolve_gateway_info(current, target.get("bound_gateway_id")) != gateway):
            raise NodeBindingConflict("测试期间节点绑定已变化，请重新测试。")
        self.send_json(result)

    def handle_gateway_add(self):
        req_json = self.read_json_body()
        gid = text_field(req_json.get("id", ""), "id", maximum=128, strip=True)
        name = text_field(req_json.get("name", ""), "name", maximum=255, strip=True)
        host, port = validate_host_port(req_json.get("host"), req_json.get("port", 7890))
        protocol = normalize_protocol(req_json.get("protocol", "http"))
        desc = text_field(req_json.get("description", ""), "description", maximum=4096, strip=True)

        if not name:
            self.send_json({"success": False, "error": "网关名称和IP不能为空"}, status_code=400)
            return

        cfg = load_config()
        gateways = cfg.get("gateways", [])
        values = {"name": name, "host": host, "port": port, "protocol": protocol, "description": desc}
        gateway_url(values)
        # Identical retries reuse their saved identity, including when the first response was lost.
        for g in gateways:
            if (not gid or g.get("id") == gid) and all(g.get(key, "") == value for key, value in values.items()):
                self.send_json({"success": True, "message": "代理网关已存在", "gateway": g})
                return
        if not gid:
            safe_slug = re.sub(r"[^a-zA-Z0-9-]", "", host.replace(".", "-")) or "gateway"
            base = f"gw-{safe_slug}"
            used = {g.get("id") for g in gateways}
            gid = base
            if gid in used:
                base = f"{base}-{port}"
                gid = base
                suffix = 2
                while gid in used:
                    gid = f"{base}-{suffix}"
                    suffix += 1
        for g in gateways:
            if g.get("id") == gid:
                self.send_json({"success": False, "error": f"网关ID '{gid}' 已存在"}, status_code=400)
                return

        new_gw = {
            "id": gid,
            "name": name,
            "host": host,
            "port": port,
            "protocol": protocol,
            "description": desc,
            "is_default": False
        }
        gateway_url(new_gw)
        if not gateways:
            cfg["active_gateway_id"] = gid
            new_gw["is_default"] = True
        gateways.append(new_gw)
        cfg["gateways"] = gateways
        save_config(cfg)
        self.send_json({"success": True, "message": "代理网关添加成功", "gateway": new_gw})

    def handle_gateway_update(self):
        req_json = self.read_json_body()
        gid = text_field(req_json.get("id", ""), "id", maximum=128, strip=True)
        if not gid:
            self.send_json({"success": False, "error": "网关ID不能为空"}, status_code=400)
            return

        cfg = load_config()
        gateways = cfg.get("gateways", [])
        target = None
        for gateway in gateways:
            if gateway.get("id") == gid:
                target = gateway
                break

        if not target:
            self.send_json({"success": False, "error": f"未找到ID为 '{gid}' 的网关"}, status_code=404)
            return

        previous_endpoint = tuple(str(target.get(key, "http" if key == "protocol" else "")).strip().lower()
                                  if key == "protocol" else str(target.get(key, "")).strip()
                                  for key in ("host", "port", "protocol"))
        draft = copy.deepcopy(target)
        if "name" in req_json:
            draft["name"] = text_field(req_json["name"], "name", maximum=255, strip=True)
        if "host" in req_json:
            draft["host"] = text_field(req_json["host"], "host", maximum=255, strip=True)
        if "port" in req_json:
            draft["port"] = integer_field(req_json["port"], "port", 1, 65535)
        if "protocol" in req_json:
            draft["protocol"] = normalize_protocol(req_json["protocol"])
        if "description" in req_json:
            draft["description"] = text_field(req_json["description"], "description", maximum=4096,
                                               strip=True)

        draft["host"], draft["port"] = validate_host_port(draft.get("host"), draft.get("port"))
        draft["protocol"] = normalize_protocol(draft.get("protocol", "http"))
        gateway_url(draft)
        endpoint = tuple(str(draft.get(key, "http" if key == "protocol" else ""))
                         for key in ("host", "port", "protocol"))
        target.clear()
        target.update(draft)
        if previous_endpoint != endpoint:
            for node in cfg.get("clients", []):
                if node.get("bound_gateway_id") == gid:
                    node["node_revision"] = node_revision(node) + 1
                    node["binding_revision"] = node.get("binding_revision", 0) + 1
                    node["managed_state"] = "unknown"
                    node["verification"] = {"verified": False, "status": "unknown", "verification_scope": "gateway_changed"}
        save_config(cfg)
        self.send_json({"success": True, "message": "代理网关更新成功", "gateway": target})

    def handle_gateway_delete(self):
        req_json = self.read_json_body()
        gid = req_json.get("id", "").strip()
        if not gid:
            self.send_json({"success": False, "error": "网关ID不能为空"}, status_code=400)
            return

        cfg = load_config()
        if gid == cfg.get("active_gateway_id"):
            self.send_json({"success": False, "error": "不能删除当前正处于激活状态的默认网关，请先切换默认网关"}, status_code=400)
            return
        if any(node.get("bound_gateway_id") == gid for node in cfg.get("clients", [])):
            raise NodeBindingConflict("仍有节点绑定此网关，请先保存这些节点的新绑定。")

        gateways = cfg.get("gateways", [])
        new_gateways = [g for g in gateways if g.get("id") != gid]

        if len(new_gateways) == len(gateways):
            self.send_json({"success": False, "error": f"未找到ID为 '{gid}' 的网关"}, status_code=404)
            return

        cfg["gateways"] = new_gateways
        save_config(cfg)
        self.send_json({"success": True, "message": "代理网关删除成功", "id": gid})

    def handle_api_run(self):
        payload = self.read_json_body()
        request = diagnostic_command(payload)
        cfg = load_config()
        gw = resolve_gateway_info(cfg, payload.get("gateway_id"))
        proxy = gateway_url(gw)
        result = run_diagnostic_request(request, proxy)
        self.close_connection = True
        self.send_response(200)
        self.send_header("Connection", "close")
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.end_headers()
        events = [
            {"type": "start", "command": request["method"] + " " + request["url"],
             "gateway": f"{gw['name']} ({proxy})", "time": time.strftime("%H:%M:%S")},
            {"type": "result", **result},
            {"type": "stdout", "line": result.get("headers", "")},
            {"type": "stdout", "line": result.get("preview", "")},
            {"type": "finish", "exit_code": 0 if result.get("success") else 1,
             "msg": "HTTP 请求完成" if result.get("success") else result.get("error", "请求失败")},
        ]
        for event in events:
            self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
        self.wfile.flush()


def run_server(port=None, bind=None):
    cfg = load_config()
    port = port if port is not None else int(cfg.get("web_port", 8899))
    host = bind or os.environ.get("NET_PROXY_BIND", "127.0.0.1")
    token, required = resolve_access_token(host)
    ACCESS.update(token=token, required=required)
    warning = config_permission_warning()
    if warning:
        print(warning, file=sys.stderr, flush=True)
    with ThreadingHTTPServer((host, port), ProxyConsoleHandler) as httpd:
        print(f"net-proxy-tool | http://{host}:{httpd.server_port}", flush=True)
        if required and not ACCESS["printed"]:
            ACCESS["printed"] = True
            print("net-proxy-tool | access link: http://{}:{}/?token={}".format(
                access_link_host(host), httpd.server_port, token), flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description="Start the net-proxy-tool web console")
    parser.add_argument("legacy_port", nargs="?", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int)
    parser.add_argument("--bind", help="Listen address (default: 127.0.0.1)")
    args = parser.parse_args()
    try:
        run_server(args.port if args.port is not None else args.legacy_port, args.bind)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"net-proxy-tool: {exc}\n")


if __name__ == "__main__":
    main()
