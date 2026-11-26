"""Run the whole flow of net-proxy-tool in one process and narrate it.

The demo needs no existing proxy: it starts the local observation gateway,
saves it as a gateway, sends one request through it and shows the connections
the gateway saw. It uses a temporary configuration and never changes the
configuration of the operator.

    python -X utf8 tools/demo.py
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
    parser.add_argument("--keep-config", action="store_true",
                        help="keep the temporary configuration instead of removing it")
    args = parser.parse_args(argv)

    temporary = tempfile.TemporaryDirectory(prefix="net-proxy-demo-")
    config_path = Path(temporary.name) / "config.json"
    previous = os.environ.get("NET_PROXY_CONFIG")
    os.environ["NET_PROXY_CONFIG"] = str(config_path)
    origin = None
    gateway = None
    try:
        step(1, "准备一个临时配置，不会改动你正在使用的配置。")
        detail("配置文件：" + str(config_path))
        save_config(load_config())

        step(2, "选择一个请求目标。")
        target = args.target
        extra_ports = ()
        if reachable(target):
            detail("目标：" + target + "（使用真实网络）")
        else:
            origin, local_url = start_local_origin()
            target = local_url
            extra_ports = (origin.server_address[1],)
            detail("目标不可达，改用本机示例站点：" + target)
            detail("本机站点使用随机端口，因此临时放行该端口，其余目的端口仍被拒绝。")

        step(3, "启动本机观测网关：它只监听回环地址，默认只允许 80 和 443 端口。")
        allowed = (80, 443) + tuple(extra_ports)
        gateway = LocalGateway(port=0, allowed_ports=allowed)
        port = gateway.start()
        record = gateway.config_record()
        record["port"] = port
        detail("监听地址：" + str(gateway.host) + ":" + str(port))
        detail("允许的目的端口：" + ", ".join(str(item) for item in sorted(gateway.allowed_ports)))

        config = load_config()
        config["gateways"] = [record]
        config["active_gateway_id"] = record["id"]
        save_config(config)
        detail("已保存为网关：" + record["id"])

        step(4, "通过本机观测网关发送一次代理请求。")
        proxy = "http://127.0.0.1:{}".format(port)
        detail("代理：" + proxy)
        result = console.check_http_target("Demo probe", target, proxy, timeout=20)
        detail("最终 HTTP 状态：" + str(result.get("code")))
        detail("路径已核验：" + ("是" if result.get("path_verified") else "否"))
        detail("错误：" + str(result.get("error") or "无"))

        step(5, "网关记录了这次访问。")
        records = wait_for_records(gateway)
        if not records:
            detail("网关没有记录到连接。")
        for record_line in records:
            detail("{} {}:{} → {}".format(record_line.get("method"), record_line.get("host"),
                                          record_line.get("port"), record_line.get("outcome")))

        step(6, "结论。")
        detail("请求经过了你选择的网关，最终状态与访问目标都在上面可核对。")
        detail("代理变量只进入子进程；远程节点按账号或容器生效，其它进程不受影响。")
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
