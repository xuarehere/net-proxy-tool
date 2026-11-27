"""Regressions for the node pool fixes."""
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from web import server

ROOT = Path(__file__).resolve().parents[1]


class HostAddressTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="npt-addresses-")
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

    def get(self, path):
        connection = http.client.HTTPConnection(*self.web.server_address, timeout=6)
        try:
            connection.request("GET", path, None, {"Host": "127.0.0.1:{}".format(self.web.server_port)})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_the_console_reports_its_own_addresses(self):
        status, body = self.get("/api/host-addresses")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(body["count"], 1)
        addresses = body["addresses"]
        self.assertTrue(any(entry.get("address") == "127.0.0.1" for entry in addresses))
        loopback = [entry for entry in addresses if entry.get("address") == "127.0.0.1"]
        self.assertTrue(loopback[0]["loopback"])
        self.assertNotIn("ssh_pass", json.dumps(body))

    def test_the_loopback_classification_matches_the_server(self):
        for name in ("127.0.0.1", "127.0.0.53", "::1", "::ffff:127.0.0.1"):
            self.assertTrue(server.is_loopback_client(name), name)
        for name in ("192.0.2.10", "203.0.113.7", "example.invalid", ""):
            self.assertFalse(server.is_loopback_client(name), name)


class FrontEndFixTests(unittest.TestCase):
    """The front end has no unit harness; these checks keep the fixes present."""

    def read(self, name):
        return (ROOT / "web" / "static" / name).read_text(encoding="utf-8")

    def test_each_node_keeps_its_own_probe_result(self):
        script = self.read("app.js")
        self.assertNotIn("activeNodeProbe", script)
        self.assertIn("nodeProbeSequences", script)
        self.assertIn("nodeProbeResults", script)

    def test_the_action_menu_is_positioned_against_the_viewport(self):
        style = self.read("style.css")
        block = style.split(".action-dropdown-menu {", 1)[1].split("}", 1)[0]
        self.assertIn("position: fixed", block)
        script = self.read("app.js")
        self.assertIn("function positionDropdownMenu", script)

    def test_the_dim_text_reaches_the_contrast_ratio(self):
        style = self.read("style.css")
        dark = style.split(":root {", 1)[1].split("}", 1)[0]
        value = dark.split("--text-dim:", 1)[1].split(";", 1)[0].strip()
        ratio = _contrast_ratio(value, "#131b2e")
        self.assertGreaterEqual(ratio, 4.5, "{} on #131b2e is {:.2f}:1".format(value, ratio))


def _channel(value):
    part = value / 255
    return part / 12.92 if part <= 0.03928 else ((part + 0.055) / 1.055) ** 2.4


def _luminance(colour):
    red, green, blue = (int(colour[index:index + 2], 16) for index in (1, 3, 5))
    return (0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue))


def _contrast_ratio(foreground, background):
    first, second = _luminance(foreground), _luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


if __name__ == "__main__":
    unittest.main()
