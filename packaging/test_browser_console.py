"""Exercise the public Web UI in Chromium with two recording proxies and isolated node dispatch."""
import argparse
from contextlib import ExitStack, contextmanager
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import tempfile
import sys
from threading import Thread
from unittest.mock import patch

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "test"))
import gateway_tls_fixture
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


def gateway_failure_flow(page, url):
    """Run the wizard through a real EOF, trusted TLS redirects and a stalled last hop."""
    with gateway_tls_fixture.redirect_then_stall() as proxy:
        cfg = load_config()
        gateway = dict(id="tls-fixture", name="TLS fixture", host="127.0.0.1", port=proxy.server_port, protocol="http")
        cfg["gateways"].append(gateway)
        cfg["clients"] = [dict(id="fixture-node", name="Fixture node", host="fixture.invalid",
                               access_mode="ssh", os_type="linux", bound_gateway_id=gateway["id"])]
        save_config(cfg)
        page.goto(url)
        page.locator("#advanced-wizard > summary").click()
        page.locator("#wizard-gw-select").select_option(gateway["id"])
        target = page.locator("#wizard-test-url")
        target.fill(gateway_tls_fixture.START)
        test = page.locator("#wizard-test-gw-btn")
        result = page.locator("#step-1-result")
        with patch.object(server, "check_http_target", partial(server.check_http_target, timeout=2)):
            with page.expect_response("**/api/test-gateway") as response:
                test.click()
        body = response.value.json()
        expect(result.locator("strong")).to_have_text("TLS 握手超时 · " + gateway_tls_fixture.FINAL + " 未返回最终 HTTP 响应")
        result.locator("summary").click()
        for evidence in ("TLS 握手 EOF", "第 1 跳（重试）", gateway_tls_fixture.SECOND,
                         "第 3 跳", "首跳 HTTP 302 → 未收到最终 HTTP 状态"):
            expect(result).to_contain_text(evidence)
        assert proxy.log == gateway_tls_fixture.EXPECTED_LOG
        command = page.locator("#wizard-probe-command").text_content()
        assert gateway_tls_fixture.START in command and str(proxy.server_port) in command and " -I" not in command
        assert page.locator("#card-step-2").evaluate("el => el.inert")
        before = load_config()
        with patch.object(server, "check_node_requests", return_value={"message": "只读请求已完成"}) as checked:
            page.locator("#wizard-readonly-test").click()
            expect(page.locator("#wizard-readonly-output")).to_contain_text("只读请求已完成")
        assert checked.call_args.args[0]["id"] == "fixture-node"
        assert checked.call_args.args[1]["id"] == gateway["id"]
        assert checked.call_args.args[2] == gateway_tls_fixture.START
        assert load_config() == before
        page.locator("#wizard-compare").click()
        expect(page.locator("#sb-gw-override-select")).to_have_value(gateway["id"])
        expect(page.locator("#sb-cmd-input")).to_have_value(gateway_tls_fixture.START)
        page.locator('[data-tab="tab-wizard"]').click()
        pending = []
        page.route("**/api/test-gateway", lambda route: pending.append(route))
        with page.expect_request("**/api/test-gateway"):
            test.click()
        target.fill(gateway_tls_fixture.FINAL)
        target.fill(gateway_tls_fixture.START)
        with page.expect_request("**/api/test-gateway"):
            test.click()
        assert len(pending) == 2
        pending[1].fulfill(json=body)
        expect(result.locator("strong")).to_contain_text("TLS 握手超时")
        with page.expect_request_finished(lambda request: request.url.endswith("/api/test-gateway")):
            pending[0].fulfill(json={"online": True, "code": 200, "http_ok": True})
        expect(page.locator("#status-tag-step-1")).to_have_text("目标请求未成功")
        assert page.locator("#card-step-2").evaluate("el => el.inert")
        page.unroute("**/api/test-gateway")


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

        for control in page.locator("[data-target-input]").all():
            labels = control.locator("option").all_text_contents()
            for label in ("Google", "Claude", "ChatGPT", "YouTube", "Gemini", "Example", "GitHub", "GitHub Zen API", "自定义 URL"):
                assert label in labels, labels
            expect(page.locator("#" + control.get_attribute("data-target-input"))).to_have_value("https://www.google.com/")

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
        expect(form("setup-command")).to_contain_text("http://browser-fixture.invalid/forbidden")
        expect(form("setup-compare")).to_be_visible()
        form("setup-compare").click()
        again = "http://browser-fixture.invalid/forbidden"
        expect(form("sb-cmd-input")).to_have_value(again)
        expect(form("sb-gw-override-select")).to_have_value(gateways[1].gateway_id)
        before = list(gateways[1].requests)
        form("sb-run-btn").click()
        expect(form("sb-diag-rate-val")).to_have_text("HTTP 403")
        assert gateways[1].requests == before + [again]

        cfg = load_config()
        assert len(cfg["gateways"]) == 2
        cfg["diagnostic_targets"] = {"Redirect": {"url": START}, "Plain": FINAL,
                                     "Denied": "http://browser-fixture.invalid/forbidden"}
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
        expect(form("wizard-target-grid").locator(".t-pill.success")).to_have_count(2)
        expect(form("wizard-target-grid").locator(".t-pill.failed")).to_have_text("HTTP 403")
        expect(page.locator('[data-target-input="setup-url"] option', has_text="Redirect")).to_have_count(1)
        probes = []

        def probe(node, gateway=None, target_url=None):
            probes.append((node["id"], gateway and gateway["id"], target_url))
            code = 200 if gateway else 403
            return {
                "online": bool(gateway), "http_ok": bool(gateway), "business_ok": None if gateway else False,
                "status_line": "HTTP " + str(code), "target_url": target_url, "final_url": FINAL,
                "code": code, "first_status": 302, "final_status": code, "is_proxy_enabled": False,
                "redirects": [{"url": target_url, "code": 302, "location": FINAL}], "exit_code": 0,
                "peer": {"ip": "192.0.2.10" if gateway else "192.0.2.11", "port": 3128 if gateway else 443},
                "proxy_evidence": {"status": "selected_proxy" if gateway else "unknown"},
                "execution_identity": {"uid": "1000", "user": "qa", "home": "/home/qa",
                                       "curl_config": "/home/qa/.curlrc"},
                "auth_ok": True, "connect_status": 200 if gateway else None,
                "stages": {"ssh": "passed", "http": "passed" if gateway else "failed"},
            }

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
        expect(form("wizard-feedback-content")).to_contain_text("启用前已有的代理可能继续生效")

        def baseline_proxy(node, gateway=None, target_url=None):
            result = probe(node, gateway, target_url)
            result.update(online=True, code=200, http_ok=True, first_status=200, final_status=200,
                          business_ok=None, redirects=[], status_line="HTTP 200",
                          peer={"ip": "192.0.2.10", "port": 3128}, is_proxy_enabled=False)
            return result

        with patch.object(server, "check_node_http", side_effect=baseline_proxy):
            form("wizard-btn-node-test").click()
            output = form("wizard-feedback-content")
            expect(output).to_contain_text("托管配置记录 · 已关闭")
            expect(output).to_contain_text("普通 curl（目标当前设置） · 成功")
            expect(output).to_contain_text("与显式请求的代理对端一致")
        form("wizard-client-select").select_option("node-one")
        assert form("card-step-4").evaluate("el => el.inert")

        page.locator('[data-tab="tab-topology"]').click()
        prompts = []
        def cancel_batch(dialog):
            prompts.append(dialog.message)
            dialog.dismiss()
        page.once("dialog", cancel_batch)
        form("top-disable-all-btn").click()
        assert "启用前基线" in prompts[0] and "原有代理可能继续生效" in prompts[0]
        node = page.locator('tr', has=page.locator('[data-action="test-node-out"][data-id="node-two"]'))
        check = node.locator('[data-action="test-node-out"]')
        settings = node.locator("[data-node-target]")
        settings.select_option("https://claude.ai/")
        with patch.object(server, "check_node_http", side_effect=probe):
            check.click()
            expect(form("node-test-heading")).to_contain_text("node-two")
            expect(form("node-test-record")).to_contain_text("https://claude.ai/")
            expect(form("node-test-record")).to_contain_text("记录 · 已关闭")
            expect(form("node-test-record")).to_contain_text("公网出口 IP · 未核验")
            expect(form("node-test-checks")).to_contain_text("首跳 HTTP 302 → 最终 HTTP 200")
            expect(form("node-test-checks")).to_contain_text("首跳 HTTP 302 → 最终 HTTP 403")
            expect(form("node-test-checks")).to_contain_text("192.0.2.10:3128")
            expect(form("node-test-checks")).to_contain_text("192.0.2.11:443")
            expect(form("node-test-checks")).to_contain_text("与显式请求的代理对端不同")
            expect(form("node-test-checks")).to_contain_text("未验证登录状态及账户权限")
            expect(form("node-test-checks")).to_contain_text("/home/qa/.curlrc")
            assert probes[-2:] == [("node-two", gw, "https://claude.ai/") for gw in (None, gateways[1].gateway_id)]
            settings.select_option("")
            expect(form("node-test-results")).to_be_hidden()
            node.locator("[data-node-custom]").fill(START)
            check.click()
            expect(form("node-test-record")).to_contain_text(START)
            assert probes[-1][2] == START
            form("node-target-url").fill(FINAL)
            received = []
            page.once("dialog", lambda dialog: (received.append(dialog.message), dialog.accept()))
            form("top-health-check-btn").click()
            expect(form("top-health-check-btn")).to_be_enabled()
            assert received and FINAL in received[0]
            assert all(entry[2] == FINAL for entry in probes[-4:])

        cfg = load_config()
        cfg["diagnostic_targets"] = {}
        save_config(cfg)
        page.reload()
        expect(form("setup-save")).to_be_enabled()
        expect(form("setup-url")).to_have_value("https://www.google.com/")
        form("advanced-wizard").locator(":scope > summary").click()
        form("wizard-test-url").fill(START)
        form("wizard-test-gw-btn").click()
        form("wizard-confirm-client-btn").click()
        expect(form("wizard-target-grid")).to_contain_text("没有配置多站目标")
        form("wizard-start-diag-btn").click()
        expect(form("status-tag-step-3")).to_have_text("未配置多站目标")
        assert not form("card-step-4").evaluate("el => el.inert")

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
        cfg["clients"][1].update(host="127.0.0.1", access_mode="local", is_proxy_enabled=False)
        save_config(cfg)
        page.reload()
        page.locator('[data-tab="tab-topology"]').click()
        local_action = form("top-clients-tbody").locator('[data-action="toggle-client"][data-id="node-two"]')
        if os.name == "nt":
            local_action.click()
            expect(form("tab-sandbox")).to_be_visible()
            expect(form("sb-gw-override-select")).to_have_value(gateways[1].gateway_id)
        else:
            commands.clear()
            with patch.object(server, "apply_node_proxy", side_effect=dispatch):
                with page.expect_response("**/api/node-switch") as switched:
                    local_action.click()
                assert switched.value.json()["success"], switched.value.json()
            assert commands == [("node-two", gateways[1].gateway_id, "on")]
            expect(form("tab-topology")).to_be_visible()
        gateway_failure_flow(page, url)
        assert not errors, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path)
    run(parser.parse_args().screenshot)
    print("Browser regression checks passed.")
