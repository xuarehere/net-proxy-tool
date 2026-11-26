"""Check the node pool in Chromium: independent results, a complete menu, a loopback warning."""
import argparse
from contextlib import ExitStack, contextmanager
from http.server import ThreadingHTTPServer
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


def node_probe_result(name, code):
    """A read-only result for one node, as the console renders it."""
    return {
        "message": "只读请求已完成", "success": code == 200, "online": code == 200,
        "http_ok": code == 200, "code": code, "first_status": code, "final_status": code,
        "status_line": "HTTP " + str(code), "target_url": "http://node-fixture.invalid/probe",
        "final_url": "http://node-fixture.invalid/probe", "is_proxy_enabled": False,
        "redirects": [], "exit_code": 0, "auth_ok": True, "connect_status": 200,
        "peer": {"ip": "192.0.2.10", "port": 3128},
        "proxy_evidence": {"status": "selected_proxy"},
        "execution_identity": {"uid": "1000", "user": "qa", "home": "/home/qa",
                               "curl_config": "/home/qa/.curlrc"},
        "stages": {"ssh": "passed", "http": "passed" if code == 200 else "failed"},
        "node_id": name,
    }


def run():
    with ExitStack() as stack:
        temp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        stack.enter_context(patch.dict(os.environ, {"NET_PROXY_CONFIG": str(temp / "config.json")}))
        console = stack.enter_context(listener(server.ProxyConsoleHandler))
        url = "http://127.0.0.1:" + str(console.server_port)

        cfg = load_config()
        cfg["gateways"] = [
            {"id": "loopback-gw", "name": "Loopback gateway", "host": "127.0.0.1", "port": 3128,
             "protocol": "http", "is_default": True},
            {"id": "reachable-gw", "name": "Reachable gateway", "host": "192.0.2.10", "port": 3128,
             "protocol": "http"},
        ]
        cfg["active_gateway_id"] = "loopback-gw"
        cfg["clients"] = [
            {"id": "node-one", "name": "Node one", "host": "192.0.2.1", "port": 22,
             "access_mode": "ssh", "os_type": "linux", "ssh_user": "tester",
             "bound_gateway_id": "loopback-gw"},
            {"id": "node-two", "name": "Node two", "host": "192.0.2.2", "port": 22,
             "access_mode": "ssh", "os_type": "linux", "ssh_user": "tester",
             "bound_gateway_id": "reachable-gw"},
        ]
        save_config(cfg)

        p = stack.enter_context(sync_playwright())
        browser = p.chromium.launch(executable_path=p.chromium.executable_path)
        stack.callback(browser.close)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        page.locator('[data-tab="tab-topology"]').click()

        # Two nodes tested at the same time keep their own result.
        answers = {}

        def route_probe(route):
            node = route.request.post_data_json.get("node_id")
            answers[node] = route
            route.continue_()

        page.route("**/api/node-test", route_probe)
        one = page.locator('tr', has=page.locator('[data-action="test-node-out"][data-id="node-one"]'))
        two = page.locator('tr', has=page.locator('[data-action="test-node-out"][data-id="node-two"]'))
        one.locator('[data-action="test-node-out"]').click()
        two.locator('[data-action="test-node-out"]').click()
        page.wait_for_timeout(300)
        assert set(answers) == {"node-one", "node-two"}, answers
        answers["node-one"].fulfill(json=node_probe_result("node-one", 200))
        answers["node-two"].fulfill(json=node_probe_result("node-two", 403))
        page.wait_for_timeout(300)
        expect(page.locator("#node-test-heading")).to_contain_text("node-two")
        expect(page.locator("#node-test-record")).to_contain_text("HTTP 403")
        expect(one.locator(".rtt-pill")).to_have_text("HTTP 成功")
        expect(two.locator(".rtt-pill")).to_have_text("查看结果")
        page.unroute("**/api/node-test")

        # The action menu opens complete, outside the table.
        menu = two.locator(".action-dropdown-menu")
        expect(menu).to_be_hidden()
        two.locator(".btn-dropdown-toggle").click()
        expect(menu).to_be_visible()
        box = menu.bounding_box()
        assert box is not None
        assert box["x"] >= 0 and box["y"] >= 0, box
        assert box["x"] + box["width"] <= page.viewport_size["width"] + 1, box
        assert box["y"] + box["height"] <= page.viewport_size["height"] + 1, box
        assert menu.evaluate("el => getComputedStyle(el).position") == "fixed"
        two.locator(".btn-dropdown-toggle").click()

        # A remote node on a loopback gateway asks before it is switched on.
        prompts = []
        commands = []

        def dispatch(node, action, config):
            commands.append((node["id"], action))
            return {"returncode": 0}

        page.once("dialog", lambda dialog: (prompts.append(dialog.message), dialog.dismiss()))
        with patch.object(server, "apply_node_proxy", side_effect=dispatch):
            one.locator('[data-action="toggle-client"]').click()
            page.wait_for_timeout(300)
        assert prompts, "the loopback gateway did not ask for a confirmation"
        assert "127.0.0.1" in prompts[0], prompts[0]
        assert commands == [], commands

        # The console reports its own addresses.
        addresses = page.evaluate("fetch('/api/host-addresses').then(r => r.json())")
        assert addresses["count"] >= 1, addresses
        assert not errors, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()
    run()
    print("Node pool browser checks passed.")
