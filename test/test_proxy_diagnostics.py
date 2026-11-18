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


class RecordingProxy(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.hits.append(self.path)
        suffix = self.path.rsplit("/", 1)[-1]
        code, location = 200, None
        if suffix == "redirect":
            code, location = 302, "http://second.invalid/final"
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
        result = server.check_http_target("tls", "https://target.invalid/", self.url)
        self.assertEqual(result["code"], 407)
        self.assertEqual(result["error_type"], "proxy_auth")
        self.assertFalse(result["response_received"])
        self.assertTrue(result["tcp_ok"])
        self.proxy.connect_code = 200
        context = ssl.create_default_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        with patch.object(ssl, "create_default_context", return_value=context):
            with patch.object(context, "wrap_socket", side_effect=ssl.SSLCertVerificationError("untrusted")):
                result = server.check_http_target("tls", "https://target.invalid/", self.url)
        self.assertEqual(result["error_type"], "tls_certificate")
        self.assertFalse(result["http_ok"])

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
                        conn.request("POST", "/api/gateways/add", json.dumps(payload))
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
