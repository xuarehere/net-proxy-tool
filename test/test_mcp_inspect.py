"""Regressions for the inspect mode of run_with_proxy."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from net_proxy_mcp import ToolRegistry
from web.local_gateway import LocalGateway


class RecordingProxy(BaseHTTPRequestHandler):
    """A proxy that answers every absolute request and remembers what it saw."""

    def do_GET(self):
        self.server.seen.append(self.path)
        self.send_response(200)
        self.send_header("Content-Length", "6")
        self.end_headers()
        self.wfile.write(b"proxied")

    def do_CONNECT(self):
        self.server.seen.append("CONNECT " + self.path)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


class InspectModeTests(unittest.TestCase):
    def setUp(self):
        self.proxy = ThreadingHTTPServer(("127.0.0.1", 0), RecordingProxy)
        self.proxy.seen = []
        worker = threading.Thread(target=self.proxy.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(self.proxy.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(self.proxy.shutdown)

        temporary = tempfile.TemporaryDirectory(prefix="npt-inspect-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.previous = os.environ.get("NET_PROXY_CONFIG")
        self.addCleanup(self.restore)
        config = self.directory / "config.json"
        config.write_text(json.dumps({
            "version": "1.4.3",
            "active_gateway_id": "gw",
            "gateways": [{"id": "gw", "name": "recording", "host": "127.0.0.1",
                          "port": self.proxy.server_address[1], "protocol": "http",
                          "is_default": True}],
            "clients": [],
            "no_proxy": "localhost,127.0.0.1",
        }), encoding="utf-8")
        os.environ["NET_PROXY_CONFIG"] = str(config)
        self.registry = ToolRegistry(start_directory=self.directory)

    def restore(self):
        if self.previous is None:
            os.environ.pop("NET_PROXY_CONFIG", None)
        else:
            os.environ["NET_PROXY_CONFIG"] = self.previous

    def test_the_command_still_leaves_through_the_selected_gateway(self):
        result = self.registry.run_with_proxy({
            "argv": [sys.executable, "-c",
                     "import urllib.request; print(urllib.request.urlopen('http://example.invalid/probe').read().decode())"],
            "inspect": True,
        })
        self.assertEqual(result["exit_code"], 0, result["stderr"])
        self.assertTrue(self.proxy.seen, "the selected gateway saw no request")
        self.assertIn("example.invalid", self.proxy.seen[0])

    def test_the_contacted_hosts_are_reported(self):
        result = self.registry.run_with_proxy({
            "argv": [sys.executable, "-c",
                     "import urllib.request; urllib.request.urlopen('http://example.invalid/probe')"],
            "inspect": True,
        })
        hosts = result["contacted_hosts"]
        self.assertEqual([entry["host"] for entry in hosts], ["example.invalid"])
        self.assertEqual([entry["port"] for entry in hosts], [80])
        self.assertNotIn("probe", json.dumps(hosts))

    def test_no_observation_gateway_survives_the_call(self):
        before = LocalGateway.live_count()
        self.registry.run_with_proxy({
            "argv": [sys.executable, "-c", "print('ok')"],
            "inspect": True,
        })
        self.assertEqual(LocalGateway.live_count(), before)

    def test_without_inspect_no_gateway_is_started(self):
        result = self.registry.run_with_proxy({
            "argv": [sys.executable, "-c", "print('ok')"],
        })
        self.assertNotIn("contacted_hosts", result)
        self.assertNotIn("observed", result)


if __name__ == "__main__":
    unittest.main()
