"""Run the whole flow of net-proxy-tool in one process and narrate it.

The demo needs no existing proxy: it starts the local observation gateway,
saves it as a gateway, sends one request through it and shows the connections
the gateway saw. It uses a temporary configuration and never changes the
configuration of the operator.

    python -X utf8 tools/demo.py
    python -X utf8 tools/demo.py --lang zh-CN
    python -X utf8 tools/demo.py --target https://www.example.org/
"""
import argparse
import json
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sdk.config import load_config, save_config  # noqa: E402
from web import server as console  # noqa: E402
from web.local_gateway import LocalGateway  # noqa: E402

DEFAULT_TARGET = "https://example.com/"

MESSAGES = {
    "en": {
        "step1": "Prepare an isolated temporary configuration; your live settings are never modified.",
        "config_file": "Config file: ",
        "step2": "Select a probe target.",
        "target_live": "Target: {target} (real network)",
        "target_local": "Target unreachable; using local fixture site: {target}",
        "target_local_note": "Allowing the random fixture port temporarily; all other destination ports stay blocked.",
        "step3": "Start the local observation gateway (loopback-only, ports 80 and 443 allowed by default).",
        "listen_addr": "Listening at: {host}:{port}",
        "allowed_ports": "Allowed destination ports: {ports}",
        "saved_gw": "Saved as gateway: {gw_id}",
        "step4": "Send one observed HTTP proxy request through the local observation gateway.",
        "proxy_addr": "Proxy: {proxy}",
        "final_status": "Final HTTP status: {code}",
        "path_verified": "Path verified: {answer}",
        "yes": "yes",
        "no": "no",
        "error": "Error: {err}",
        "none": "none",
        "step5": "The gateway recorded this connection.",
        "no_records": "No connections were recorded by the gateway.",
        "step6": "Conclusion.",
        "conclusion_1": "The request traveled through the selected gateway with verifiable status and host records above.",
        "conclusion_2": "Proxy variables are scoped only to child processes or selected nodes; other sessions stay untouched.",
    },
    "zh-CN": {
        "step1": "准备一个临时配置，不会改动你正在使用的配置。",
        "config_file": "配置文件：",
        "step2": "选择一个请求目标。",
        "target_live": "目标：{target}（使用真实网络）",
        "target_local": "目标不可达，改用本机示例站点：{target}",
        "target_local_note": "本机站点使用随机端口，因此临时放行该端口，其余目的端口仍被拒绝。",
        "step3": "启动本机观测网关：它只监听回环地址，默认只允许 80 和 443 端口。",
        "listen_addr": "监听地址：{host}:{port}",
        "allowed_ports": "允许的目的端口：{ports}",
        "saved_gw": "已保存为网关：{gw_id}",
        "step4": "通过本机观测网关发送一次代理请求。",
        "proxy_addr": "代理：{proxy}",
        "final_status": "最终 HTTP 状态：{code}",
        "path_verified": "路径已核验：{answer}",
        "yes": "是",
        "no": "否",
        "error": "错误：{err}",
        "none": "无",
        "step5": "网关记录了这次访问。",
        "no_records": "网关没有记录到连接。",
        "step6": "结论。",
        "conclusion_1": "请求经过了你选择的网关，最终状态与访问目标都在上面可核对。",
        "conclusion_2": "代理变量只进入子进程；远程节点按账号或容器生效，其它进程不受影响。",
    },
}


class LocalOrigin(BaseHTTPRequestHandler):
    """A stand-in origin, used when the network is unavailable."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "11")
        self.end_headers()
        self.wfile.write(b"demo-origin")

    def log_message(self, *args):
        pass


def step(number, text):
    print("\n[{}] {}".format(number, text), flush=True)


def detail(text):
    print("      " + text, flush=True)


def start_local_origin():
    """Start a local origin on a free port and return (server, url)."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalOrigin)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    return server, "http://127.0.0.1:{}/demo".format(server.server_port)


def reachable(url):
    """True when the target answers at all."""
    try:
        import urllib.request
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=8) as response:
            return 200 <= response.status < 400
    except Exception:
        return False


def wait_for_records(gateway, attempts=100):
    """The gateway writes its record after the connection ends, so wait for it."""
    for _ in range(attempts):
        records = gateway.records_list()
        if records:
            return records
        time.sleep(0.05)
    return gateway.records_list()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Show the net-proxy-tool flow without a proxy.")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="the URL to request")
    parser.add_argument("--lang", default="en", choices=("en", "zh-CN"),
                        help="output language (default: en)")
    parser.add_argument("--keep-config", action="store_true",
                        help="keep the temporary configuration instead of removing it")
    args = parser.parse_args(argv)
    msg = MESSAGES[args.lang]

    temporary = tempfile.TemporaryDirectory(prefix="net-proxy-demo-")
    config_path = Path(temporary.name) / "config.json"
    previous = os.environ.get("NET_PROXY_CONFIG")
    os.environ["NET_PROXY_CONFIG"] = str(config_path)
    origin = None
    gateway = None
    try:
        step(1, msg["step1"])
        detail(msg["config_file"] + str(config_path))
        save_config(load_config())

        step(2, msg["step2"])
        target = args.target
        extra_ports = ()
        if reachable(target):
            detail(msg["target_live"].format(target=target))
        else:
            origin, local_url = start_local_origin()
            target = local_url
            extra_ports = (origin.server_address[1],)
            detail(msg["target_local"].format(target=target))
            detail(msg["target_local_note"])

        step(3, msg["step3"])
        allowed = (80, 443) + tuple(extra_ports)
        gateway = LocalGateway(port=0, allowed_ports=allowed)
        port = gateway.start()
        record = gateway.config_record()
        record["port"] = port
        detail(msg["listen_addr"].format(host=gateway.host, port=port))
        detail(msg["allowed_ports"].format(
            ports=", ".join(str(item) for item in sorted(gateway.allowed_ports))))

        config = load_config()
        config["gateways"] = [record]
        config["active_gateway_id"] = record["id"]
        save_config(config)
        detail(msg["saved_gw"].format(gw_id=record["id"]))

        step(4, msg["step4"])
        proxy = "http://127.0.0.1:{}".format(port)
        detail(msg["proxy_addr"].format(proxy=proxy))
        result = console.check_http_target("Demo probe", target, proxy, timeout=20)
        detail(msg["final_status"].format(code=result.get("code")))
        detail(msg["path_verified"].format(
            answer=msg["yes"] if result.get("path_verified") else msg["no"]))
        detail(msg["error"].format(err=result.get("error") or msg["none"]))

        step(5, msg["step5"])
        records = wait_for_records(gateway)
        if not records:
            detail(msg["no_records"])
        for record_line in records:
            detail("{} {}:{} → {}".format(record_line.get("method"), record_line.get("host"),
                                          record_line.get("port"), record_line.get("outcome")))

        step(6, msg["step6"])
        detail(msg["conclusion_1"])
        detail(msg["conclusion_2"])
        print("", flush=True)
        return 0
    finally:
        if gateway is not None:
            gateway.stop()
        if origin is not None:
            origin.shutdown()
            origin.server_close()
        if previous is None:
            os.environ.pop("NET_PROXY_CONFIG", None)
        else:
            os.environ["NET_PROXY_CONFIG"] = previous
        if not args.keep_config:
            temporary.cleanup()


if __name__ == "__main__":
    sys.exit(main())
