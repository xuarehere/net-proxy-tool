import hashlib
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
        if data is not None and path in ('/api/clients/update', '/api/clients/delete', '/api/node-switch'):
            data = dict(data)
            node = next((item for item in load_config().get('clients', [])
                         if item['id'] == data.get('node_id', data.get('id'))), None)
            if node:
                data.setdefault('node_revision', node.get('node_revision', 0))
        conn = http.client.HTTPConnection(*self.web.server_address, timeout=6)
        try:
            request_headers = dict(headers or {})
            if data is not None:
                request_headers.setdefault("Content-Type", "application/json")
            conn.request("GET" if data is None else "POST", path,
                         None if data is None else json.dumps(data), request_headers)
            response = conn.getresponse()
            body = response.read()
            if response.headers.get_content_type() == "application/json":
                body = json.loads(body)
            return response.status, body
        finally:
            conn.close()

    def test_first_run_and_proxy_forwarding(self):
        self.assertEqual(self.request("/api/config")[1]["gateways"], [])
        self.assertIsNone(self.request("/api/status")[1]["gateway"])
        self.assertEqual(self.request("/api/status?gateway_id=missing")[0], 404)
        self.assertIn(b'id="setup-form"', self.request("/")[1])
        with patch.dict(os.environ, {"NET_PROXY_INSTANCE_TOKEN": "private-token"}):
            health = self.request("/api/health")[1]
            self.assertEqual(health["service"], "net-proxy-tool")
            self.assertEqual(health["instance_id"], hashlib.sha256(b"private-token").hexdigest())
            self.assertNotIn("private-token", repr(health))
        hits = []

        class Proxy(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                self.send_response({"auth": 407, "redirect": 301}.get(self.path.rsplit("/", 1)[-1], 204))
                self.end_headers()

            def do_CONNECT(self):
                self.send_response(407)
                self.end_headers()

        proxy = self.start_server(Proxy)
        gateway = {"name": "test", "host": "127.0.0.1", "port": proxy.server_port}
        status, added = self.request("/api/gateways/add", gateway)
        self.assertEqual(status, 200)
        cfg = self.request("/api/config")[1]
        self.assertEqual(cfg["active_gateway_id"], added["gateway"]["id"])
        self.assertEqual(hits, [])
        for suffix, expected in (("ok", 204), ("auth", 407), ("redirect", 301)):
            url = "http://test.invalid/" + suffix
            _, result = self.request("/api/test-gateway", dict(gateway, target_url=url))
            self.assertTrue(result["tcp_ok"])
            self.assertEqual(result["code"], expected)
            self.assertEqual(result["online"], expected == 204)
            self.assertEqual(hits[-1], url)
        _, refused = self.request("/api/test-gateway", dict(gateway, target_url="https://no-dns.invalid/"))
        self.assertTrue(refused["tcp_ok"])
        self.assertFalse(refused["online"])
        self.assertEqual(refused["code"], 407)

    def test_docker_host_port_and_validation(self):
        node = {"id": "c", "name": "Container", "host": "127.0.0.1", "ssh_user": "runner",
                "access_mode": "docker_host", "port": 2222, "container_name": "worker"}
        self.assertEqual(self.request("/api/clients/add", node)[0], 200)
        for invalid in ({"container_name": "c; touch injected"}, {"ssh_host": "::1%$(echo x)"},
                        {"ssh_user": "-oProxyCommand=bad"}):
            self.assertEqual(self.request("/api/clients/update", dict(invalid, id="c"))[0], 400)
        with patch.object(server, "check_tcp_port", return_value=(True, 1)) as tcp, \
                patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"true", b"")) as run:
            self.assertTrue(self.request("/api/test-node-preflight", node)[1]["success"])
            tcp.assert_called_once_with("127.0.0.1", 2222, timeout=2.5)
            self.assertEqual(run.call_args.args[0][1:3], ["-p", "2222"])
        result = subprocess.CompletedProcess([], 0, b"407", b"")
        with patch.object(subprocess, "run", return_value=result) as run:
            for path, payload in (("/api/node-test", {"node_id": "c"}), ("/api/nodes/health-check-all", {})):
                data = self.request(path, payload)[1]
                self.assertFalse(data.get("health_map", {}).get("c", data)["online"])
                self.assertEqual(run.call_args.args[0][1:3], ["-p", "2222"])
        baseline = {'ok': True, 'managed': {'state': 'enabled', 'restoration_manifest': {'fixture': 'fingerprint'}}}
        verified = {'verified': True, 'status': 'restored', 'verification_scope': 'managed_files_only', 'checks': {}}
        with patch.object(server.node_baseline, 'capture_node_baseline', return_value=baseline), \
                patch.object(server.node_baseline, 'verify_node_baseline', return_value=verified), \
                patch.object(server, 'run_node_script', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
            self.assertTrue(self.request("/api/node-switch", {"node_id": "c", "action": "off"})[1]["success"])
            self.assertEqual(run.call_args.args[0]['access_mode'], 'docker_host')
            self.assertIn('action=off', run.call_args.args[1])

    def test_cross_origin_and_password(self):
        self.assertEqual(self.request("/api/config", headers={"Host": "rebind.invalid"})[0], 403)
        self.assertEqual(self.request("/api/config", {}, {"Origin": "https://foreign.invalid"})[0], 403)
        self.assertEqual(self.request("/api/shutdown", {})[0], 403)
        payload = {"id": "node", "name": "test", "host": "test.invalid", "auth_type": "password", "ssh_pass": "q'$42"}
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
            _, batch = self.request("/api/nodes/batch-switch", {"action": "on", 'nodes': [
                {'node_id': 'c', 'node_revision': load_config()['clients'][0]['node_revision']}]})
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
        (home / ".net-proxy-switch.sh").write_text("export HTTP_PROXY=legacy\n", encoding="utf-8")
        result = switch("off")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((home / ".net-proxy-switch.sh").exists())
        self.assertEqual((home / ".curlrc").read_bytes(), original)
        for action in ("on", "off"):
            result = switch(action)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((home / ".net-proxy-switch.sh").exists())
        self.assertEqual((home / ".curlrc").read_bytes(), original)
        self.assertEqual(switch("on").returncode, 0)
        managed = (home / ".curlrc").read_bytes()
        (home / ".profile").write_text("export EDIT=1\n", encoding="utf-8")
        self.assertNotEqual(switch("off").returncode, 0)
        self.assertEqual((home / ".curlrc").read_bytes(), managed)
