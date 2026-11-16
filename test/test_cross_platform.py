"""CLI, SDK, launcher and node-management regressions with isolated configuration."""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sdk.config import config_path, load_config, resolve_gateway, save_config
from sdk.proxy_session import ProxySession, is_gateway_alive
from web.server import ProxyConsoleHandler, ThreadingHTTPServer


class IsolatedTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="net proxy ")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "config.json"
        environment = patch.dict(os.environ, NET_PROXY_CONFIG=str(self.path))
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop("NET_PROXY_GATEWAY", None)


class CommandTests(IsolatedTest):
    def test_empty_and_legacy_config(self):
        self.assertEqual(config_path(), self.path)
        self.assertEqual(load_config()["clients"], [])
        self.assertFalse(self.path.exists())
        self.path.write_text('{"proxy_host":"127.0.0.1","proxy_port":17777}', encoding="utf-8")
        self.assertEqual(resolve_gateway(load_config()), ("127.0.0.1", 17777))
        self.assertEqual(resolve_gateway(load_config(), "[::1]:3128"), ("::1", 3128))
        self.path.write_text("{oops", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "config.json"):
            load_config()
        self.assertEqual(self.path.read_text(), "{oops")

    def test_probe_and_nested_session(self):
        with socket.socket() as gateway:
            gateway.bind(("127.0.0.1", 0))
            gateway.listen()
            endpoint = f"127.0.0.1:{gateway.getsockname()[1]}"
            self.assertTrue(is_gateway_alive(endpoint))
            os.environ["HTTP_PROXY"] = "previous"
            with ProxySession(endpoint) as url:
                self.assertEqual(os.environ["HTTP_PROXY"], url)
                with self.assertRaises(RuntimeError), ProxySession("localhost:1234", check=False):
                    raise RuntimeError("test")
                self.assertEqual(os.environ["HTTP_PROXY"], url)
            self.assertEqual(os.environ["HTTP_PROXY"], "previous")

    def test_cli_exit_code_and_quoted_arguments(self):
        cmd = [sys.executable, str(ROOT / "with_proxy.py"), "--gateway", "localhost:1234",
               "--no-check", sys.executable, "-c",
               "import os,sys; print(os.environ['HTTP_PROXY'],sys.argv[1]);sys.exit(37)", "two words"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertIn("http://localhost:1234 two words", result.stdout)


class WebApiTests(IsolatedTest):
    def test_node_crud_switch_and_audit(self):
        cfg = load_config()
        cfg["gateways"] = [{"id": "gw", "host": "127.0.0.1", "port": 7890}]
        cfg["active_gateway_id"] = "gw"
        save_config(cfg)
        with ThreadingHTTPServer(("127.0.0.1", 0), ProxyConsoleHandler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def api(path, payload=None):
                    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                    try:
                        body = None if payload is None else json.dumps(payload)
                        conn.request("GET" if payload is None else "POST", path, body,
                                     {"Content-Type": "application/json"})
                        response = conn.getresponse()
                        data = json.load(response)
                        self.assertEqual(response.status, 200, data)
                        return data
                    finally:
                        conn.close()
                node = {"id": "n1", "name": "fixture", "host": "node.example",
                        "bound_gateway_id": "gw", "os_type": "linux", "ssh_user": "tester"}
                self.assertTrue(api("/api/clients/add", node)["success"])
                self.assertTrue(api("/api/clients/update", {"id": "n1", "name": "updated"})["success"])
                with patch("web.server.apply_node_proxy", return_value={"returncode": 0}) as dispatch:
                    self.assertTrue(api("/api/node-switch", {"node_id": "n1", "action": "on"})["success"])
                    self.assertTrue(api("/api/nodes/batch-switch", {"action": "off"})["success"])
                    self.assertEqual(dispatch.call_count, 2)
                self.assertTrue(api("/api/clients/delete", {"id": "n1"})["success"])
                self.assertTrue(api("/api/audit-logs")["logs"])
            finally:
                server.shutdown()
                thread.join()


class LauncherTests(IsolatedTest):
    def launch(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "launcher.py"), *args],
                              capture_output=True, text=True, timeout=22)

    def test_start_reuse_and_stop(self):
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = str(reservation.getsockname()[1])
        self.addCleanup(self.launch, "--stop")
        first = self.launch(port, "--no-browser")
        self.assertEqual(first.returncode, 0, first.stderr)
        state_file = self.path.parent / "data/instance.json"
        original = json.loads(state_file.read_text())
        self.assertEqual(self.launch(port, "--no-browser").returncode, 0)
        self.assertEqual(json.loads(state_file.read_text()), original)
        self.assertEqual(self.launch("--stop").returncode, 0)
        self.assertFalse(state_file.exists())

    def test_port_collision_leaves_other_service_running(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), ProxyConsoleHandler) as other:
            thread = threading.Thread(target=other.serve_forever, daemon=True)
            thread.start()
            try:
                result = self.launch(str(other.server_port), "--no-browser")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.path.parent / "data/instance.json").exists())
                self.assertEqual(self.launch("--stop").returncode, 0)
                with socket.create_connection(other.server_address, timeout=2):
                    pass
            finally:
                other.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
