"""HTTP boundary regressions for console-hardening."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import http.client
import io
import json
import os
from pathlib import Path
import re
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from sdk.config import load_config
from web import server


class ConsoleHardeningTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory(prefix="npt-hardening-"))
        self.stack.enter_context(patch.dict(os.environ, NET_PROXY_CONFIG=str(Path(directory) / "config.json")))
        self.web = self.listen(server.ProxyConsoleHandler)

    def listen(self, handler):
        instance = self.stack.enter_context(server.ThreadingHTTPServer(("127.0.0.1", 0), handler))
        worker = threading.Thread(target=instance.serve_forever, daemon=True)
        worker.start()
        self.stack.callback(worker.join, 3)
        self.stack.callback(instance.shutdown)
        return instance

    def request(self, path, body=b"{}", headers=None, web=None, method="POST"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        connection = http.client.HTTPConnection(*(web or self.web).server_address, timeout=8)
        try:
            connection.request(method, path, body if method == "POST" else None, headers or {})
            response = connection.getresponse()
            raw = response.read()
            content_type = response.headers.get_content_type()
            parsed = json.loads(raw) if content_type == "application/json" else raw
            return response.status, content_type, parsed
        finally:
            connection.close()

    @staticmethod
    def json_headers(value="application/json"):
        return {"Content-Type": value}

    def test_post_requires_json_media_type_and_accepts_parameters(self):
        with patch.object(server, "check_tcp_port", return_value=(True, 1.0)) as probe:
            for headers in ({}, self.json_headers("text/plain"), self.json_headers("application/x-json")):
                status, content_type, body = self.request(
                    "/api/test-host", {"host": "127.0.0.1", "port": 22}, headers)
                self.assertEqual((status, content_type), (415, "application/json"), body)
            status, _, body = self.request(
                "/api/test-host", {"host": "127.0.0.1", "port": 22},
                self.json_headers("application/json; charset=utf-8"))
        self.assertEqual(status, 200, body)
        self.assertEqual(probe.call_count, 1)

    def test_body_limit_and_malformed_json_return_json_errors(self):
        status, content_type, body = self.request(
            "/api/test-host", b"{" + b" " * (1024 * 1024), self.json_headers())
        self.assertEqual((status, content_type), (413, "application/json"), body)
        for raw in (b"{broken", b"[]", b"\xff", b"[" * 2000 + b"]" * 2000):
            status, content_type, body = self.request("/api/test-host", raw, self.json_headers())
            self.assertEqual(status, 400, body)
            self.assertEqual(content_type, "application/json")

    def test_duplicate_content_length_is_rejected_before_transport(self):
        body = b'{"host":"127.0.0.1","port":22}'
        request = (b"POST /api/test-host HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                   b"Content-Type: application/json\r\nContent-Length: " + str(len(body)).encode("ascii") +
                   b"\r\nContent-Length: " + str(len(body)).encode("ascii") +
                   b"\r\nConnection: close\r\n\r\n" + body)
        with patch.object(server, "check_tcp_port") as probe, \
                socket.create_connection(self.web.server_address, timeout=3) as connection:
            connection.sendall(request)
            response = b""
            while True:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                response += chunk
        self.assertIn(b" 400 ", response.split(b"\r\n", 1)[0])
        probe.assert_not_called()

    def test_transfer_encoding_and_duplicate_content_type_are_rejected(self):
        body = b'{"host":"127.0.0.1","port":22}'
        base = (b"POST /api/test-host HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: " +
                str(len(body)).encode("ascii") + b"\r\nConnection: close\r\n")
        variants = (
            b"Content-Type: application/json\r\nTransfer-Encoding: chunked\r\n",
            b"Content-Type: application/json\r\nContent-Type: text/plain\r\n",
        )
        with patch.object(server, "check_tcp_port", return_value=(True, 1.0)) as probe:
            for headers in variants:
                with socket.create_connection(self.web.server_address, timeout=3) as connection:
                    connection.sendall(base + headers + b"\r\n" + body)
                    response = b""
                    while True:
                        chunk = connection.recv(4096)
                        if not chunk:
                            break
                        response += chunk
                self.assertIn(b" 400 ", response.split(b"\r\n", 1)[0])
        probe.assert_not_called()

    def test_test_host_rejects_invalid_values_without_opening_a_socket(self):
        invalid = [
            {"host": value, "port": 22} for value in (None, [], {}, "", "bad host", "a\n.example")
        ] + [
            {"host": "127.0.0.1", "port": value}
            for value in (None, True, [], {}, 0, 65536, "not-a-port")
        ]
        with patch.object(server, "check_tcp_port") as probe:
            for payload in invalid:
                status, content_type, body = self.request(
                    "/api/test-host", payload, self.json_headers())
                self.assertEqual(status, 400, (payload, body))
                self.assertEqual(content_type, "application/json")
        probe.assert_not_called()

    def test_gateway_protocol_is_normalized_before_persistence(self):
        status, _, body = self.request(
            "/api/gateways/add", {"id": "gw", "name": "gateway", "host": "127.0.0.1", "port": 3128},
            self.json_headers())
        self.assertEqual(status, 200, body)
        status, _, body = self.request(
            "/api/gateways/update", {"id": "gw", "protocol": " HTTP "}, self.json_headers())
        self.assertEqual(status, 200, body)
        self.assertEqual(load_config()["gateways"][0]["protocol"], "http")
        status, _, body = self.request(
            "/api/gateways/update", {"id": "gw", "protocol": "socks5", "port": 9999}, self.json_headers())
        self.assertEqual(status, 400, body)
        saved = load_config()["gateways"][0]
        self.assertEqual((saved["protocol"], saved["port"]), ("http", 3128))

    def test_unpaired_unicode_surrogate_is_rejected_before_persistence(self):
        with self.assertRaises(ValueError):
            server.text_field(chr(0xD800), "name")
        status, content_type, body = self.request(
            "/api/clients/add", {"name": chr(0xD800), "host": "127.0.0.1", "port": 22},
            self.json_headers())
        self.assertEqual((status, content_type), (400, "application/json"), body)
        self.assertEqual(load_config()["clients"], [])

    def test_wrong_recognized_field_type_is_a_400(self):
        status, content_type, body = self.request(
            "/api/gateways/add", {"name": ["not", "text"], "host": "127.0.0.1", "port": 3128},
            self.json_headers())
        self.assertEqual((status, content_type), (400, "application/json"), body)

    def test_unexpected_exception_returns_only_generic_error_and_id(self):
        private_detail = "private-internal-detail"

        class CrashingHandler(server.ProxyConsoleHandler):
            def handle_test_host(self):
                raise RuntimeError(private_detail)

            def log_message(self, *args):
                pass

        crashing = self.listen(CrashingHandler)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            status, content_type, body = self.request(
                "/api/test-host", {}, self.json_headers(), web=crashing)
        self.assertEqual((status, content_type), (500, "application/json"), body)
        self.assertFalse(body["success"])
        self.assertEqual(body["error"], "Internal server error")
        self.assertRegex(body["error_id"], r"^[a-f0-9]{16}$")
        self.assertNotIn(private_detail, json.dumps(body))
        log = stderr.getvalue()
        self.assertIn(body["error_id"], log)
        self.assertIn("RuntimeError", log)
        self.assertNotIn(private_detail, log)

    def test_unexpected_get_exception_uses_the_same_safe_error_policy(self):
        private_detail = "private-get-detail"

        class CrashingGetHandler(server.ProxyConsoleHandler):
            def serve_get(self):
                raise RuntimeError(private_detail)

            def log_message(self, *args):
                pass

        crashing = self.listen(CrashingGetHandler)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            status, content_type, body = self.request(
                "/api/config", headers={}, web=crashing, method="GET")
        self.assertEqual((status, content_type), (500, "application/json"), body)
        self.assertEqual(body["error"], "Internal server error")
        self.assertNotIn(private_detail, json.dumps(body) + stderr.getvalue())
        self.assertIn(body["error_id"], stderr.getvalue())

    def test_connections_receive_a_sixty_second_read_timeout(self):
        class TimeoutHandler(server.ProxyConsoleHandler):
            def handle_test_host(self):
                self.send_json({"success": True, "socket_timeout": self.connection.gettimeout()})

            def log_message(self, *args):
                pass

        timed = self.listen(TimeoutHandler)
        status, _, body = self.request("/api/test-host", {}, self.json_headers(), web=timed)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["socket_timeout"], 60)

    def test_audit_failure_warns_on_stderr_without_exception_detail(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("builtins.open", side_effect=OSError("private-audit-detail")), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            server.write_audit_log("test", details="private-request-detail")
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Audit Log Warning", stderr.getvalue())
        self.assertIn("OSError", stderr.getvalue())
        self.assertNotIn("private-audit-detail", stderr.getvalue())
        self.assertNotIn("private-request-detail", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
