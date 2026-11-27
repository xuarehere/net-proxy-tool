"""Exercise an extracted release using its real launcher, a local test proxy and optional Chromium."""
import argparse
import http.client
import json
import os
import socket
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TARGET = "http://portable-check.invalid/release-smoke"


class RecordingProxy(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.seen.append(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"portable proxy fixture")

    do_HEAD = do_GET

    def log_message(self, *args):
        pass


def api(port, path, payload=None, token=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=90)
    try:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Cookie"] = "npt_access=" + token
        conn.request("POST" if data else "GET", path, data, headers)
        res = conn.getresponse()
        body = res.read()
        if res.status != 200:
            raise RuntimeError(f"{path}: {res.status} {body[:200]!r}")
        return json.loads(body)
    finally:
        conn.close()


def browser_setup(port, gateway):
    import re
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"http://127.0.0.1:{port}/")
        page.locator("#setup-name").fill(gateway["name"])
        page.locator("#setup-host").fill(gateway["host"])
        page.locator("#setup-port").fill(str(gateway["port"]))
        with page.expect_response(lambda r: "/api/gateways/add" in r.url) as response:
            page.locator("#setup-save").click()
        assert response.value.ok, response.value.status
        page.locator("#setup-url").fill(TARGET)
        with page.expect_response(lambda r: "/api/test-gateway" in r.url) as tested:
            page.locator("#setup-test").click()
        assert tested.value.json()["success"]
        page.locator("#setup-result", has_text=re.compile(r"代理请求成功|Proxy request succeeded")).wait_for()
        assert "HTTP 200" in page.locator("#setup-result").inner_text()
        assert not errors, errors
        browser.close()


def run(root, browser=False):
    root = root.resolve()
    windows = os.name == "nt"
    command = [str(root / ("Start.bat" if windows else "net-proxy-tool"))]
    runtime = root / ("runtime/python.exe" if windows else "runtime/bin/python3")
    assert runtime.is_file(), runtime
    with tempfile.TemporaryDirectory(prefix="net-proxy 中文 ") as tmp:
        config = Path(tmp) / "config.json"
        env = dict(os.environ, NET_PROXY_CONFIG=str(config), PYTHONUTF8="1")
        if windows:
            env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]

        def launch(*args):
            try:
                subprocess.run(command + list(args), cwd=tmp, env=env, stdin=subprocess.DEVNULL,
                               check=True, timeout=30)
            except subprocess.SubprocessError:
                log = config.parent / "data/console.log"
                if log.is_file():
                    print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-15:]))
                raise

        with ThreadingHTTPServer(("127.0.0.1", 0), RecordingProxy) as proxy:
            proxy.seen = []
            thread = threading.Thread(target=proxy.serve_forever, daemon=True)
            thread.start()
            gateway = {"name": "Portable smoke", "host": "127.0.0.1", "port": proxy.server_port,
                       "protocol": "http"}
            try:
                launch(str(port), "--no-browser")
                assert api(port, "/api/health")["service"] == "net-proxy-tool"
                assert not api(port, "/api/config")["gateways"]
                if browser:
                    browser_setup(port, gateway)
                else:
                    assert api(port, "/api/gateways/add", gateway)["success"]
                    result = api(port, "/api/test-gateway", dict(gateway, target_url=TARGET))
                    assert result.get("success"), result
                assert TARGET in proxy.seen, proxy.seen
                proxy.seen.clear()
                cli = "import urllib.request; assert urllib.request.urlopen(%r).read() == b'portable proxy fixture'" % TARGET
                subprocess.run([str(runtime), str(root / "with_proxy.py"), str(runtime), "-c", cli],
                               env=env, cwd=tmp, check=True, timeout=20)
                assert TARGET in proxy.seen
                launch("--stop")
                launch(str(port), "--no-browser")
                assert api(port, "/api/config")["gateways"][0]["port"] == gateway["port"]
            finally:
                try:
                    if (config.parent / "data/instance.json").is_file():
                        launch("--stop")
                finally:
                    proxy.shutdown()
                    thread.join()
        legacy = {"proxy_host": "127.0.0.1", "proxy_port": 7812}
        config.write_text(json.dumps(legacy), encoding="utf-8")
        launch(str(port), "--no-browser")
        try:
            assert api(port, "/api/config")["gateways"][0]["port"] == 7812
        finally:
            launch("--stop")
    print("Portable first run, real proxy request, restart and legacy config passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--browser", action="store_true")
    args = parser.parse_args()
    run(args.root, args.browser)
