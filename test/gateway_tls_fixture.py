"""A loopback proxy that reproduces EOF, two redirects and a final TLS handshake timeout."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import threading
from unittest.mock import patch

START = "https://first.fixture.invalid/start"
SECOND = "https://second.fixture.invalid/step"
FINAL = "https://last.fixture.invalid/final"


class Origin(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.log.append(("GET", self.headers["Host"], self.path))
        self.send_response(302)
        self.send_header("Location", {"/start": SECOND, "/step": FINAL}[self.path])
        self.send_header("Content-Length", "0")
        self.end_headers()


class Proxy(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_CONNECT(self):
        proxy = self.server
        first = not proxy.log
        proxy.log.append(("CONNECT", self.path))
        self.send_response(200)
        self.end_headers()
        self.wfile.flush()
        if first or self.path == "last.fixture.invalid:443":
            # Consume the ClientHello before sending EOF to avoid a platform-specific TCP reset.
            self.connection.settimeout(5)
            self.connection.recv(8192)
            if first:
                self.connection.shutdown(socket.SHUT_WR)
            else:
                proxy.finish.wait(10)
            return
        with proxy.tls.wrap_socket(self.connection, server_side=True) as tunnel:
            Origin(tunnel, self.client_address, proxy)


@contextmanager
def redirect_then_stall():
    with tempfile.TemporaryDirectory(prefix="gateway-tls-") as td:
        cert, key, config = [Path(td) / name for name in ("ca.pem", "key.pem", "openssl.cnf")]
        config.write_text("[req]\ndistinguished_name=dn\nprompt=no\nx509_extensions=ext\n"
                          "[dn]\nCN=first.fixture.invalid\n[ext]\nsubjectAltName=DNS:*.fixture.invalid\n"
                          "basicConstraints=critical,CA:TRUE\nkeyUsage=critical,digitalSignature,keyCertSign\n"
                          "subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid:always\n", encoding="ascii")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-config", str(config), "-keyout", str(key), "-out", str(cert)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        with ThreadingHTTPServer(("127.0.0.1", 0), Proxy) as proxy:
            proxy.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            proxy.tls.load_cert_chain(cert, key)
            proxy.log = []
            proxy.finish = threading.Event()
            worker = threading.Thread(target=proxy.serve_forever, daemon=True)
            worker.start()
            try:
                with patch.dict(os.environ, {"SSL_CERT_FILE": str(cert)}):
                    yield proxy
            finally:
                proxy.finish.set()
                proxy.shutdown()
                worker.join()


EXPECTED_LOG = [
    ("CONNECT", "first.fixture.invalid:443"), ("CONNECT", "first.fixture.invalid:443"),
    ("GET", "first.fixture.invalid", "/start"), ("CONNECT", "second.fixture.invalid:443"),
    ("GET", "second.fixture.invalid", "/step"), ("CONNECT", "last.fixture.invalid:443"),
]
