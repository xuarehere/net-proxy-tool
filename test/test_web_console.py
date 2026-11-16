import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from sdk.config import load_config, save_config
from web import server


class TestWebConsole(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {"NET_PROXY_CONFIG": str(Path(self.temp.name, "config.json"))})
        env.start()
        self.addCleanup(env.stop)
        self.web = self.start_server(server.ProxyConsoleHandler)

    def start_server(self, handler):
        listener = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        worker = threading.Thread(target=listener.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(listener.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(listener.shutdown)
        return listener

    def request(self, path, data=None, headers=None):
        conn = http.client.HTTPConnection(*self.web.server_address, timeout=6)
        try:
            conn.request("GET" if data is None else "POST", path,
                         None if data is None else json.dumps(data), headers or {})
            response = conn.getresponse()
            body = response.read()
            if response.headers.get_content_type() == "application/json":
                body = json.loads(body)
            return response.status, body
        finally:
            conn.close()

    def test_first_run_and_proxy_forwarding(self):
        self.assertEqual(self.request("/api/config")[1]["gateways"], [])
        self.assertIn(b'id="setup-form"', self.request("/")[1])
        self.assertEqual(self.request("/api/health")[1]["service"], "net-proxy-tool")
        hits = []

        class Proxy(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                self.send_response(407 if self.path.endswith("/auth") else 204)
                self.end_headers()

        proxy = self.start_server(Proxy)
        gateway = {"name": "test", "host": "127.0.0.1", "port": proxy.server_port}
        status, added = self.request("/api/gateways/add", gateway)
        self.assertEqual(status, 200)
        cfg = self.request("/api/config")[1]
        self.assertEqual(cfg["active_gateway_id"], added["gateway"]["id"])
        self.assertEqual(hits, [])
        for suffix, expected in (("ok", 204), ("auth", 407)):
            url = "http://test.invalid/" + suffix
            _, result = self.request("/api/test-gateway", dict(gateway, target_url=url))
            self.assertTrue(result["tcp_ok"])
            self.assertEqual(result["code"], expected)
            self.assertEqual(result["online"], expected == 204)
            self.assertEqual(hits[-1], url)

    def test_cross_origin_and_password(self):
        self.assertEqual(self.request("/api/config", headers={"Host": "rebind.invalid"})[0], 403)
        self.assertEqual(self.request("/api/config", {}, {"Origin": "https://foreign.invalid"})[0], 403)
        self.assertEqual(self.request("/api/shutdown", {})[0], 403)
        payload = {"id": "node", "name": "test", "host": "test.invalid", "ssh_pass": "q'$42"}
        self.assertNotIn("ssh_pass", self.request("/api/clients/add", payload)[1]["client"])
        self.assertNotIn("ssh_pass", self.request("/api/config")[1]["clients"][0])
        self.request("/api/clients/update", {"id": "node", "name": "new", "ssh_pass": ""})
        self.assertEqual(load_config()["clients"][0]["ssh_pass"], payload["ssh_pass"])

    def test_failed_dispatch_keeps_previous_state(self):
        self.request("/api/gateways/add", {"id": "gw", "name": "g", "host": "proxy.test", "port": 3128})
        self.request("/api/clients/add", {"id": "c", "name": "c", "host": "node.test", "bound_gateway_id": "gw"})
        with patch.object(server, "apply_node_proxy", return_value={"error": "offline"}):
            status, body = self.request("/api/node-switch", {"node_id": "c", "action": "on"})
            self.assertEqual(status, 502)
            self.assertFalse(body["success"])
            _, batch = self.request("/api/nodes/batch-switch", {"action": "on"})
            self.assertFalse(batch["success"])
        self.assertFalse(load_config()["clients"][0]["is_proxy_enabled"])

    def test_startup_does_not_dispatch(self):
        cfg = load_config()
        cfg["clients"] = [{"id": "legacy", "host": "old.invalid", "is_proxy_enabled": True}]
        save_config(cfg)
        with patch.object(server, "ThreadingHTTPServer") as srv, patch.object(server, "apply_node_proxy") as apply:
            server.run_server(0, "127.0.0.1")
            apply.assert_not_called()
            self.assertEqual(srv.call_args[0][0], ("127.0.0.1", 0))

    @unittest.skipUnless(sys.platform.startswith("linux") and hasattr(os, "getuid") and os.getuid() != 0,
                         "requires an unprivileged Linux shell")
    def test_switch_restores_custom_files(self):
        home = Path(self.temp.name)
        original = b"--silent\n"
        (home / ".curlrc").write_bytes(original)
        (home / ".profile").write_text("export CUSTOM=1\n", encoding="utf-8")
        proxy = "http://127.0.0.1:7890"
        def switch(action):
            script = server.generate_provisioning_script(proxy, "localhost", action)
            return subprocess.run(["sh"], input=script, env=dict(os.environ, HOME=str(home)),
                                  text=True, capture_output=True)
        for action in ("on", "on", "off", "off"):
            result = switch(action)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((home / ".curlrc").read_bytes(), original)
        self.assertEqual((home / ".profile").read_text(encoding="utf-8"), "export CUSTOM=1\n")
        self.assertFalse((home / ".wgetrc").exists())
