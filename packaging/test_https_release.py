"""Prove HTTPS redirects and CLI/SDK egress with a fixed, loopback-only TLS fixture."""
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from smoke import api


class Origin(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.seen.append(self.path)
        if self.path == "/start":
            self.send_response(302)
            self.send_header("Location", "/ok")
        elif self.path == "/ok":
            self.send_response(200)
        else:
            self.send_error(404)
            return
        self.end_headers()
        self.wfile.write(b"portable-tls-origin")

    def log_message(self, *args):
        pass


class FixtureProxy(BaseHTTPRequestHandler):
    def do_CONNECT(self):
        if self.path != "release-check.invalid:443":
            self.send_error(403)
            return
        self.send_response(200)
        self.end_headers()
        with self.server.tls.wrap_socket(self.connection, server_side=True) as stream:
            Origin(stream, self.client_address, self.server)
        self.close_connection = True

    def log_message(self, *args):
        pass


def run(root):
    root = root.resolve()
    windows = os.name == "nt"
    runtime = root / ("runtime/python.exe" if windows else "runtime/bin/python3")
    launcher = str(root / ("Start.bat" if windows else "net-proxy-tool"))
    with tempfile.TemporaryDirectory(prefix="https-release-") as temp:
        directory = Path(temp)
        cert, key, conf = (directory / name for name in ("cert.pem", "key.pem", "openssl.cnf"))
        conf.write_text("[req]\ndistinguished_name=dn\nprompt=no\nx509_extensions=ext\n"
                        "[dn]\nCN=release-check.invalid\n[ext]\nsubjectAltName=DNS:release-check.invalid\n"
                        "basicConstraints=critical,CA:TRUE\nkeyUsage=critical,digitalSignature,keyCertSign\n"
                        "subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid:always\n", encoding="ascii")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                        "-config", str(conf), "-keyout", str(key), "-out", str(cert)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        env = dict(os.environ, NET_PROXY_CONFIG=str(directory / "config.json"),
                   SSL_CERT_FILE=str(cert), PYTHONUTF8="1")
        with socket.socket() as free:
            free.bind(("127.0.0.1", 0))
            port = free.getsockname()[1]
        with ThreadingHTTPServer(("127.0.0.1", 0), FixtureProxy) as proxy:
            proxy.seen = []
            proxy.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            proxy.tls.load_cert_chain(cert, key)
            thread = threading.Thread(target=proxy.serve_forever, daemon=True)
            thread.start()
            try:
                subprocess.run([launcher, str(port), "--no-browser"], env=env, cwd=directory,
                               check=True, timeout=30)
                gateway = dict(name="TLS fixture", protocol="http", host="127.0.0.1", port=proxy.server_port)
                api(port, "/api/gateways/add", gateway)
                target = "https://release-check.invalid/start"
                result = api(port, "/api/test-gateway", dict(gateway, target_url=target))
                assert result.get("success") and result["code"] == 200, result
                assert proxy.seen == ["/start", "/ok"], proxy.seen
                request = ("import urllib.request; "
                           f"assert urllib.request.urlopen({target!r}, timeout=8).read()==b'portable-tls-origin'")
                cli = [str(runtime), str(root / "with_proxy.py"), str(runtime), "-c", request]
                # Resolve the SDK from the extracted archive even when invoked outside its directory.
                sdk = [str(runtime), "-c", f"import sys; sys.path.insert(0,{str(root)!r}); "
                       "from sdk import ProxySession\nwith ProxySession():\n " + request]
                for cmd in (cli, sdk):
                    proxy.seen.clear()
                    subprocess.run(cmd, cwd=directory, env=env, check=True, timeout=25)
                    assert proxy.seen == ["/start", "/ok"], proxy.seen
            finally:
                if (directory / "data/instance.json").exists():
                    subprocess.run([launcher, "--stop"], env=env, cwd=directory, check=True, timeout=30)
                proxy.shutdown()
                thread.join()
    print("Extracted Web, CLI and SDK each completed the TLS redirect via the selected gateway.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    run(parser.parse_args().root)
