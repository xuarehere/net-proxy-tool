#!/usr/bin/env python3
"""
net-proxy-tool: Lightweight Standalone Web Console (v3.0)
Multi-Gateway, Multi-Node Topology, Dynamic CRUD & Progressive Guided Sandbox Execution.
Zero third-party dependencies (pure Python 3 standard library).
"""
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
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
CONFIG_FILE = TOOL_DIR / "config.json"
AUDIT_LOG_FILE = TOOL_DIR / "data" / "audit.log"


def write_audit_log(action, node_id="-", status="info", details="", operator_ip="127.0.0.1"):
    """
    Appends an event record to the lightweight audit log in JSON Lines format.
    """
    try:
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "node_id": node_id or "-",
            "operator_ip": operator_ip or "127.0.0.1",
            "status": status,
            "details": str(details or "")
        }
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Audit Log Warning] {e}")


def get_audit_logs(limit=60):
    """
    Retrieves the most recent audit log entries in reverse chronological order.
    """
    if not AUDIT_LOG_FILE.exists():
        return []
    records = []
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
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
                "description": "局域网科学出海网关",
                "is_default": True
            }
        ],
        "clients": [
            {
                "id": "node-linux-server",
                "name": "Linux 计算工作站 / GPU 服务器",
                "host": "192.168.1.101",
                "os_type": "linux",
                "bound_gateway_id": "gw-default",
                "tags": ["Linux", "x86_64", "计算节点"],
                "description": "深度学习计算节点或研发工作站"
            }
        ],
        "web_port": 8899,
        "no_proxy": "localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,*.local",
        "diagnostic_targets": {
            "Google": {"url": "https://www.google.com", "desc": "基础连通", "category": "基础服务"},
            "GitHub": {"url": "https://github.com", "desc": "源码拉取", "category": "研发必备"},
            "Raw GitHub": {"url": "https://raw.githubusercontent.com", "desc": "脚本拉取", "category": "研发必备"},
            "HuggingFace": {"url": "https://huggingface.co", "desc": "AI模型下载", "category": "AI/大模型"},
            "PyPI": {"url": "https://pypi.org", "desc": "pip 包管理", "category": "包管理"},
            "OpenAI API": {"url": "https://api.openai.com", "desc": "LLM 接口", "category": "AI/大模型"},
            "YouTube": {"url": "https://www.youtube.com", "desc": "多媒体传输", "category": "多媒体"}
        }
    }
    # 首次自愈机制: 若 config.json 不存在，自动从 config.example.json 拷贝生成
    if not CONFIG_FILE.exists():
        example_cfg = TOOL_DIR / "config.example.json"
        if example_cfg.exists():
            try:
                shutil.copy2(example_cfg, CONFIG_FILE)
            except Exception:
                pass

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception:
            pass
    return default_cfg


def save_config(cfg_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg_data, f, indent=2, ensure_ascii=False)


def resolve_gateway_info(cfg, gateway_id=None):
    gid = gateway_id or cfg.get("active_gateway_id")
    for gw in cfg.get("gateways", []):
        if gw.get("id") == gid:
            return gw
    for gw in cfg.get("gateways", []):
        if gw.get("is_default"):
            return gw
    if cfg.get("gateways"):
        return cfg["gateways"][0]
    return {
        "id": "default",
        "name": "默认网关",
        "host": "127.0.0.1",
        "port": 7890,
        "protocol": "http"
    }


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

    t0 = time.time()
    try:
        proxy_handler = urllib.request.ProxyHandler({
            "http": proxy_url,
            "https": proxy_url
        })
        opener = urllib.request.build_opener(proxy_handler)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (net-proxy-tool-diagnostic/3.0)"}
        )
        with opener.open(req, timeout=timeout) as resp:
            code = resp.getcode()
            rtt_ms = round((time.time() - t0) * 1000, 1)
            return {
                "name": name,
                "url": url,
                "desc": desc,
                "category": category,
                "status": "online",
                "code": code,
                "latency_ms": rtt_ms
            }
    except urllib.error.HTTPError as e:
        rtt_ms = round((time.time() - t0) * 1000, 1)
        return {
            "name": name,
            "url": url,
            "desc": desc,
            "category": category,
            "status": "online",
            "code": e.code,
            "latency_ms": rtt_ms
        }
    except Exception as e:
        rtt_ms = round((time.time() - t0) * 1000, 1)
        return {
            "name": name,
            "url": url,
            "desc": desc,
            "category": category,
            "status": "offline",
            "error": str(e),
            "latency_ms": rtt_ms
        }


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

    if password and auth_type == "password":
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sh") as tf:
            tf.write(f"#!/bin/sh\necho '{password}'\n")
            askpass_path = tf.name
        os.chmod(askpass_path, stat.S_IRWXU)

        env = os.environ.copy()
        env["SSH_ASKPASS"] = askpass_path
        env["SSH_ASKPASS_REQUIRE"] = "force"
        env["DISPLAY"] = "dummy"

        try:
            pubkey = get_control_node_public_key()
            if pubkey:
                enroll_cmd = (
                    f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
                    f"grep -qF '{pubkey}' ~/.ssh/authorized_keys 2>/dev/null || "
                    f"echo '{pubkey}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
                )
                full_script = f"{enroll_cmd}\n{script}"
            else:
                full_script = script

            ssh_bin = ["setsid", "ssh"] if sys.platform != "win32" and shutil.which("setsid") else ["ssh"]
            cmd = ssh_bin + [
                "-p", str(port),
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=5",
                f"{user}@{host}",
                "sh"
            ]
            res = subprocess.run(
                cmd,
                input=full_script,
                capture_output=True,
                text=True,
                errors="replace",
                env=env,
                timeout=timeout
            )
            return res
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
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5",
            f"{user}@{host}",
            "sh"
        ]
        res = subprocess.run(
            cmd,
            input=script,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout
        )
        return res


def generate_provisioning_script(proxy_url, no_proxy, action="on"):
    """
    Generates unified provisioning script for both non-root workstations and root containers.
    """
    if action == "on":
        return f"""
# Layer 1: Dedicated Tool Configurations (Immediate across all sessions including active tmux)
mkdir -p ~/.config/pip
cat << 'EOF' > ~/.curlrc
proxy = "{proxy_url}"
noproxy = "{no_proxy}"
EOF

git config --global http.proxy "{proxy_url}" 2>/dev/null || true
git config --global https.proxy "{proxy_url}" 2>/dev/null || true

cat << 'EOF' > ~/.config/pip/pip.conf
[global]
proxy = {proxy_url}
EOF

cat << 'EOF' > ~/.wgetrc
http_proxy = {proxy_url}
https_proxy = {proxy_url}
EOF

# Try system-wide configs if root or passwordless sudo available (ignore errors if standard user)
if [ "$(id -u)" = "0" ]; then
    cp ~/.curlrc /etc/curlrc 2>/dev/null || true
    mkdir -p /etc/pip /etc/apt/apt.conf.d 2>/dev/null || true
    cp ~/.config/pip/pip.conf /etc/pip.conf 2>/dev/null || true
    git config --system http.proxy "{proxy_url}" 2>/dev/null || true
    cat << 'EOF' > /etc/apt/apt.conf.d/99net-proxy
Acquire::http::Proxy "{proxy_url}";
Acquire::https::Proxy "{proxy_url}";
EOF
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo -n cp ~/.curlrc /etc/curlrc 2>/dev/null || true
    sudo -n mkdir -p /etc/pip /etc/apt/apt.conf.d 2>/dev/null || true
    sudo -n cp ~/.config/pip/pip.conf /etc/pip.conf 2>/dev/null || true
    sudo -n git config --system http.proxy "{proxy_url}" 2>/dev/null || true
fi

# Layer 2: Prepend Environment Variables at Line 1 of bashrc (Bypass [ -z "$PS1" ] && return)
PREPEND_CODE='
# --- NET-PROXY-TOOL-START ---
export HTTP_PROXY="{proxy_url}"
export HTTPS_PROXY="{proxy_url}"
export http_proxy="{proxy_url}"
export https_proxy="{proxy_url}"
export NO_PROXY="{no_proxy}"
export no_proxy="{no_proxy}"
# --- NET-PROXY-TOOL-END ---
'

for f in ~/.bashrc ~/.bash_profile ~/.profile /etc/bash.bashrc /etc/profile; do
  if [ -f "$f" ] && [ -w "$f" ]; then
    sed -i '/# --- NET-PROXY-TOOL-START ---/,/# --- NET-PROXY-TOOL-END ---/d' "$f" 2>/dev/null || true
    printf "%s\\n%s" "$PREPEND_CODE" "$(cat "$f")" > "$f" 2>/dev/null || true
  fi
done

cat << 'EOF' > ~/.net-proxy-switch.sh
export HTTP_PROXY="{proxy_url}"
export HTTPS_PROXY="{proxy_url}"
export http_proxy="{proxy_url}"
export https_proxy="{proxy_url}"
export NO_PROXY="{no_proxy}"
export no_proxy="{no_proxy}"
EOF
"""
    else:
        return """
# Clean up user tool configurations
rm -f ~/.curlrc ~/.config/pip/pip.conf ~/.wgetrc ~/.net-proxy-switch.sh
git config --global --unset http.proxy 2>/dev/null || true
git config --global --unset https.proxy 2>/dev/null || true

# Clean up system-wide configs if permitted
if [ "$(id -u)" = "0" ]; then
    rm -f /etc/curlrc /etc/pip.conf /etc/apt/apt.conf.d/99net-proxy
    git config --system --unset http.proxy 2>/dev/null || true
    git config --system --unset https.proxy 2>/dev/null || true
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo -n rm -f /etc/curlrc /etc/pip.conf /etc/apt/apt.conf.d/99net-proxy 2>/dev/null || true
    sudo -n git config --system --unset http.proxy 2>/dev/null || true
fi

# Clean up environment prepend blocks
for f in ~/.bashrc ~/.bash_profile ~/.profile /etc/bash.bashrc /etc/profile; do
  if [ -f "$f" ] && [ -w "$f" ]; then
    sed -i '/# --- NET-PROXY-TOOL-START ---/,/# --- NET-PROXY-TOOL-END ---/d' "$f" 2>/dev/null || true
  fi
done
"""


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
    proxy_url = f"http://{gw['host']}:{gw['port']}"
    no_proxy = cfg.get("no_proxy", "localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,*.local")

    result = {"action": action, "node_id": target.get("id"), "os_type": os_type, "access_mode": access_mode}

    # 1. 宿主机 Docker 穿透通道 (Legacy / Specific for containers without SSH)
    if access_mode == "docker_host":
        cname = target.get("container_name") or target.get("name") or "app-container"
        ssh_host = target.get("ssh_host") or target.get("host") or "127.0.0.1"
        ssh_user = target.get("ssh_user") or "ubuntu"
        script = generate_provisioning_script(proxy_url, no_proxy, action)
        try:
            res = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
                 f"{ssh_user}@{ssh_host}", "docker", "exec", "-i", "-u", "0", cname, "sh"],
                input=script,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=12
            )
            result["returncode"] = res.returncode
            if res.returncode != 0:
                result["stderr"] = res.stderr.strip()
        except Exception as e:
            result["error"] = str(e)
        return result

    # 2. 本地 Linux 节点 (动态检测当前服务器本机)
    if is_local_host(target.get("host")) and int(target.get("port") or 22) == 22 and not target.get("container_name"):
        script = generate_provisioning_script(proxy_url, no_proxy, action)
        try:
            res = subprocess.run(["bash", "-c", script], capture_output=True, text=True, errors="replace", timeout=10)
            result["local_returncode"] = res.returncode
            if res.returncode != 0:
                result["local_stderr"] = res.stderr.strip()
        except Exception as e:
            result["local_error"] = str(e)
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
            if password and auth_type == "password":
                target["auth_type"] = "key"
                target["has_ssh_key"] = True
                save_config(cfg)
    except Exception as e:
        result["error"] = str(e)

    return result


def ensure_node_provisioning_state(cfg):
    """
    Reconciles physical node files on disk/docker with config.json states.
    Ensures self-healing when web server starts or reloads.
    """
    for client in cfg.get("clients", []):
        is_enabled = bool(client.get("is_proxy_enabled"))
        action = "on" if is_enabled else "off"
        try:
            apply_node_proxy(client, action, cfg)
        except Exception as e:
            print(f"[Warning] Failed to reconcile proxy state for {client.get('id')}: {e}")


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
        super().end_headers()

    def send_json(self, data, status_code=200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def send_text(self, text, content_type="text/plain; charset=utf-8", status_code=200):
        payload = text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        post_data = self.rfile.read(content_length).decode("utf-8")
        return json.loads(post_data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("", "/"):
            self.path = "/index.html"
            return super().do_GET()

        if path == "/proxy-on":
            cfg = load_config()
            gw = resolve_gateway_info(cfg)
            proxy_url = f"http://{gw['host']}:{gw['port']}"
            no_proxy = cfg.get("no_proxy", "localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,*.local")
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
            proxy_url = f"http://{gw['host']}:{gw['port']}"
            no_proxy = cfg.get("no_proxy", "localhost,127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,*.local")
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
                handlers[path]()
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, status_code=500)
            return

        self.send_error(404, "Not Found")

    def handle_api_status(self, query_string):
        query = urllib.parse.parse_qs(query_string)
        gid = query.get("gateway_id", [None])[0]

        cfg = load_config()
        gw = resolve_gateway_info(cfg, gid)
        host, port = gw["host"], int(gw["port"])
        proxy_url = f"http://{host}:{port}"

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
        cfg.update(req_json)
        save_config(cfg)
        self.send_json({"success": True, "message": "配置保存成功", "config": cfg})

    def handle_set_active_gateway(self):
        req_json = self.read_json_body()
        gid = req_json.get("gateway_id")
        cfg = load_config()
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
        if not host or not port:
            self.send_json({"success": False, "error": "Host and port required"}, status_code=400)
            return
        ok, rtt_or_err = check_tcp_port(host, port, timeout=2.5)
        if ok:
            self.send_json({"success": True, "online": True, "latency_ms": rtt_or_err})
        else:
            self.send_json({"success": True, "online": False, "error": str(rtt_or_err)})

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
        password = req_json.get("ssh_pass", "").strip()
        container_name = req_json.get("container_name", "").strip()
        ssh_host = req_json.get("ssh_host", "").strip() or host

        if access_mode == "docker_host":
            ok, rtt_or_err = check_tcp_port(ssh_host, 22, timeout=2.5)
            if not ok:
                self.send_json({
                    "success": False,
                    "tcp_ok": False,
                    "message": f"❌ 宿主机网络不可达 ({ssh_host}:22): {rtt_or_err}"
                })
                return
            try:
                cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=4", f"{user}@{ssh_host}", f"docker inspect -f '{{{{.State.Running}}}}' {container_name}"]
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3.0)
        try:
            sock.connect((host, port))
            tcp_ok = True
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
        bound_gw = req_json.get("bound_gateway_id", "gw-183").strip()
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
            new_client["ssh_pass"] = req_json["ssh_pass"].strip()
        if "container_name" in req_json:
            new_client["container_name"] = req_json["container_name"].strip()
        if "ssh_host" in req_json:
            new_client["ssh_host"] = req_json["ssh_host"].strip()

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
        if "ssh_pass" in req_json: target["ssh_pass"] = req_json["ssh_pass"].strip()
        if "bound_gateway_id" in req_json: target["bound_gateway_id"] = req_json["bound_gateway_id"].strip()
        if "container_name" in req_json: target["container_name"] = req_json["container_name"].strip()
        if "ssh_host" in req_json: target["ssh_host"] = req_json["ssh_host"].strip()
        if "is_proxy_enabled" in req_json: target["is_proxy_enabled"] = bool(req_json["is_proxy_enabled"])
        if "tags" in req_json:
            t = req_json["tags"]
            target["tags"] = t if isinstance(t, list) else [x.strip() for x in str(t).split(",") if x.strip()]
        if "description" in req_json: target["description"] = req_json["description"].strip()

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
        dispatch_result = apply_node_proxy(target, action, cfg)

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
            "gateway": f"{gw['host']}:{gw['port']}",
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
            action = "off"

        cfg = load_config()
        clients = cfg.get("clients", [])
        results = []

        for target in clients:
            cid = target.get("id")
            try:
                res = apply_node_proxy(target, action, cfg)
                target["is_proxy_enabled"] = (action == "on")
                ok = (res.get("returncode", 0) == 0)
                results.append({
                    "node_id": cid,
                    "name": target.get("name"),
                    "success": ok,
                    "action": action,
                    "error": res.get("stderr")
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
            "success": True,
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
            cid = target.get("id")
            t0 = time.time()
            test_cmd = "curl -I --connect-timeout 6 https://www.google.com | head -n 2"
            os_type = (target.get("os_type") or "linux").lower()
            access_mode = (target.get("access_mode") or ("docker_host" if target.get("container_name") and not target.get("port") else "ssh")).lower()

            try:
                if access_mode == "docker_host":
                    cname = target.get("container_name") or target.get("name") or "app-container"
                    ssh_host = target.get("ssh_host") or target.get("host") or "127.0.0.1"
                    ssh_user = target.get("ssh_user") or "ubuntu"
                    res = subprocess.run(
                        ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=4", f"{ssh_user}@{ssh_host}", "docker", "exec", "-i", cname, "sh"],
                        input=test_cmd, capture_output=True, text=True, errors="replace", timeout=10
                    )
                elif is_local_host(target.get("host")) and int(target.get("port") or 22) == 22 and not target.get("container_name"):
                    res = subprocess.run(["curl", "-I", "--connect-timeout", "6", "https://www.google.com"], capture_output=True, text=True, errors="replace", timeout=10)
                else:
                    host = target.get("host")
                    port = int(target.get("port") or 22)
                    user = target.get("ssh_user") or ("root" if os_type == "docker" else "ubuntu")
                    auth_type = target.get("auth_type") or ("password" if target.get("ssh_pass") else "key")
                    password = target.get("ssh_pass")
                    res = run_remote_ssh_script(host, port, user, auth_type, password, test_cmd, timeout=10)

                rtt = round((time.time() - t0) * 1000, 1)
                is_online = (res.returncode == 0 and any(code in res.stdout for code in ("200", "301", "302")))
                status_line = res.stdout.strip().split("\n")[0] if res.stdout.strip() else ("HTTP 200 OK" if is_online else "直连超时或未通外网")
                return cid, {
                    "online": is_online,
                    "latency_ms": rtt if is_online else None,
                    "status_line": status_line,
                    "is_proxy_enabled": target.get("is_proxy_enabled", False)
                }
            except Exception as e:
                return cid, {
                    "online": False,
                    "latency_ms": None,
                    "status_line": str(e),
                    "is_proxy_enabled": target.get("is_proxy_enabled", False)
                }

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

        os_type = (target.get("os_type") or "linux").lower()
        access_mode = (target.get("access_mode") or ("docker_host" if target.get("container_name") and not target.get("port") else "ssh")).lower()
        t0 = time.time()
        test_cmd = "curl -I --connect-timeout 8 https://www.google.com | head -n 2"

        # 1. 宿主机 Docker 穿透模式 (Legacy)
        if access_mode == "docker_host":
            cname = target.get("container_name") or target.get("name") or "app-container"
            ssh_host = target.get("ssh_host") or target.get("host") or "127.0.0.1"
            ssh_user = target.get("ssh_user") or "ubuntu"
            try:
                res = subprocess.run(
                    ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
                     f"{ssh_user}@{ssh_host}", "docker", "exec", "-i", cname, "sh"],
                    input=test_cmd,
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=14
                )
                rtt_ms = round((time.time() - t0) * 1000, 1)
                is_online = (res.returncode == 0 and any(code in res.stdout for code in ("200", "301", "302")))
                status_line = res.stdout.strip().split("\n")[0] if res.stdout.strip() else ("HTTP 200 OK" if is_online else "直连超时或未通外网")
                self.send_json({
                    "success": True,
                    "node_id": node_id,
                    "online": is_online,
                    "latency_ms": rtt_ms if is_online else None,
                    "status_line": status_line,
                    "is_proxy_enabled": target.get("is_proxy_enabled", False),
                    "message": "容器出海访问正常" if is_online else "容器处于直连状态或外网未连通"
                })
            except Exception as e:
                self.send_json({"success": False, "node_id": node_id, "online": False, "error": str(e), "message": f"远程容器检测异常: {e}"})
            return

        # 2. 本地 Linux 节点 (动态检测当前服务器本机)
        if is_local_host(target.get("host")) and int(target.get("port") or 22) == 22 and not target.get("container_name"):
            try:
                res = subprocess.run(["curl", "-I", "--connect-timeout", "8", "https://www.google.com"], capture_output=True, text=True, errors="replace", timeout=14)
                rtt_ms = round((time.time() - t0) * 1000, 1)
                is_online = (res.returncode == 0 and any(code in res.stdout for code in ("200", "301", "302")))
                status_line = res.stdout.strip().split("\n")[0] if res.stdout.strip() else ("HTTP 200 OK" if is_online else "直连超时或未通外网")
                self.send_json({
                    "success": True,
                    "node_id": node_id,
                    "online": is_online,
                    "latency_ms": rtt_ms if is_online else None,
                    "status_line": status_line,
                    "is_proxy_enabled": target.get("is_proxy_enabled", False),
                    "message": "本地计算节点出海访问正常" if is_online else "本地计算节点未通外网 (处于直连模式)"
                })
            except Exception as e:
                self.send_json({"success": False, "node_id": node_id, "online": False, "error": str(e), "message": f"节点连通性检测异常: {e}"})
            return

        # 3. 通用远程 SSH 直连通道 (物理工作站 / 工控机 / 边缘设备 / 暴露端口容器)
        host = target.get("host")
        port = int(target.get("port") or 22)
        user = target.get("ssh_user") or ("root" if os_type == "docker" else "ubuntu")
        auth_type = target.get("auth_type") or ("password" if target.get("ssh_pass") else "key")
        password = target.get("ssh_pass")
        try:
            res = run_remote_ssh_script(host, port, user, auth_type, password, test_cmd, timeout=14)
            rtt_ms = round((time.time() - t0) * 1000, 1)
            is_online = (res.returncode == 0 and any(code in res.stdout for code in ("200", "301", "302")))
            status_line = res.stdout.strip().split("\n")[0] if res.stdout.strip() else ("HTTP 200 OK" if is_online else "直连超时或未通外网")
            self.send_json({
                "success": True,
                "node_id": node_id,
                "online": is_online,
                "latency_ms": rtt_ms if is_online else None,
                "status_line": status_line,
                "is_proxy_enabled": target.get("is_proxy_enabled", False),
                "message": f"节点【{target['name']}】出海访问正常" if is_online else f"节点【{target['name']}】处于直连状态或外网未连通"
            })
        except Exception as e:
            self.send_json({"success": False, "node_id": node_id, "online": False, "error": str(e), "message": f"远程节点检测异常: {e}"})
        return

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
        gw_arg = f"{gw['host']}:{gw['port']}"

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
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


def run_server(port: int = None):
    cfg = load_config()
    server_port = port if port else int(cfg.get("web_port", 8899))
    server_address = ("0.0.0.0", server_port)

    # 启动时自动同步各物理节点/容器的底层专有配置状态 (自愈保障)
    try:
        ensure_node_provisioning_state(cfg)
    except Exception as e:
        print(f"[Warning] 节点状态自愈初始化警告: {e}")

    httpd = ThreadingHTTPServer(server_address, ProxyConsoleHandler)
    print("==================================================")
    print(" net-proxy-tool 通用跨平台 Web 控制台 (v1.3.0)")
    print(f" 监听端口: {server_port}")
    print(f" 浏览器访问: http://localhost:{server_port}")
    print(" 纯 Python 3 标准库 · 进程级沙箱 · Docker 隔离 · 零依赖")
    print("==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止 Web 控制台...")
        httpd.server_close()


def main():
    p = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    run_server(p)


if __name__ == "__main__":
    main()
