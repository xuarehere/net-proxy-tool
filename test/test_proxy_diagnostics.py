"""Hermetic HTTP proxy and safe request-entry regressions."""
import io
import http.client
import json
import os
from pathlib import Path
import ssl
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from web import server
from sdk.config import load_config
import gateway_tls_fixture


class RecordingProxy(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.hits.append(self.path)
        suffix = self.path.rsplit("/", 1)[-1]
        code, location = 200, None
        if suffix == "redirect":
            code, location = 302, getattr(self.server, "redirect_url", "http://second.invalid/final")
        elif suffix == "loop":
            code, location = 302, self.path
        elif suffix.startswith("hop"):
            code, location = 302, "/hop" + str(int(suffix[3:]) + 1)
        elif suffix in ("403", "407", "429"):
            code = int(suffix)
        elif suffix == "slow":
            time.sleep(0.15)
        self.send_response(code)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "5")
        self.end_headers()
        try:
            if self.command != "HEAD":
                self.wfile.write(b"hello")
        except (BrokenPipeError, ConnectionResetError):
            pass

    do_HEAD = do_GET

    def do_CONNECT(self):
        self.server.hits.append("CONNECT " + self.path)
        self.send_response(self.server.connect_code)
        self.end_headers()


class HandshakeProxy(RecordingProxy):
    protocol_version = "HTTP/1.1"

    def handle(self):
        try:
            super().handle()
        except ConnectionResetError:
            pass  # The probe deliberately closes a failed or redirected tunnel.

    def do_CONNECT(self):
        super().do_CONNECT()
        self.close_connection = False


class ProxyDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.proxy = ThreadingHTTPServer(("127.0.0.1", 0), RecordingProxy)
        self.proxy.hits = []
        self.proxy.connect_code = 407
        worker = threading.Thread(target=self.proxy.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(self.proxy.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(self.proxy.shutdown)
        self.url = "http://127.0.0.1:" + str(self.proxy.server_port)

    def probe(self, suffix, **kwargs):
        return server.check_http_target("test", "http://first.invalid/" + suffix, self.url, **kwargs)

    def test_redirect_always_uses_selected_proxy(self):
        with patch.dict(os.environ, {"NO_PROXY": "*", "no_proxy": "*",
                                     "HTTP_PROXY": "http://wrong.invalid:1"}):
            result = self.probe("redirect")
        self.assertEqual(result["status"], "online")
        self.assertEqual(result["final_url"], "http://second.invalid/final")
        self.assertEqual(result["redirects"][0]["code"], 302)
        self.assertEqual(self.proxy.hits, ["http://first.invalid/redirect", "http://second.invalid/final"])
        self.assertTrue(result["tcp_ok"] and result["path_verified"] and result["http_ok"])

    def test_http_response_is_distinct_from_business_success(self):
        for code in ("403", "407", "429"):
            result = self.probe(code)
            self.assertEqual(result["code"], int(code))
            self.assertTrue(result["response_received"])
            self.assertTrue(result["path_verified"])
            self.assertFalse(result["http_ok"])
            self.assertEqual(result["error_type"], "proxy_auth" if code == "407" else "http_status")

    def test_loop_limit_and_timeout(self):
        self.assertEqual(self.probe("loop")["error_type"], "redirect_loop")
        result = self.probe("hop0")
        self.assertEqual(result["error_type"], "redirect_limit")
        self.assertEqual(len(result["redirects"]), 6)
        self.assertEqual(self.probe("slow", timeout=0.03)["error_type"], "timeout")

    def test_connect_auth_and_tls_verification(self):
        for status, error in [(407, "proxy_auth"), (502, "proxy_tunnel")]:
            self.proxy.connect_code = status
            result = server.check_http_target("tls", "https://target.invalid/", self.url)
            self.assertEqual(result["code"], status)  # v1.4.2 compatibility
            self.assertEqual(result["attempts"][-1]["connect_status"], status)
            self.assertIsNone(result["first_status"])
            self.assertIsNone(result["final_status"])
            self.assertEqual(result["error_type"], error)
            self.assertFalse(result["response_received"] or result["path_verified"])
            self.assertTrue(result["tcp_ok"])
            self.assertEqual(result["tls_retries"], 0)
        self.assertEqual(len(self.proxy.hits), 2)
        self.proxy.connect_code = 200
        context = ssl.create_default_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        with patch.object(ssl, "create_default_context", return_value=context):
            with patch.object(context, "wrap_socket", side_effect=ssl.SSLCertVerificationError("untrusted")):
                result = server.check_http_target("tls", "https://target.invalid/", self.url)
        self.assertEqual(result["error_type"], "tls_certificate")
        self.assertFalse(result["http_ok"])
        self.assertEqual(result["tls_retries"], 0)
        self.assertEqual(len(self.proxy.hits), 3)

    def test_verified_tls_redirects_then_final_handshake_timeout(self):
        with gateway_tls_fixture.redirect_then_stall() as proxy:
            result = server.check_http_target("redirect", gateway_tls_fixture.START,
                                              f"http://127.0.0.1:{proxy.server_port}", timeout=2)
        self.assertEqual(proxy.log, gateway_tls_fixture.EXPECTED_LOG)
        self.assertEqual([a["tls"] for a in result["attempts"]], ["eof", "passed", "passed", "timeout"])
        self.assertEqual([a["http_status"] for a in result["attempts"]], [None, 302, 302, None])
        self.assertEqual([a["hop"] for a in result["attempts"]], [1, 1, 2, 3])
        self.assertEqual([a["connect_status"] for a in result["attempts"]], [200] * 4)
        self.assertEqual([r["location"] for r in result["redirects"]], [gateway_tls_fixture.SECOND, gateway_tls_fixture.FINAL])
        self.assertEqual(result["first_status"], 302)
        self.assertIsNone(result["final_status"])
        self.assertEqual(result["error_type"], "timeout")
        self.assertEqual(result["stage"], "tls")
        self.assertEqual(result["final_url"], gateway_tls_fixture.FINAL)
        self.assertTrue(result["budget_expired"])
        self.assertFalse(result["http_ok"] or result["response_received"])

    def test_a_peer_eof_is_retried_whatever_the_python_reports(self):
        # Python 3.8 raises SSLZeroReturnError and newer versions SSLEOFError.
        for error in (ssl.SSLEOFError("EOF"), ssl.SSLZeroReturnError("EOF")):
            with self.subTest(error=type(error).__name__):
                result, _ = self.tls_fixture([error, None], first_handshake_seconds=0)
                self.assertEqual(result["tls_retries"], 1)
                self.assertEqual(result["attempts"][0]["tls"], "eof")

    def tls_fixture(self, outcomes, suffix="final", first_handshake_seconds=5):
        """Keep CONNECT/GET real and inject only the TLS handshake outcome."""
        self.proxy.RequestHandlerClass = HandshakeProxy
        self.proxy.connect_code = 200
        self.proxy.redirect_url = "https://second.invalid/final"
        clock = [0.0]
        sockets, timeouts = [], []

        def handshake(sock, **kwargs):
            if sockets:
                self.assertEqual(sockets[-1].fileno(), -1, "previous tunnel must close before another handshake")
            sockets.append(sock)
            timeouts.append(sock.gettimeout())
            if len(sockets) == 1:
                clock[0] = first_handshake_seconds
            outcome = outcomes[len(sockets) - 1]
            if outcome is not None:
                raise outcome
            return sock

        with patch.object(server.time, "monotonic", side_effect=lambda: clock[0]):
            with patch.object(ssl, "create_default_context") as context:
                context.return_value.wrap_socket.side_effect = handshake
                result = server.check_http_target("TLS fixture", "https://target.invalid/" + suffix, self.url)
        self.assertTrue(all(sock.fileno() == -1 for sock in sockets))
        return result, timeouts

    def test_tls_eof_retry_closes_tunnel_and_shares_deadline(self):
        eof = ssl.SSLEOFError("UNEXPECTED_EOF_WHILE_READING")
        result, timeouts = self.tls_fixture([eof, None])
        self.assertTrue(result["http_ok"], result)
        self.assertEqual(result["tls_retries"], 1)
        self.assertIn("UNEXPECTED_EOF", result["tls_retry_reason"])
        self.assertEqual(timeouts, [15.0, 10.0])
        self.assertEqual(self.proxy.hits, ["CONNECT target.invalid:443", "CONNECT target.invalid:443", "/final"])

    def test_tls_eof_retry_is_once_for_the_whole_redirect_chain(self):
        eof = ssl.SSLEOFError("UNEXPECTED_EOF_WHILE_READING")
        result, timeouts = self.tls_fixture([eof, None, eof], suffix="redirect")
        self.assertEqual(result["error_type"], "tls_handshake")
        self.assertEqual(result["tls_retries"], 1)
        self.assertEqual(len(timeouts), 3)
        self.assertEqual(self.proxy.hits, ["CONNECT target.invalid:443", "CONNECT target.invalid:443",
                                          "/redirect", "CONNECT second.invalid:443"])

    def test_repeated_tls_eof_stops_after_one_retry(self):
        eof = ssl.SSLEOFError("UNEXPECTED_EOF_WHILE_READING")
        result, timeouts = self.tls_fixture([eof, eof])
        self.assertEqual(result["error_type"], "tls_handshake")
        self.assertEqual(result["tls_retries"], 1)
        self.assertEqual(len(timeouts), 2)
        self.assertEqual(self.proxy.hits, ["CONNECT target.invalid:443"] * 2)

    def test_tls_eof_cannot_restart_exhausted_budget(self):
        result, timeouts = self.tls_fixture([ssl.SSLEOFError("EOF")], first_handshake_seconds=15)
        self.assertEqual(result["error_type"], "timeout")
        self.assertEqual(result["tls_retries"], 0)
        self.assertEqual(timeouts, [15.0])
        self.assertEqual(self.proxy.hits, ["CONNECT target.invalid:443"])

    def test_invalid_input_never_connects(self):
        for url in ("file:///tmp/a", "https://user:password@example.com/", "https://example.com/\r\nX: a"):
            result = server.check_http_target("invalid", url, self.url)
            self.assertEqual(result["error_type"], "invalid_url")
        self.assertEqual(self.proxy.hits, [])

    def test_command_parser_and_no_executable_expansion(self):
        for text, method in (('curl.exe -I "https://example.com/?a=one&b=two"', "HEAD"),
                             ("curl -sS -L 'https://example.com/'", "GET"),
                             ('curl --request HEAD --url "https://example.com/"', "HEAD")):
            self.assertEqual(server.diagnostic_command({"command": text})["method"], method)
        for command in ("python -c 'print(1)'", "curl -o /tmp/a https://example.com/",
                        "curl -T file https://example.com/", "curl https://example.com/ ; whoami",
                        'curl "https://example.com/?q=$(whoami)"',
                        'curl "https://example.com/`whoami`"',
                        'curl "https://example.com/', "curl -X POST https://example.com/"):
            with self.subTest(command=command), self.assertRaises(ValueError):
                server.diagnostic_command({"command": command})

    def test_system_curl_receives_structured_quoted_request(self):
        executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/curl.exe" if os.name == "nt" else Path("/usr/bin/curl")
        if not executable.exists():
            self.skipTest("system curl unavailable")
        request = server.diagnostic_command({"command": 'curl.exe -I "http://first.invalid/a?one=1&two=2"'})
        with patch.dict(os.environ, {"NO_PROXY": "*"}):
            result = server.run_diagnostic_request(request, self.url)
        self.assertTrue(result["success"], result)
        self.assertEqual(self.proxy.hits[-1], "http://first.invalid/a?one=1&two=2")
        self.assertIn("200", result["headers"])

    def test_sse_request_has_bounded_text_fields(self):
        handler = object.__new__(server.ProxyConsoleHandler)
        handler.read_json_body = lambda: {"target_url": "http://first.invalid/final"}
        handler.send_response = lambda *args: None
        handler.send_header = lambda *args: None
        handler.end_headers = lambda: None
        handler.wfile = io.BytesIO()
        cfg = {"gateways": [{"id": "g", "name": "proxy", "host": "127.0.0.1",
                              "port": self.proxy.server_port}], "active_gateway_id": "g"}
        with patch.object(server, "load_config", return_value=cfg):
            try:
                handler.handle_api_run()
            except ValueError as exc:
                if "curl" in str(exc):
                    self.skipTest("system curl unavailable")
                raise
        events = [json.loads(line[6:]) for line in handler.wfile.getvalue().decode().splitlines()
                  if line.startswith("data: ")]
        result = next(event for event in events if event["type"] == "result")
        self.assertEqual(result["preview"], "hello")
        self.assertEqual(events[-1]["exit_code"], 0)


class GatewayIdentityTests(unittest.TestCase):
    def test_same_host_ports_retries_and_conflicting_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"NET_PROXY_CONFIG": str(Path(temp) / "config.json")}):
                web = server.ThreadingHTTPServer(("127.0.0.1", 0), server.ProxyConsoleHandler)
                worker = threading.Thread(target=web.serve_forever, daemon=True)
                worker.start()
                self.addCleanup(web.server_close)
                self.addCleanup(worker.join, 2)
                self.addCleanup(web.shutdown)

                def add(payload):
                    conn = http.client.HTTPConnection(*web.server_address, timeout=3)
                    try:
                        conn.request("POST", "/api/gateways/add", json.dumps(payload),
                                     {"Content-Type": "application/json"})
                        response = conn.getresponse()
                        return response.status, json.loads(response.read())
                    finally:
                        conn.close()

                first = {"name": "A", "host": "127.0.0.1", "port": 7890}
                second = dict(first, name="B", port=7891)
                saved_first = add(first)[1]["gateway"]["id"]
                saved_second = add(second)[1]["gateway"]["id"]
                self.assertEqual(saved_first, "gw-127-0-0-1")
                self.assertEqual(saved_second, "gw-127-0-0-1-7891")
                with ThreadPoolExecutor(max_workers=4) as pool:
                    retries = list(pool.map(add, [second] * 8))
                self.assertTrue(all(code == 200 and data["gateway"]["id"] == saved_second for code, data in retries))
                self.assertEqual(len(load_config()["gateways"]), 2)
                third = dict(first, name="another profile", port=7891)
                self.assertEqual(add(third)[1]["gateway"]["id"], saved_second + "-2")
                self.assertEqual(add(dict(first, id=saved_first))[0], 200)
                self.assertEqual(add(dict(second, id=saved_first))[0], 400)
                cfg = load_config()
                self.assertEqual(cfg["active_gateway_id"], saved_first)
                self.assertEqual(len({g["id"] for g in cfg["gateways"]}), 3)
