"""Regressions for the local observation gateway."""
import http.client
import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from web.local_gateway import LocalGateway


class OriginHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "9")
        self.end_headers()
        self.wfile.write(b"origin-ok")

    def log_message(self, *args):
        pass


class LocalGatewayTests(unittest.TestCase):
    def setUp(self):
        self.origin = ThreadingHTTPServer(("127.0.0.1", 0), OriginHandler)
        worker = threading.Thread(target=self.origin.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(self.origin.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(self.origin.shutdown)
        self.origin_port = self.origin.server_address[1]

        self.gateway = LocalGateway(port=0, allowed_ports=(80, 443, self.origin_port))
        self.gateway.start()
        self.addCleanup(self.gateway.stop)

    def raw(self, payload, read=4096, port=None):
        with socket.create_connection(("127.0.0.1", port or self.gateway.port), timeout=5) as connection:
            connection.sendall(payload)
            data = b""
            while len(data) < read:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                data += chunk
            return data

    def test_an_absolute_request_reaches_the_origin(self):
        request = ("GET http://127.0.0.1:{}/path?q=1 HTTP/1.1\r\nHost: 127.0.0.1:{}\r\n\r\n"
                   .format(self.origin_port, self.origin_port)).encode()
        answer = self.raw(request)
        self.assertIn(b"200", answer.split(b"\r\n", 1)[0])
        self.assertIn(b"origin-ok", answer)

    def test_a_connect_tunnel_reaches_the_origin(self):
        request = ("CONNECT 127.0.0.1:{} HTTP/1.1\r\nHost: 127.0.0.1:{}\r\n\r\n"
                   .format(self.origin_port, self.origin_port)).encode()
        with socket.create_connection(("127.0.0.1", self.gateway.port), timeout=5) as connection:
            connection.sendall(request)
            answer = connection.recv(1024)
            self.assertIn(b"200", answer.split(b"\r\n", 1)[0])
            connection.sendall(b"GET /tunneled HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
            data = b""
            while b"origin-ok" not in data and len(data) < 4096:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                data += chunk
        self.assertIn(b"origin-ok", data)

    def test_a_forbidden_port_is_refused_without_a_connection(self):
        request = ("GET http://127.0.0.1:9/ HTTP/1.1\r\nHost: 127.0.0.1:9\r\n\r\n").encode()
        answer = self.raw(request)
        self.assertIn(b"403", answer.split(b"\r\n", 1)[0])
        records = self.gateway.records_list()
        self.assertTrue(any(record["outcome"] == "forbidden" for record in records))

    def test_a_request_that_is_not_a_proxy_request_is_refused(self):
        answer = self.raw(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertIn(b"400", answer.split(b"\r\n", 1)[0])

    def test_an_oversized_head_is_refused(self):
        padding = b"X-Padding: " + b"a" * 20000 + b"\r\n"
        answer = self.raw(b"GET http://127.0.0.1/ HTTP/1.1\r\n" + padding + b"\r\n")
        self.assertIn(b"431", answer.split(b"\r\n", 1)[0])

    def test_the_records_name_the_destination_and_hold_no_body(self):
        request = ("GET http://127.0.0.1:{}/seen HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
                   .format(self.origin_port)).encode()
        self.raw(request)
        records = self.gateway.records_list()
        self.assertTrue(records)
        record = records[-1]
        self.assertEqual(record["host"], "127.0.0.1")
        self.assertEqual(record["port"], self.origin_port)
        self.assertEqual(record["method"], "GET")
        self.assertNotIn("origin-ok", str(record))
        self.assertIn("time", record)

    def test_the_configuration_record_names_the_gateway(self):
        record = self.gateway.config_record()
        self.assertEqual(record["id"], "local-gateway")
        self.assertEqual(record["kind"], "local")
        self.assertEqual(record["host"], "127.0.0.1")
        self.assertEqual(record["port"], self.gateway.port)
        self.assertEqual(record["protocol"], "http")

    def test_the_gateway_only_listens_on_the_loopback_interface(self):
        self.assertEqual(self.gateway.server.server_address[0], "127.0.0.1")

    def test_the_records_are_bounded(self):
        gateway = LocalGateway(port=0, allowed_ports=(80,), record_limit=3)
        gateway.start()
        self.addCleanup(gateway.stop)
        for _ in range(5):
            gateway._remember({"method": "GET"})
        self.assertEqual(len(gateway.records_list()), 3)

    def test_an_upstream_receives_the_original_request(self):
        received = []

        class UpstreamProxy(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", "4")
                self.end_headers()
                self.wfile.write(b"upst")

            def do_CONNECT(self):
                received.append("CONNECT " + self.path)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamProxy)
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(upstream.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(upstream.shutdown)

        gateway = LocalGateway(port=0, upstream="127.0.0.1:{}".format(upstream.server_address[1]),
                               allowed_ports=(80, 443, self.origin_port))
        gateway.start()
        self.addCleanup(gateway.stop)

        request = ("GET http://127.0.0.1:{}/chained HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
                   .format(self.origin_port)).encode()
        answer = self.raw(request, port=gateway.port)
        self.assertIn(b"200", answer.split(b"\r\n", 1)[0])
        self.assertEqual(received, ["http://127.0.0.1:{}/chained".format(self.origin_port)])

    def test_a_connect_tunnel_is_chained_through_the_upstream(self):
        received = []

        class UpstreamProxy(BaseHTTPRequestHandler):
            def do_CONNECT(self):
                received.append(self.path)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamProxy)
        worker = threading.Thread(target=upstream.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(upstream.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(upstream.shutdown)

        gateway = LocalGateway(port=0, upstream="127.0.0.1:{}".format(upstream.server_address[1]),
                               allowed_ports=(80, 443, self.origin_port))
        gateway.start()
        self.addCleanup(gateway.stop)

        request = ("CONNECT 127.0.0.1:{} HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
                   .format(self.origin_port)).encode()
        answer = self.raw(request, port=gateway.port)
        self.assertIn(b"200", answer.split(b"\r\n", 1)[0])
        self.assertEqual(received, ["127.0.0.1:{}".format(self.origin_port)])


if __name__ == "__main__":
    unittest.main()
