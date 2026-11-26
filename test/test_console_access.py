"""Access token, Host gate and audit regressions for console-access."""
from contextlib import ExitStack, redirect_stderr
import http.client
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from sdk.config import data_dir, load_config
from web import server


class AccessControlTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory(prefix="npt-access-"))
        self.config = Path(directory) / "config.json"
        self.stack.enter_context(patch.dict(os.environ, NET_PROXY_CONFIG=str(self.config)))
        self.stack.enter_context(patch.dict(server.ACCESS, token="", required=False, printed=True))

    def handler(self, address=("198.51.100.7", 51234), headers=None, path="/api/config"):
        """Build a handler stub that answers one request without a socket."""
        instance = object.__new__(server.ProxyConsoleHandler)
        instance.client_address = address
        instance.headers = headers or {}
        instance.path = path
        instance.requestline = "GET " + path + " HTTP/1.1"
        instance.close_connection = False
        instance.sent = []
        instance.wfile = io.BytesIO()
        instance.send_response = lambda code, *args: instance.sent.append(("status", code))
        instance.send_header = lambda key, value: instance.sent.append((key, value))
        instance.end_headers = lambda: None
        return instance

    def cookie_headers(self, token):
        return {"Cookie": "npt_access=" + token}

    def test_loopback_clients_never_need_a_token(self):
        with patch.dict(server.ACCESS, token="secret-token", required=True):
            for address in (("127.0.0.1", 5000), ("127.0.0.53", 5000), ("::1", 5000, 0, 0),
                            ("::ffff:127.0.0.1", 5000)):
                instance = self.handler(address=address)
                self.assertTrue(instance.authorize_access(), address)
                self.assertEqual(instance.sent, [])

    def test_non_loopback_client_without_a_token_is_refused(self):
        with patch.dict(server.ACCESS, token="secret-token", required=True):
            instance = self.handler()
            self.assertFalse(instance.authorize_access())
            self.assertIn(("status", 401), instance.sent)
            self.assertNotIn(b"secret-token", instance.wfile.getvalue())

    def test_correct_query_token_sets_a_strict_cookie_and_redirects(self):
        with patch.dict(server.ACCESS, token="secret-token", required=True):
            instance = self.handler(path="/?token=secret-token")
            self.assertFalse(instance.authorize_access())
            self.assertIn(("status", 302), instance.sent)
            self.assertIn(("Location", "/"), instance.sent)
            cookies = [value for key, value in instance.sent if key == "Set-Cookie"]
            self.assertEqual(len(cookies), 1)
            self.assertIn("npt_access=secret-token", cookies[0])
            self.assertIn("HttpOnly", cookies[0])
            self.assertIn("SameSite=Strict", cookies[0])
            self.assertIn("Path=/", cookies[0])

    def test_wrong_query_token_is_refused_without_a_cookie(self):
        with patch.dict(server.ACCESS, token="secret-token", required=True):
            instance = self.handler(path="/?token=wrong-token")
            self.assertFalse(instance.authorize_access())
            self.assertIn(("status", 401), instance.sent)
            self.assertEqual([value for key, value in instance.sent if key == "Set-Cookie"], [])

    def test_correct_cookie_is_accepted(self):
        with patch.dict(server.ACCESS, token="secret-token", required=True):
            instance = self.handler(headers=self.cookie_headers("secret-token"))
            self.assertTrue(instance.authorize_access())
            self.assertEqual(instance.sent, [])

    def test_a_valid_cookie_wins_over_a_wrong_query_token(self):
        with patch.dict(server.ACCESS, token="secret-token", required=True):
            instance = self.handler(headers=self.cookie_headers("secret-token"), path="/?token=wrong")
            self.assertTrue(instance.authorize_access())
            self.assertEqual(instance.sent, [])

    def test_token_never_reaches_the_request_log(self):
        with patch.dict(server.ACCESS, token="secret-token", required=True):
            instance = self.handler(path="/?token=secret-token")
            instance.log_message = lambda *args: instance.sent.append(("log", args[0] % args[1:]))
            instance.log_request(302)
        logged = "".join(value for key, value in instance.sent if key == "log")
        self.assertNotIn("secret-token", logged)
        self.assertIn("redacted", logged)


class HostGateTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory(prefix="npt-host-"))
        self.stack.enter_context(patch.dict(os.environ, NET_PROXY_CONFIG=str(Path(directory) / "config.json")))

    def test_local_names_are_known_without_a_dns_lookup(self):
        with patch("socket.getaddrinfo", side_effect=AssertionError("unexpected DNS lookup")):
            names = server.console_host_names()
        self.assertIn("localhost", names)
        self.assertIn("127.0.0.1", names)
        self.assertIn("::1", names)
        self.assertIn(socket.gethostname().lower(), names)

    def test_strict_host_list_is_kept_without_access_control(self):
        with patch.dict(server.ACCESS, required=False):
            allowed = server.allowed_host_names()
        self.assertEqual(allowed, {"localhost", "127.0.0.1", "::1"})

    def test_host_list_is_extended_only_with_access_control(self):
        with patch.dict(server.ACCESS, required=True):
            allowed = server.allowed_host_names()
        self.assertIn(socket.gethostname().lower(), allowed)
        self.assertIn("localhost", allowed)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory(prefix="npt-audit-"))
        self.config = Path(directory) / "config.json"
        self.stack.enter_context(patch.dict(os.environ, NET_PROXY_CONFIG=str(self.config)))

    def test_record_carries_an_iso_timestamp_and_the_client_address(self):
        server.write_audit_log("client_add", "node-1", "success", "节点登记已保存", operator_ip="203.0.113.9")
        records = server.get_audit_logs(5)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["client_address"], "203.0.113.9")
        self.assertEqual(record["operator_ip"], "203.0.113.9")
        self.assertRegex(record["timestamp"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        self.assertNotIn("secret", json.dumps(record).lower() or "")

    def test_audit_log_rotates_and_keeps_three_generations(self):
        path = server.audit_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        for index in range(4):
            path.write_bytes(b"x" * (5 * 1024 * 1024))
            server.write_audit_log("rotation", "node", "info", "generation {}".format(index))
        self.assertTrue(path.exists())
        self.assertLessEqual(path.stat().st_size, 5 * 1024 * 1024 + 4096)
        self.assertTrue((path.parent / "audit.log.1").exists())
        self.assertTrue((path.parent / "audit.log.2").exists())
        self.assertTrue((path.parent / "audit.log.3").exists())
        self.assertFalse((path.parent / "audit.log.4").exists())


class PublishedConsoleTests(unittest.TestCase):
    """End-to-end checks over a real socket on a non-loopback address."""

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory(prefix="npt-published-"))
        self.stack.enter_context(patch.dict(os.environ, NET_PROXY_CONFIG=str(Path(directory) / "config.json")))
        self.address = server.access_link_host("0.0.0.0")
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                probe.connect(("192.0.2.1", 9))
                candidate = probe.getsockname()[0]
            finally:
                probe.close()
        except OSError as exc:
            self.skipTest("no non-loopback address available: {}".format(exc))
        if server.is_loopback_client(candidate):
            self.skipTest("no non-loopback address available")
        self.address = candidate

    def listen(self, bind=None):
        instance = self.stack.enter_context(server.ThreadingHTTPServer((bind or self.address, 0),
                                                                      server.ProxyConsoleHandler))
        worker = threading.Thread(target=instance.serve_forever, daemon=True)
        worker.start()
        self.stack.callback(worker.join, 3)
        self.stack.callback(instance.shutdown)
        return instance

    def request(self, web, path="/api/health", headers=None):
        connection = http.client.HTTPConnection(self.address, web.server_port, timeout=6)
        try:
            connection.request("GET", path, None, headers or {"Host": "{}:{}".format(
                self.address, web.server_port)})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_published_console_refuses_a_client_without_the_token(self):
        web = self.listen()
        with patch.dict(server.ACCESS, token="secret-token", required=True, printed=True):
            status, headers, body = self.request(web)
            self.assertEqual(status, 401)
            self.assertNotIn(b"secret-token", body)
            self.assertNotIn("Set-Cookie", headers)

    def test_published_console_issues_a_cookie_for_the_access_link(self):
        web = self.listen()
        with patch.dict(server.ACCESS, token="secret-token", required=True, printed=True):
            status, headers, body = self.request(web, path="/?token=secret-token")
            self.assertEqual(status, 302)
            self.assertEqual(headers.get("Location"), "/")
            cookie = headers.get("Set-Cookie", "")
            self.assertIn("npt_access=secret-token", cookie)
            self.assertIn("HttpOnly", cookie)
            self.assertIn("SameSite=Strict", cookie)
            self.assertNotIn(b"secret-token", body)
            status, _, _ = self.request(web, headers={"Host": "{}:{}".format(self.address, web.server_port),
                                                      "Cookie": "npt_access=secret-token"})
            self.assertEqual(status, 200)

    def test_loopback_client_is_not_asked_for_a_token(self):
        web = self.listen(bind="0.0.0.0")
        with patch.dict(server.ACCESS, token="secret-token", required=True, printed=True):
            connection = http.client.HTTPConnection("127.0.0.1", web.server_port, timeout=6)
            try:
                connection.request("GET", "/api/health", None, {"Host": "127.0.0.1:{}".format(web.server_port)})
                self.assertEqual(connection.getresponse().status, 200)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
