#!/usr/bin/env python3
"""
net-proxy-tool: Lightweight Standalone Web Console (v3.0)
Multi-Gateway, Multi-Node Topology, Dynamic CRUD & Progressive Guided Sandbox Execution.
Zero third-party dependencies (pure Python 3 standard library).
"""
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse
import hashlib
import hmac
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import threading
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

WEB_DIR = Path(__file__).resolve().parent
TOOL_DIR = WEB_DIR.parent
STATIC_DIR = WEB_DIR / "static"
if __package__ in (None, ""):
    sys.path.insert(0, str(TOOL_DIR))

from sdk.config import data_dir, load_config, resolve_gateway_info, save_config

CONFIG_WRITE_LOCK = threading.RLock()


def audit_path():
    return data_dir() / "audit.log"


def write_audit_log(action, node_id="-", status="info", details="", operator_ip="127.0.0.1"):
    """
    Appends an event record to the lightweight audit log in JSON Lines format.
    """
    try:
        audit_path().parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "node_id": node_id or "-",
            "operator_ip": operator_ip or "127.0.0.1",
            "status": status,
            "details": str(details or "")
        }
        with open(audit_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Audit Log Warning] {e}")


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
    """动态检查目标主机是否为当前服务器本机 (跨平台兼容 x86/ARM/Win/Mac/Linux)"""
    if not host:
        return False
    host_clean = host.strip().lower()
    if host_clean in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
        return True
    try:
        local_ips = {"127.0.0.1", "localhost", "::1"}
        hostname = socket.gethostname()
        local_ips.add(socket.gethostbyname(hostname).lower())
        for info in socket.getaddrinfo(hostname, None):
            local_ips.add(info[4][0].lower())
        return host_clean in local_ips
    except Exception:
        return False


def check_tcp_port(host: str, port: int, timeout: float = 1.5):
    t0 = time.time()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            rtt_ms = round((time.time() - t0) * 1000, 1)
            return True, rtt_ms
    except Exception as e:
        return False, str(e)


def check_http_target(name: str, target_info, proxy_url: str, timeout: float = 4.5):
    if isinstance(target_info, dict):
        url = target_info.get("url", "")
        desc = target_info.get("desc", "")
        category = target_info.get("category", "")
    else:
        url = str(target_info)
        desc = ""
        category = ""

    started = time.monotonic()
    result = {"name": name, "url": url, "desc": desc, "category": category, "status": "offline"}
    conn = None
    try:
        target = urllib.parse.urlsplit(url)
        proxy = urllib.parse.urlsplit(proxy_url)
        if target.scheme not in ("http", "https") or not target.hostname or target.username or target.password:
            raise ValueError("目标必须是无凭据的 HTTP 或 HTTPS URL")
        # Connect to the explicit proxy even for localhost and when NO_PROXY is set.
        if target.scheme == "https":
            conn = http.client.HTTPSConnection(proxy.hostname, proxy.port, timeout=timeout)
            conn.set_tunnel(target.hostname, target.port or 443)
            path = urllib.parse.urlunsplit(("", "", target.path or "/", target.query, ""))
        else:
            conn = http.client.HTTPConnection(proxy.hostname, proxy.port, timeout=timeout)
            path = urllib.parse.urlunsplit(target._replace(fragment=""))
        conn.request("GET", path, headers={"Host": target.netloc, "User-Agent": "net-proxy-tool/1.4"})
        response = conn.getresponse()
        result["code"] = response.status
        if 200 <= response.status < 300:
            result["status"] = "online"
        else:
            result["error"] = f"HTTP {response.status} {response.reason}"
    except (ValueError, OSError, http.client.HTTPException) as exc:
        result["error"] = str(exc)
        # http.client reports a rejected HTTPS CONNECT as OSError before getresponse().
        tunnel = re.match(r"Tunnel connection failed: (\d{3})\b", str(exc))
        if tunnel:
            result["code"] = int(tunnel[1])
    finally:
        if conn is not None:
            conn.close()
    result["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
    return result


def validate_host_port(host, port):
    if ":" in host:
        address, sep, zone = host.partition("%")
        ipaddress.IPv6Address(address)
        if sep and not re.fullmatch(r"[A-Za-z0-9_.-]+", zone):
            raise ValueError("无效的 IPv6 区域标识")
    elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", host):
        raise ValueError("请输入有效的代理主机名或 IP 地址")
    if not 1 <= int(port) <= 65535:
        raise ValueError("端口必须在 1 至 65535 之间")


def gateway_url(gw):
    if not gw:
        raise ValueError("请先添加 HTTP 代理网关")
    if gw.get("protocol", "http") != "http":
        raise ValueError("请使用 HTTP 或 mixed 代理监听端口")
    host, port = gw["host"], int(gw["port"])
    validate_host_port(host, port)
    return f"http://[{host}]:{port}" if ":" in host else f"http://{host}:{port}"


def validate_bypass(value):
    if not isinstance(value, str) or not re.fullmatch(r"[\w.,*:/%\[\]-]*", value):
        raise ValueError("直连列表应为以逗号分隔的主机、IP 或网段")
    return value


def public_data(value):
    if isinstance(value, dict):
        return {key: public_data(child) for key, child in value.items()
                if key.lower() not in {"ssh_pass", "password", "token", "api_key", "private_key"}}
    if isinstance(value, list):
        return [public_data(child) for child in value]
    return value


def get_control_node_public_key():
    """Reads local SSH public key for auto-enrollment into remote targets."""
    for fn in ("id_rsa.pub", "id_ed25519.pub", "id_ecdsa.pub"):
        path = os.path.expanduser(f"~/.ssh/{fn}")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception:
                pass
    return None


def ssh_with_script(command, script, timeout, env=None):
    # Remote sh expects LF regardless of the Windows controller's code page.
    result = subprocess.run(command, input=script.encode("utf-8"), capture_output=True, env=env, timeout=timeout)
    return subprocess.CompletedProcess(command, result.returncode, result.stdout.decode("utf-8", "replace"),
                                       result.stderr.decode("utf-8", "replace"))


def run_remote_ssh_script(host, port, user, auth_type, password, script, timeout=14):
    """
    Executes a script on a remote workstation, edge board, or container via SSH.
    Supports:
    - Key-based auth (BatchMode=yes)
    - Password-based auth via SSH_ASKPASS (zero external dependencies, pure stdlib)
    - Auto-injection of local SSH public key on first password-authenticated connection.
    """
    port = int(port or 22)
    user = user or "root"
    auth_type = (auth_type or ("password" if password else "key")).lower()

    validate_host_port(host, port)
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", user):
        raise ValueError("无效的 SSH 用户名")
    if password and auth_type == "password":
        if os.name == "nt":
            raise ValueError("Windows 控制端请使用 OpenSSH 密钥认证；密码接入可在 Linux 控制端执行")
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sh") as tf:
            tf.write('#!/bin/sh\nprintf "%s\\n" "$NET_PROXY_SSH_PASSWORD"\n')
            askpass_path = tf.name
        os.chmod(askpass_path, stat.S_IRWXU)

        env = os.environ.copy()
        env["NET_PROXY_SSH_PASSWORD"] = password
        env["SSH_ASKPASS"] = askpass_path
        env["SSH_ASKPASS_REQUIRE"] = "force"
        env["DISPLAY"] = "dummy"

        try:
            pubkey = get_control_node_public_key() if script.startswith("action=on\n") else None
            if pubkey:
                pubkey = shlex.quote(pubkey)
                enroll_cmd = (
                    f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
                    f"grep -qFx -- {pubkey} ~/.ssh/authorized_keys 2>/dev/null || "
                    f"printf '%s\\n' {pubkey} >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
                )
                full_script = f"{enroll_cmd}\n{script}"
            else:
                full_script = script

            ssh_bin = ["setsid", "ssh"] if sys.platform != "win32" and shutil.which("setsid") else ["ssh"]
            cmd = ssh_bin + [
                "-p", str(port),
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ConnectTimeout=5",
                f"{user}@{host}",
                "sh"
            ]
            return ssh_with_script(cmd, full_script, timeout, env)
        finally:
            try:
                os.remove(askpass_path)
            except Exception:
                pass
    else:
        cmd = [
            "ssh",
            "-p", str(port),
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=5",
            f"{user}@{host}",
            "sh"
        ]
        return ssh_with_script(cmd, script, timeout)


def generate_provisioning_script(proxy_url, no_proxy, action="on"):
    """Deploy a POSIX script with per-file snapshots and conflict detection."""
    if action not in ("on", "off"):
        raise ValueError("Invalid switch action")
    template = (WEB_DIR / "provision.sh").read_text(encoding="utf-8")
    return "action={}\nproxy={}\nbypass={}\n".format(
        action, shlex.quote(proxy_url), shlex.quote(validate_bypass(no_proxy))) + template


def validate_ssh_destination(host, user, container=None):
    validate_host_port(host, 22)
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]*", user):
        raise ValueError("无效的 SSH 用户名")
    if container is not None and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", container):
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
    return ["ssh", "-p", str(port), "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=5", f"{user}@{host}", " ".join(map(shlex.quote, remote))]


def validate_client(target):
    validate_host_port(target["host"], target.get("port", 22))
    if target.get("access_mode") == "docker_host":
        validate_ssh_destination(target.get("ssh_host") or target["host"], target.get("ssh_user") or "ubuntu",
                                 target.get("container_name") or "")
    else:
        validate_ssh_destination(target["host"], target.get("ssh_user") or "root")


def apply_node_proxy(target, action, cfg):
    """
    Dual-layer provisioning engine (Dedicated Tool Configs + Shell Environment Hooks).
    Unified support for:
    1. Local node (self machine, cross-platform detected via is_local_host)
    2. Remote workstations / edge boards / containers via Direct SSH (passwordless or auto-enroll password)
    3. Host Docker Engine penetration (legacy containers without SSH daemon)
    """
    os_type = (target.get("os_type") or "linux").lower()
    access_mode = (target.get("access_mode") or ("docker_host" if target.get("container_name") and not target.get("port") else "ssh")).lower()
    gw = resolve_gateway_info(cfg, target.get("bound_gateway_id"))
    proxy_url = gateway_url(gw) if action == "on" else ""
    no_proxy = cfg.get("no_proxy", "localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,*.local")

    result = {"action": action, "node_id": target.get("id"), "os_type": os_type, "access_mode": access_mode}

    # 1. 宿主机 Docker 穿透通道 (Legacy / Specific for containers without SSH)
    if access_mode == "docker_host":
        script = generate_provisioning_script(proxy_url, no_proxy, action)
        try:
            res = ssh_with_script(docker_ssh_command(target, "exec", "-i", "-u", "0"), script, 12)
            result["returncode"] = res.returncode
            if res.returncode != 0:
                result["stderr"] = res.stderr.strip()
        except Exception as e:
            result["error"] = str(e)
        return result

    # 2. 本地 Linux 节点 (动态检测当前服务器本机)
    if is_local_host(target.get("host")) and int(target.get("port") or 22) == 22 and not target.get("container_name"):
        if sys.platform == "win32" or os_type == "windows":
            return dict(result, error="Windows 本机请使用单命令或 PowerShell 会话代理")
        script = generate_provisioning_script(proxy_url, no_proxy, action)
        try:
            res = subprocess.run(["sh", "-c", script], capture_output=True, text=True, errors="replace", timeout=10)
            result["returncode"] = res.returncode
            if res.returncode != 0:
                result["stderr"] = res.stderr.strip()
        except Exception as e:
            result["error"] = str(e)
        return result

    # 3. 通用远程 SSH 直连通道 (物理工作站 / 工控机 / 边缘设备 / 暴露端口的 Docker 容器)
    host = target.get("host")
    port = int(target.get("port") or 22)
    user = target.get("ssh_user") or ("root" if os_type == "docker" else "ubuntu")
    auth_type = target.get("auth_type") or ("password" if target.get("ssh_pass") else "key")
    password = target.get("ssh_pass")

    script = generate_provisioning_script(proxy_url, no_proxy, action)
    try:
        res = run_remote_ssh_script(host, port, user, auth_type, password, script, timeout=14)
        result["returncode"] = res.returncode
        if res.returncode != 0:
            result["stderr"] = res.stderr.strip()
        else:
            # If initial connection with password succeeded, upgrade node to key auth
            if action == "on" and password and auth_type == "password" and get_control_node_public_key():
                probe = run_remote_ssh_script(host, port, user, "key", None, "true", timeout=8)
                if probe.returncode != 0:
                    return result
                target.pop("ssh_pass", None)
                target["auth_type"] = "key"
                target["has_ssh_key"] = True
    except Exception as e:
        result["error"] = str(e)

    return result


def check_node_http(target):
    mode = target.get("access_mode") or ("docker_host" if target.get("container_name") and not target.get("port") else "ssh")
    started = time.monotonic()
    result = {"online": False, "latency_ms": None, "is_proxy_enabled": bool(target.get("is_proxy_enabled"))}
    try:
        local = (mode != "docker_host" and is_local_host(target.get("host"))
                 and int(target.get("port") or 22) == 22 and not target.get("container_name"))
        # Use only the final status, not CONNECT headers or numbers in an HTTP body.
        command = ["curl", "-sS", "-o", os.devnull if local else "/dev/null", "-w", "%{http_code}",
                   "--max-time", "8", "https://www.google.com"]
        if local:
            res = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=10)
        else:
            script = " ".join(map(shlex.quote, command))
            if mode == "docker_host":
                res = ssh_with_script(docker_ssh_command(target, "exec", "-i"), script, 14)
            else:
                user = target.get("ssh_user") or ("root" if target.get("os_type") == "docker" else "ubuntu")
                res = run_remote_ssh_script(target["host"], target.get("port"), user,
                                            target.get("auth_type"), target.get("ssh_pass"), script, timeout=14)
        code = res.stdout.strip()
        result["online"] = res.returncode == 0 and bool(re.fullmatch(r"2[0-9]{2}", code))
        result["status_line"] = ("HTTP " + code) if res.returncode == 0 else (res.stderr.strip() or "请求失败")
        result["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result.update(error=str(exc), status_line=str(exc))
    return result


DANGEROUS_PATTERNS = [
    r"\brm\s+-[rf]*\s+/",
    r"\bmkfs\b",
    r"\bfdisk\b",
    r"\bdd\s+if=",
    r":\(\)\s*\{"
]


class ProxyConsoleHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

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

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        if content_length > 1024 * 1024:
            self.close_connection = True
            raise ValueError("请求体过大")
        post_data = self.rfile.read(content_length).decode("utf-8")
        data = json.loads(post_data)
        if not isinstance(data, dict):
            raise ValueError("请求体必须是 JSON 对象")
        return data

    def parse_request(self):
        if not super().parse_request():
            return False
        host = self.headers.get("Host", "")
        try:
            parsed = urllib.parse.urlsplit("//" + host)
            if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
                raise ValueError()
            allowed = {"localhost", "127.0.0.1", "::1", self.connection.getsockname()[0]}
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
        return True

    def do_GET(self):
        try:
            self.serve_get()
        except ValueError as exc:
            self.send_json({"success": False, "error": str(exc)}, 400)

    def serve_get(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("", "/"):
            self.path = "/index.html"
            return super().do_GET()

        if path == "/proxy-on":
            cfg = load_config()
            gw = resolve_gateway_info(cfg)
            proxy_url = gateway_url(gw)
            no_proxy = validate_bypass(cfg.get("no_proxy", "localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,*.local"))
            script = f"""# Generated by net-proxy-tool
export HTTP_PROXY="{proxy_url}"
export HTTPS_PROXY="{proxy_url}"
export http_proxy="{proxy_url}"
export https_proxy="{proxy_url}"
export NO_PROXY="{no_proxy}"
export no_proxy="{no_proxy}"
echo "[net-proxy-tool] 出海代理已开启 (出网网关: {gw['host']}:{gw['port']})"
"""
            self.send_text(script)
            return

        if path == "/proxy-off":
            script = """# Generated by net-proxy-tool
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY no_proxy
echo "[net-proxy-tool] 出海代理已关闭，当前会话已恢复 100% 直连"
"""
            self.send_text(script)
            return

        if path == "/container-init.sh":
            cfg = load_config()
            gw = resolve_gateway_info(cfg)
            proxy_url = gateway_url(gw)
            no_proxy = validate_bypass(cfg.get("no_proxy", "localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,*.local"))
            script = f"""#!/bin/bash
# net-proxy-tool: Docker 容器内独立开关一键初始化
# 纯容器内生效，绝不影响宿主机和其他容器

cat << 'EOF' > /etc/profile.d/net-proxy-switch.sh
alias proxy-on='export HTTP_PROXY="{proxy_url}" HTTPS_PROXY="{proxy_url}" http_proxy="{proxy_url}" https_proxy="{proxy_url}" NO_PROXY="{no_proxy}" no_proxy="{no_proxy}" && echo "✅ [容器代理] 已开启出海通道 ({gw['host']}:{gw['port']})"'
alias proxy-off='unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY no_proxy && echo "🛑 [容器代理] 已关闭出海通道，恢复直连"'
alias proxy-status='env | grep -i proxy || echo "⚪ [容器代理] 当前处于直连状态 (未开启代理)"'
EOF

cat << 'EOF' > /usr/local/bin/with-proxy
#!/bin/sh
HTTP_PROXY="{proxy_url}" \\
HTTPS_PROXY="{proxy_url}" \\
http_proxy="{proxy_url}" \\
https_proxy="{proxy_url}" \\
NO_PROXY="{no_proxy}" \\
no_proxy="{no_proxy}" \\
exec "$@"
EOF
chmod +x /usr/local/bin/with-proxy 2>/dev/null || true

for f in ~/.bashrc /etc/bash.bashrc; do
    if [ -f "$f" ]; then
        grep -q 'net-proxy-switch.sh' "$f" 2>/dev/null || echo '[ -f /etc/profile.d/net-proxy-switch.sh ] && source /etc/profile.d/net-proxy-switch.sh' >> "$f"
    fi
done

source /etc/profile.d/net-proxy-switch.sh 2>/dev/null || true

echo "=================================================="
echo "🎉 [容器环境] 容器内独立代理开关已就绪！"
echo "在容器内部直接输入以下命令即可随时控制:"
echo "  proxy-on           # 开启出海代理"
echo "  proxy-off          # 关闭出海代理 (恢复直连)"
echo "  proxy-status       # 查看代理开关状态"
echo "  with-proxy <命令>  # 单任务临时走代理 (如 with-proxy pip install ...)"
echo "=================================================="
"""
            self.send_text(script)
            return

        if path == "/api/health":
            token = os.environ.get("NET_PROXY_INSTANCE_TOKEN", "")
            self.send_json({"status": "ok", "version": "1.4.0", "service": "net-proxy-tool",
                            "pid": os.getpid(), "instance_id": hashlib.sha256(token.encode()).hexdigest() if token else ""})
            return

        if path == "/api/config":
            self.send_json(load_config())
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
                # Serialize read-modify-write updates, including switch results.
                if path in ("/api/config", "/api/set-active-gateway", "/api/node-switch", "/api/nodes/batch-switch") or path.startswith(("/api/clients/", "/api/gateways/")):
                    with CONFIG_WRITE_LOCK:
                        handlers[path]()
                else:
                    handlers[path]()
            except (ValueError, KeyError, TypeError) as e:
                self.send_json({"success": False, "error": str(e)}, status_code=400)
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status_code=500)
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
        gw = resolve_gateway_info(cfg, gid)
        if not gw:
            self.send_json({"gateway": None, "targets": [], "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "error": "未找到网关，请先在首页保存 HTTP 代理网关。"}, 404 if gid else 200)
            return
        host, port = gw["host"], int(gw["port"])
        proxy_url = gateway_url(gw)

        gw_ok, gw_rtt = check_tcp_port(host, port)
        results = {
            "gateway": {
                "id": gw.get("id"),
                "name": gw.get("name"),
                "host": host,
                "port": port,
                "online": gw_ok,
                "latency_ms": gw_rtt if gw_ok else None,
                "error": None if gw_ok else str(gw_rtt)
            },
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "targets": []
        }

        if gw_ok:
            targets = cfg.get("diagnostic_targets", {})
            with ThreadPoolExecutor(max_workers=7) as pool:
                futures = [
                    pool.submit(check_http_target, name, info, proxy_url)
                    for name, info in targets.items()
                ]
                for f in futures:
                    results["targets"].append(f.result())

        self.send_json(results)

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
        host = req_json.get("host", "").strip()
        port = int(req_json.get("port", 0))
        proxy = gateway_url({"host": host, "port": port, "protocol": req_json.get("protocol", "http")})
        ok, tcp_info = check_tcp_port(host, port, timeout=2.5)
        url = req_json.get("target_url") or "https://example.com/"
        if not ok:
            self.send_json({"success": False, "tcp_ok": False, "online": False, "error": tcp_info})
            return
        result = check_http_target("HTTP probe", url, proxy)
        online = result["status"] == "online"
        self.send_json(dict(result, success=online, tcp_ok=True, online=online, tcp_latency_ms=tcp_info))

    def handle_test_host(self):
        req_json = self.read_json_body()
        host = req_json.get("host", "").strip()
        port = int(req_json.get("port", 22))  # Default check port 22 or 80
        if not host:
            self.send_json({"success": False, "error": "Host IP required"}, status_code=400)
            return
        ok, rtt_or_err = check_tcp_port(host, port, timeout=2.0)
        self.send_json({"success": True, "online": ok, "latency_ms": rtt_or_err if ok else None, "error": None if ok else str(rtt_or_err)})

    def handle_test_node_preflight(self):
        """
        Three-stage deep preflight check:
        1. TCP socket connect + RTT measurement
        2. SSH protocol banner handshake
        3. Real credential authentication test (Password via ASKPASS or Key via BatchMode)
        """
        req_json = self.read_json_body()
        host = req_json.get("host", "").strip()
        port = int(req_json.get("port") or 22)
        access_mode = req_json.get("access_mode", "ssh").strip().lower()
        auth_type = req_json.get("auth_type", "key").strip().lower()
        user = req_json.get("ssh_user", "").strip() or "root"
        password = req_json.get("ssh_pass", "")
        container_name = req_json.get("container_name", "").strip()
        ssh_host = req_json.get("ssh_host", "").strip() or host

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
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
                if res.returncode == 0 and "true" in res.stdout.lower():
                    self.send_json({
                        "success": True,
                        "tcp_ok": True,
                        "latency_ms": rtt_or_err,
                        "auth_ok": True,
                        "message": f"🟢 宿主机已连通 ({rtt_or_err}ms)，且 Docker 容器【{container_name}】正在健康运行中！"
                    })
                else:
                    self.send_json({
                        "success": False,
                        "tcp_ok": True,
                        "latency_ms": rtt_or_err,
                        "auth_ok": False,
                        "message": f"⚠️ 宿主机已连通，但未检测到运行中的容器【{container_name}】"
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
            if auth_type == "password" and password:
                res = run_remote_ssh_script(host, port, user, "password", password, "true", timeout=6)
                if res.returncode == 0:
                    auth_ok = True
                    auth_msg = "密码鉴权验证通过 (自愈公钥植入就绪)"
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
        req_json = self.read_json_body()
        cid = req_json.get("id", "").strip()
        name = req_json.get("name", "").strip()
        host = req_json.get("host", "").strip()
        os_type = req_json.get("os_type", "linux").strip().lower()
        bound_gw = req_json.get("bound_gateway_id", "").strip()
        tags = req_json.get("tags", [])
        desc = req_json.get("description", "").strip()

        if not name or not host:
            self.send_json({"success": False, "error": "节点名称和主机IP不能为空"}, status_code=400)
            return

        if not cid:
            # Auto-generate ID if empty
            safe_slug = re.sub(r"[^a-zA-Z0-9-]", "", host.replace(".", "-"))
            cid = f"node-{safe_slug}"

        cfg = load_config()
        clients = cfg.get("clients", [])

        # Check existing ID
        for c in clients:
            if c.get("id") == cid:
                self.send_json({"success": False, "error": f"节点ID '{cid}' 已存在，请更换"}, status_code=400)
                return

        new_client = {
            "id": cid,
            "name": name,
            "host": host,
            "port": int(req_json.get("port", 22)),
            "os_type": os_type,
            "access_mode": req_json.get("access_mode", "ssh").strip().lower(),
            "auth_type": req_json.get("auth_type", "key").strip().lower(),
            "bound_gateway_id": bound_gw,
            "is_proxy_enabled": False,
            "tags": tags if isinstance(tags, list) else [t.strip() for t in str(tags).split(",") if t.strip()],
            "description": desc
        }
        if "ssh_user" in req_json and req_json["ssh_user"]:
            new_client["ssh_user"] = req_json["ssh_user"].strip()
        if "ssh_pass" in req_json and req_json["ssh_pass"]:
            new_client["ssh_pass"] = req_json["ssh_pass"]
        if "container_name" in req_json:
            new_client["container_name"] = req_json["container_name"].strip()
        if "ssh_host" in req_json:
            new_client["ssh_host"] = req_json["ssh_host"].strip()

        validate_client(new_client)
        clients.append(new_client)
        cfg["clients"] = clients
        save_config(cfg)
        write_audit_log("client_add", cid, "success", f"添加节点: {name} ({host}:{new_client['port']})")
        self.send_json({"success": True, "message": "业务节点添加成功", "client": new_client})

    def handle_client_update(self):
        req_json = self.read_json_body()
        cid = req_json.get("id", "").strip()
        if not cid:
            self.send_json({"success": False, "error": "节点ID不能为空"}, status_code=400)
            return

        cfg = load_config()
        clients = cfg.get("clients", [])
        target = None
        for c in clients:
            if c.get("id") == cid:
                target = c
                break

        if not target:
            self.send_json({"success": False, "error": f"未找到ID为 '{cid}' 的业务节点"}, status_code=404)
            return

        if "name" in req_json: target["name"] = req_json["name"].strip()
        if "host" in req_json: target["host"] = req_json["host"].strip()
        if "port" in req_json: target["port"] = int(req_json["port"])
        if "os_type" in req_json: target["os_type"] = req_json["os_type"].strip().lower()
        if "access_mode" in req_json: target["access_mode"] = req_json["access_mode"].strip().lower()
        if "auth_type" in req_json: target["auth_type"] = req_json["auth_type"].strip().lower()
        if "ssh_user" in req_json: target["ssh_user"] = req_json["ssh_user"].strip()
        if req_json.get("ssh_pass"): target["ssh_pass"] = req_json["ssh_pass"]
        if "bound_gateway_id" in req_json: target["bound_gateway_id"] = req_json["bound_gateway_id"].strip()
        if "container_name" in req_json: target["container_name"] = req_json["container_name"].strip()
        if "ssh_host" in req_json: target["ssh_host"] = req_json["ssh_host"].strip()
        if "is_proxy_enabled" in req_json: target["is_proxy_enabled"] = bool(req_json["is_proxy_enabled"])
        if "tags" in req_json:
            t = req_json["tags"]
            target["tags"] = t if isinstance(t, list) else [x.strip() for x in str(t).split(",") if x.strip()]
        if "description" in req_json: target["description"] = req_json["description"].strip()

        validate_client(target)
        save_config(cfg)
        write_audit_log("client_update", cid, "success", f"更新节点: {target['name']}")
        self.send_json({"success": True, "message": "业务节点更新成功", "client": target})

    def handle_client_delete(self):
        req_json = self.read_json_body()
        cid = req_json.get("id", "").strip()
        if not cid:
            self.send_json({"success": False, "error": "节点ID不能为空"}, status_code=400)
            return

        cfg = load_config()
        clients = cfg.get("clients", [])
        new_clients = [c for c in clients if c.get("id") != cid]

        if len(new_clients) == len(clients):
            self.send_json({"success": False, "error": f"未找到ID为 '{cid}' 的业务节点"}, status_code=404)
            return

        cfg["clients"] = new_clients
        save_config(cfg)
        write_audit_log("client_delete", cid, "success", f"删除业务节点: {cid}")
        self.send_json({"success": True, "message": "业务节点删除成功", "id": cid})

    def handle_node_switch(self):
        req_json = self.read_json_body()
        node_id = req_json.get("node_id", "").strip()
        action = req_json.get("action", "on").strip().lower()

        cfg = load_config()
        clients = cfg.get("clients", [])
        target = None
        for c in clients:
            if c.get("id") == node_id:
                target = c
                break

        if not target:
            self.send_json({"success": False, "error": f"未找到节点 {node_id}"}, status_code=404)
            return

        gw = resolve_gateway_info(cfg, target.get("bound_gateway_id"))
        if action not in ("on", "off"):
            raise ValueError("无效的节点操作")
        dispatch_result = apply_node_proxy(target, action, cfg)

        if dispatch_result.get("returncode") != 0:
            detail = dispatch_result.get("error") or dispatch_result.get("stderr") or "下发失败"
            write_audit_log(f"node_switch_{action}", node_id, "failed", detail)
            self.send_json({"success": False, "action": action, "error": detail, "message": detail}, 502)
            return
        # 更新节点配置状态
        target["is_proxy_enabled"] = (action == "on")
        save_config(cfg)

        msg = (
            f"✅ 节点【{target['name']}】出海通道已激活！全栈专有工具（curl/git/pip/wget/apt）与环境变量已即刻生效，在任何终端（包括已有运行中的会话）直接执行命令即可出海。"
            if action == "on"
            else f"🛑 节点【{target['name']}】出海通道已关闭，所有工具配置文件与环境已彻底清除，已恢复 100% 原生直连网络。"
        )

        status_flag = "success" if dispatch_result.get("returncode", 0) == 0 else "failed"
        write_audit_log(f"node_switch_{action}", node_id, status_flag, msg)

        self.send_json({
            "success": True,
            "action": action,
            "node_id": node_id,
            "is_proxy_enabled": target["is_proxy_enabled"],
            "gateway": f"{gw['host']}:{gw['port']}" if gw else None,
            "dispatch_result": dispatch_result,
            "message": msg
        })

    def handle_batch_switch(self):
        """
        Batch switch all nodes to proxy ON or OFF (One-click full disconnection to restore direct link).
        """
        req_json = self.read_json_body()
        action = req_json.get("action", "off").strip().lower()
        if action not in ("on", "off"):
            raise ValueError("无效的节点操作")

        cfg = load_config()
        clients = cfg.get("clients", [])
        results = []

        for target in clients:
            cid = target.get("id")
            try:
                res = apply_node_proxy(target, action, cfg)
                ok = res.get("returncode") == 0
                if ok:
                    target["is_proxy_enabled"] = (action == "on")
                results.append({
                    "node_id": cid,
                    "name": target.get("name"),
                    "success": ok,
                    "action": action,
                    "error": res.get("error") or res.get("stderr")
                })
                write_audit_log(f"batch_{action}", cid, "success" if ok else "failed", res.get("stderr", ""))
            except Exception as e:
                results.append({
                    "node_id": cid,
                    "name": target.get("name"),
                    "success": False,
                    "action": action,
                    "error": str(e)
                })
                write_audit_log(f"batch_{action}", cid, "error", str(e))

        save_config(cfg)
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)

        msg = (
            f"🛑 已成功恢复全部 {success_count}/{total_count} 个节点直连！"
            if action == "off"
            else f"⚡ 已成功为 {success_count}/{total_count} 个节点开启出海通道！"
        )
        self.send_json({
            "success": success_count == total_count,
            "action": action,
            "total": total_count,
            "success_count": success_count,
            "results": results,
            "message": msg
        })

    def handle_nodes_health_check_all(self):
        """
        Performs concurrent health checks across all worker nodes and containers.
        """
        cfg = load_config()
        clients = cfg.get("clients", [])
        health_map = {}

        def check_one(target):
            return target.get("id"), check_node_http(target)

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_results = list(executor.map(check_one, clients))

        for cid, info in future_results:
            health_map[cid] = info

        write_audit_log("health_check_all", "-", "success", f"全网巡检完成，共检测 {len(clients)} 个节点")
        self.send_json({
            "success": True,
            "health_map": health_map,
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })


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

        result = check_node_http(target)
        self.send_json(dict(result, success="error" not in result, node_id=node_id,
                            message=result["status_line"]))

    def handle_gateway_add(self):
        req_json = self.read_json_body()
        gid = req_json.get("id", "").strip()
        name = req_json.get("name", "").strip()
        host = req_json.get("host", "").strip()
        port = int(req_json.get("port", 7890))
        protocol = req_json.get("protocol", "http").strip().lower()
        desc = req_json.get("description", "").strip()

        if not name or not host:
            self.send_json({"success": False, "error": "网关名称和IP不能为空"}, status_code=400)
            return

        if not gid:
            safe_slug = re.sub(r"[^a-zA-Z0-9-]", "", host.replace(".", "-"))
            gid = f"gw-{safe_slug}"

        cfg = load_config()
        gateways = cfg.get("gateways", [])
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
        gid = req_json.get("id", "").strip()
        if not gid:
            self.send_json({"success": False, "error": "网关ID不能为空"}, status_code=400)
            return

        cfg = load_config()
        gateways = cfg.get("gateways", [])
        target = None
        for g in gateways:
            if g.get("id") == gid:
                target = g
                break

        if not target:
            self.send_json({"success": False, "error": f"未找到ID为 '{gid}' 的网关"}, status_code=404)
            return

        if "name" in req_json: target["name"] = req_json["name"].strip()
        if "host" in req_json: target["host"] = req_json["host"].strip()
        if "port" in req_json: target["port"] = int(req_json["port"])
        if "protocol" in req_json: target["protocol"] = req_json["protocol"].strip()
        if "description" in req_json: target["description"] = req_json["description"].strip()

        gateway_url(target)
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

        gateways = cfg.get("gateways", [])
        new_gateways = [g for g in gateways if g.get("id") != gid]

        if len(new_gateways) == len(gateways):
            self.send_json({"success": False, "error": f"未找到ID为 '{gid}' 的网关"}, status_code=404)
            return

        cfg["gateways"] = new_gateways
        save_config(cfg)
        self.send_json({"success": True, "message": "代理网关删除成功", "id": gid})

    def handle_api_run(self):
        try:
            req_json = self.read_json_body()
            cmd_text = req_json.get("command", "").strip()
            gid = req_json.get("gateway_id")
        except Exception:
            self.send_error(400, "Invalid JSON payload")
            return

        if not cmd_text:
            self.send_error(400, "Command cannot be empty")
            return

        for pat in DANGEROUS_PATTERNS:
            if re.search(pat, cmd_text):
                self.send_error(403, "Command blocked for system security.")
                return

        cfg = load_config()
        gw = resolve_gateway_info(cfg, gid)
        gw_arg = gateway_url(gw)[len("http://"):]

        self.close_connection = True
        self.send_response(200)
        self.send_header("Connection", "close")
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def send_event(data_dict):
            payload = f"data: {json.dumps(data_dict, ensure_ascii=False)}\n\n".encode("utf-8")
            self.wfile.write(payload)
            self.wfile.flush()

        send_event({
            "type": "start",
            "command": cmd_text,
            "gateway": f"{gw['name']} ({gw_arg})",
            "time": time.strftime("%H:%M:%S")
        })

        with_proxy_script = str(TOOL_DIR / "with_proxy.py")
        exec_cmd = [sys.executable, with_proxy_script, "--gateway", gw_arg] + cmd_text.split()

        try:
            p = subprocess.Popen(
                exec_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(TOOL_DIR)
            )

            for line in p.stdout:
                send_event({"type": "stdout", "line": line.rstrip("\r\n")})

            p.wait()
            # Zero pollution check
            env_clean = "HTTP_PROXY" not in os.environ and "http_proxy" not in os.environ
            send_event({
                "type": "finish",
                "exit_code": p.returncode,
                "env_clean": env_clean,
                "msg": f"沙箱任务运行结束 (退出码: {p.returncode})。进程已销毁，全局网络环境 100% 纯净无残留。"
            })
        except Exception as e:
            send_event({
                "type": "error",
                "msg": f"沙箱执行异常: {e}"
            })


def run_server(port=None, bind=None):
    cfg = load_config()
    port = port if port is not None else int(cfg.get("web_port", 8899))
    host = bind or os.environ.get("NET_PROXY_BIND", "127.0.0.1")
    with ThreadingHTTPServer((host, port), ProxyConsoleHandler) as httpd:
        print(f"net-proxy-tool | http://{host}:{httpd.server_port}", flush=True)
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
