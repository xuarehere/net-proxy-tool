"""Regressions for the console's local observation gateway."""
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from sdk.config import load_config
from web import server
from web.local_gateway import LocalGateway


class ConsoleLocalGatewayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="npt-console-gw-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "config.json"
        patcher = patch.dict(os.environ, NET_PROXY_CONFIG=str(self.path))
        patcher.start()
        self.addCleanup(patcher.stop)
        instance = server.ThreadingHTTPServer(("127.0.0.1", 0), server.ProxyConsoleHandler)
        worker = threading.Thread(target=instance.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(instance.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(instance.shutdown)
        self.web = instance
        self.addCleanup(server.stop_local_gateway)

    def request(self, path, body=None):
        connection = http.client.HTTPConnection(*self.web.server_address, timeout=8)
        try:
            payload = None if body is None else json.dumps(body)
            headers = {"Content-Type": "application/json"} if payload else {}
            connection.request("GET" if body is None else "POST", path, payload, headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_the_state_reports_a_stopped_gateway(self):
        status, body = self.request("/api/local-gateway")
        self.assertEqual(status, 200)
        self.assertFalse(body["running"])
        self.assertEqual(body["records"], [])

    def test_starting_writes_the_configuration_record(self):
        status, body = self.request("/api/local-gateway", {"action": "start"})
        self.assertEqual(status, 200)
        self.assertTrue(body["running"])
        self.assertTrue(body["address"].startswith("127.0.0.1:"))
        self.assertEqual(body["allowed_ports"], [80, 443])
        record = load_config()["gateways"][0]
        self.assertEqual(record["id"], "local-gateway")
        self.assertEqual(record["kind"], "local")
        self.assertEqual(record["host"], "127.0.0.1")
        self.assertEqual(record["port"], body["port"])

    def test_stopping_removes_the_configuration_record(self):
        self.request("/api/local-gateway", {"action": "start"})
        status, body = self.request("/api/local-gateway", {"action": "stop"})
        self.assertEqual(status, 200)
        self.assertFalse(body["running"])
        self.assertEqual(load_config()["gateways"], [])

    def test_an_unknown_action_is_refused(self):
        status, body = self.request("/api/local-gateway", {"action": "restart"})
        self.assertEqual(status, 400)
        self.assertIn("start", body["error"])

    def test_a_remote_node_cannot_bind_the_local_gateway(self):
        self.request("/api/local-gateway", {"action": "start"})
        node = {"id": "remote", "name": "remote", "host": "192.0.2.10", "port": 22,
                "access_mode": "ssh", "auth_type": "key", "ssh_user": "tester",
                "bound_gateway_id": "local-gateway"}
        status, body = self.request("/api/clients/add", node)
        self.assertEqual(status, 400)
        self.assertIn("loopback", body["error"])
        self.assertEqual(load_config()["clients"], [])

    def test_a_local_node_may_use_the_local_gateway(self):
        self.request("/api/local-gateway", {"action": "start"})
        node = {"id": "local", "name": "local", "host": "127.0.0.1", "port": 22,
                "access_mode": "local", "auth_type": "key",
                "bound_gateway_id": "local-gateway"}
        status, body = self.request("/api/clients/add", node)
        self.assertEqual(status, 200, body)
        self.assertEqual(load_config()["clients"][0]["bound_gateway_id"], "local-gateway")

    def test_the_gateway_only_listens_on_the_loopback_interface(self):
        self.request("/api/local-gateway", {"action": "start"})
        instance = server.LOCAL_GATEWAY["instance"]
        self.assertEqual(instance.server.server_address[0], "127.0.0.1")
        self.assertEqual(LocalGateway.live_count(), 1)


if __name__ == "__main__":
    unittest.main()
