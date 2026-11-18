"""Exercise the public Web UI in Chromium with two recording proxies and isolated node dispatch."""
import argparse
from contextlib import ExitStack, contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import tempfile
import sys
from threading import Thread
from unittest.mock import patch

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sdk.config import load_config, save_config
from web import server


START = "http://browser-fixture.invalid/start?client=browser"
FINAL = "http://browser-fixture.invalid/result"


class RecordingProxy(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append(self.path)
        if self.path == START:
            self.send_response(302)
            self.send_header("Location", FINAL)
        elif self.path == FINAL:
            self.send_response(200)
        else:
            self.send_response(403)
        self.end_headers()
        self.wfile.write(b"fixture proxy response")

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


def public_home(browser, url, screenshot):
    for theme, width in [("light", 1280), ("dark", 1280), ("light", 390), ("dark", 390)]:
        page = browser.new_page(color_scheme=theme, viewport={"width": width, "height": 840})
        page.goto(url)
        expect(page.locator("#setup-save")).to_be_enabled()
        assert page.evaluate("document.documentElement.scrollWidth") <= width
        if screenshot and theme == "dark" and width == 1280:
            page.screenshot(path=str(screenshot))
        page.close()


def run(screenshot=None):
    with ExitStack() as stack:
        temp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        stack.enter_context(patch.dict(os.environ, {"NET_PROXY_CONFIG": str(temp / "config.json")}))
        gateways = [stack.enter_context(listener(RecordingProxy)) for _ in range(2)]
        console = stack.enter_context(listener(server.ProxyConsoleHandler))
        url = "http://127.0.0.1:" + str(console.server_port)
        p = stack.enter_context(sync_playwright())
        browser = p.chromium.launch(executable_path=p.chromium.executable_path)
        stack.callback(browser.close)
        public_home(browser, url, screenshot)

        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        pending_config = []
        def hold_config(route):
            pending_config.append(route)
        page.route("**/api/config?*", hold_config)
        with page.expect_request("**/api/config?*"):
            page.goto(url)
        # A slow initial config cannot overwrite an edit or turn an add into an update.
        expect(page.locator("#setup-name")).to_be_disabled()
        expect(page.locator("#setup-save")).to_be_disabled()
        assert len(pending_config) == 1
        pending_config.pop().continue_()
        page.unroute("**/api/config?*", hold_config)
        expect(page.locator("#setup-name")).to_be_editable()
        def form(id):
            return page.locator("#" + id)

        def defer_readback():
            page.route("**/api/config?*", hold_config)

        def release_readback():
            expect(form("setup-url")).to_be_disabled()
            expect(form("setup-test")).to_be_disabled()
            expect(form("setup-save")).to_be_disabled()
            expect(form("setup-select")).to_be_disabled()
            assert len(pending_config) == 1
            pending_config.pop().continue_()
            page.unroute("**/api/config?*", hold_config)

        for i, gateway in enumerate(gateways):
            if i:
                form("setup-select").select_option("")
            form("setup-name").fill("gateway-" + str(i))
            form("setup-host").fill("127.0.0.1")
            form("setup-port").fill(str(gateway.server_port))
            defer_readback()
            with page.expect_request("**/api/config?*"):
                with page.expect_response(lambda r: r.url.endswith("/api/gateways/add")) as saved:
                    form("setup-save").click()
            release_readback()
            gateway.gateway_id = saved.value.json()["gateway"]["id"]
            expect(form("setup-select")).to_have_value(gateway.gateway_id)
            form("setup-url").fill(START)
            form("setup-test").click()
            expect(form("setup-result")).to_contain_text("HTTP 200")
            expect(form("setup-result")).to_contain_text(FINAL)
            expect(form("setup-command")).to_contain_text(START)
            assert gateway.requests == [START, FINAL]
        defer_readback()
        with page.expect_request("**/api/config?*"):
            form("setup-default").click()
        release_readback()
        expect(form("setup-default")).to_be_hidden()
        page.reload()
        expect(form("setup-select")).to_have_value(gateways[1].gateway_id)
        form("setup-url").fill("http://browser-fixture.invalid/forbidden")
        form("setup-test").click()
        expect(form("setup-result")).to_contain_text("HTTP 403")
        expect(form("setup-result")).to_contain_text("TCP 已连接")
        expect(form("setup-command")).to_be_hidden()

        cfg = load_config()
        assert len(cfg["gateways"]) == 2
        cfg["diagnostic_targets"] = {"Example": {"url": START}}
        cfg["clients"] = [dict(id=name, name=name, host=host, os_type="linux", access_mode="ssh",
                               bound_gateway_id=gateways[0].gateway_id)
                          for name, host in [("node-one", "192.0.2.1"), ("node-two", "192.0.2.2")]]
        save_config(cfg)
        page.reload()
        form("advanced-wizard").locator(":scope > summary").click()
        form("wizard-gw-select").select_option(gateways[1].gateway_id)
        form("wizard-test-url").fill(START)
        form("wizard-test-gw-btn").click()
        expect(form("status-tag-step-1")).to_contain_text("已就绪")
        form("wizard-client-select").select_option("node-two")
        form("wizard-confirm-client-btn").click()
        expect(form("status-tag-step-2")).to_contain_text("node-two")
        form("wizard-start-diag-btn").click()
        expect(form("handover-gw-name")).to_contain_text(str(gateways[1].server_port))
        probes = []

        def probe(node, gateway=None, target_url=None):
            probes.append((node["id"], gateway and gateway["id"], target_url))
            return {"online": bool(gateway), "status_line": "HTTP 200" if gateway else "HTTP 403",
                    "stages": {"http": "passed" if gateway else "failed"}}

        with patch.object(server, "check_node_http", side_effect=probe):
            form("wizard-btn-node-test").click()
            expect(form("wizard-feedback-content")).to_contain_text("显式指定网关 · 成功")
            expect(form("wizard-feedback-content")).to_contain_text("普通 curl（目标当前设置） · 未成功")
        assert probes == [("node-two", None, START), ("node-two", gateways[1].gateway_id, START)]
        commands = []
        def dispatch(node, action, config):
            commands.append((node["id"], node["bound_gateway_id"], action))
            return {"returncode": 0}

        with patch.object(server, "apply_node_proxy", side_effect=dispatch):
            form("wizard-btn-proxy-on").click()
            expect(form("wizard-feedback-badge")).to_contain_text("node-two")
            expect(form("wizard-client-select")).to_have_value("node-two")
            form("wizard-btn-proxy-off").click()
            expect(form("wizard-btn-proxy-off")).to_be_enabled()
        assert commands == [("node-two", gateways[1].gateway_id, action) for action in ("on", "off")]
        form("wizard-client-select").select_option("node-one")
        assert form("card-step-4").evaluate("el => el.inert")

        page.locator('[data-tab="tab-sandbox"]').click()
        for gw in gateways:
            form("sb-gw-override-select").select_option(gw.gateway_id)
            form("sb-cmd-input").fill(FINAL)
            before = len(gw.requests)
            form("sb-run-btn").click()
            expect(form("sb-terminal-output")).to_contain_text("fixture proxy response")
            expect(form("sb-diag-rate-val")).to_have_text("HTTP 200")
            assert gw.requests[before:] == [FINAL]
        cfg = load_config()
        cfg["clients"][1].update(os_type="windows", host="127.0.0.1")
        save_config(cfg)
        page.reload()
        page.locator('[data-tab="tab-topology"]').click()
        form("top-clients-tbody").locator('[data-action="toggle-client"][data-id="node-two"]').click()
        expect(form("tab-sandbox")).to_be_visible()
        expect(form("sb-gw-override-select")).to_have_value(gateways[1].gateway_id)
        assert not errors, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path)
    run(parser.parse_args().screenshot)
    print("Browser regression checks passed.")
