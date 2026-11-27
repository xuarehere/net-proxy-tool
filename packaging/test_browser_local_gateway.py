"""Check the local observation gateway entry points in Chromium."""
import argparse
from contextlib import ExitStack, contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
import tempfile
from threading import Thread
from unittest.mock import patch

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sdk.config import load_config, save_config  # noqa: E402
from web import server  # noqa: E402


class DemoOrigin(BaseHTTPRequestHandler):
    """The origin the demo request reaches, standing in for the internet."""

    def do_GET(self):
        self.server.requests.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "11")
        self.end_headers()
        self.wfile.write(b"demo-origin!")

    def log_message(self, *args):
        pass


@contextmanager
def listener(handler):
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as httpd:
        httpd.requests = []
        thread = Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield httpd
        finally:
            httpd.shutdown()
            thread.join()


def run():
    with ExitStack() as stack:
        temp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        stack.enter_context(patch.dict(os.environ, {"NET_PROXY_CONFIG": str(temp / "config.json")}))
        origin = stack.enter_context(listener(DemoOrigin))
        console = stack.enter_context(listener(server.ProxyConsoleHandler))
        url = "http://127.0.0.1:" + str(console.server_port)

        p = stack.enter_context(sync_playwright())
        browser = p.chromium.launch(executable_path=p.chromium.executable_path)
        stack.callback(browser.close)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)

        # The first run offers the two entry points.
        expect(page.locator("#local-gateway-start")).to_be_visible()
        expect(page.locator("#local-gateway-demo")).to_be_visible()

        # Starting the gateway shows its address and saves it as a gateway.
        page.locator("#local-gateway-start").click()
        expect(page.locator("#local-gateway-state")).to_contain_text("127.0.0.1:")
        expect(page.locator("#local-gateway-stop")).to_be_visible()
        gateways = load_config()["gateways"]
        assert any(gateway["id"] == "local-gateway" for gateway in gateways), gateways

        # Stopping the gateway removes it again.
        page.locator("#local-gateway-stop").click()
        expect(page.locator("#local-gateway-start")).to_be_visible()
        assert not any(gateway["id"] == "local-gateway"
                       for gateway in load_config()["gateways"])

        # The demo starts the gateway and sends one request through it to the demo origin.
        def probe(name, target_info, proxy_url, timeout=15.0, include_preview=False):
            return {"name": name, "url": target_info, "status": "online", "http_ok": True,
                    "path_verified": True, "code": 200, "final_url": target_info,
                    "proxy_url": proxy_url, "attempts": [], "redirects": []}

        with patch.object(server, "check_http_target", side_effect=probe):
            page.locator("#local-gateway-demo").click()
            expect(page.locator("#setup-result")).to_contain_text("HTTP 200", timeout=15000)
        expect(page.locator("#local-gateway-state")).to_contain_text("127.0.0.1:")

        # Clean up by stopping the gateway.
        page.locator("#local-gateway-stop").click()
        expect(page.locator("#local-gateway-start")).to_be_visible()
        assert not any(gateway["id"] == "local-gateway"
                       for gateway in load_config()["gateways"])
        assert not errors, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()
    run()
    print("Local observation gateway browser checks passed.")
