"""A local observation proxy: it forwards traffic and records what it saw.

The gateway exists so that the tool can be tried on a machine that has no proxy
yet, and so that an operator can see which hosts a request went to. It listens
on the loopback interface only, reaches only the destination ports it was
allowed to reach, and keeps a short memory of the connections it handled.

    python -m web.local_gateway --port 18899 --upstream HOST:PORT --allow-port N
"""
import argparse
import re
import select
import socket
import socketserver
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DEFAULT_ALLOWED_PORTS = (80, 443)
MAX_TUNNELS = 64
MAX_HEADER_BYTES = 16 * 1024
CONNECT_TIMEOUT = 10.0
IDLE_TIMEOUT = 60.0
RECORD_LIMIT = 200
GATEWAY_ID = "local-gateway"
GATEWAY_NAME = "Local observation gateway"
HOST_PATTERN = re.compile(r"[A-Za-z0-9._:%-]{1,253}")


class _Handler(socketserver.BaseRequestHandler):
    """Hand the connection to the gateway that owns the server."""

    def handle(self):
        self.server.gateway.handle(self.request)

    def log_message(self, *args):
        pass


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class LocalGateway:
    """A loopback proxy that forwards requests and remembers the connections."""

    _live = 0
    _live_lock = threading.Lock()

    @classmethod
    def live_count(cls):
        """How many gateways are running in this process."""
        with cls._live_lock:
            return cls._live

    def __init__(self, host="127.0.0.1", port=0, upstream=None, allowed_ports=DEFAULT_ALLOWED_PORTS,
                 max_tunnels=MAX_TUNNELS, max_header_bytes=MAX_HEADER_BYTES,
                 connect_timeout=CONNECT_TIMEOUT, idle_timeout=IDLE_TIMEOUT,
                 record_limit=RECORD_LIMIT):
        self.host = host
        self.requested_port = int(port)
        self.upstream = self._parse_upstream(upstream)
        self.allowed_ports = frozenset(int(item) for item in allowed_ports)
        self.max_tunnels = int(max_tunnels)
        self.max_header_bytes = int(max_header_bytes)
        self.connect_timeout = float(connect_timeout)
        self.idle_timeout = float(idle_timeout)
        self.record_limit = int(record_limit)
        self.server = None
        self.port = None
        self.tunnels = 0
        self.records = []
        self.lock = threading.Lock()

    # -- lifecycle -------------------------------------------------------
    def start(self):
        """Bind the loopback interface and start serving. Returns the port."""
        if self.server is not None:
            return self.port
        server = _Server((self.host, self.requested_port), _Handler)
        server.gateway = self
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2},
                                  daemon=True)
        thread.start()
        self.server = server
        self.thread = thread
        self.port = server.server_address[1]
        with self._live_lock:
            type(self)._live += 1
        return self.port

    def stop(self):
        """Stop serving and close the listening socket."""
        server, self.server = self.server, None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if getattr(self, "thread", None) is not None:
            self.thread.join(timeout=5)
            self.thread = None
        self.port = None
        with self._live_lock:
            type(self)._live = max(0, type(self)._live - 1)

    @property
    def running(self):
        return self.server is not None

    # -- configuration ---------------------------------------------------
    def config_record(self):
        """The gateway as the console's configuration understands it."""
        return {"id": GATEWAY_ID, "name": GATEWAY_NAME, "host": self.host,
                "port": self.port or self.requested_port, "protocol": "http", "kind": "local",
                "description": "Built-in local observation gateway listening on loopback only."}

    def records_list(self):
        """The recent connections, newest first."""
        with self.lock:
            return list(self.records)

    # -- handling --------------------------------------------------------
    def handle(self, connection):
        """Handle one client connection. Never raises."""
        started = time.monotonic()
        record = {"method": "", "host": "", "port": 0, "outcome": "closed",
                  "bytes_to_target": 0, "bytes_to_client": 0}
        try:
            connection.settimeout(self.connect_timeout)
            head = self._read_head(connection)
            if head is None:
                record["outcome"] = "failed"
                return
            request_line, headers, remainder, raw_head = head
            parts = request_line.split(" ")
            if len(parts) != 3:
                self._reply(connection, 400, "Bad Request")
                record["outcome"] = "failed"
                return
            method, target, _version = parts
            record["method"] = method
            destination = self._destination(method, target)
            if destination is None:
                self._reply(connection, 400, "Bad Request")
                record["outcome"] = "failed"
                return
            host, port = destination
            record["host"] = host
            record["port"] = port
            if port not in self.allowed_ports:
                self._reply(connection, 403, "Forbidden")
                record["outcome"] = "forbidden"
                return
            with self.lock:
                if self.tunnels >= self.max_tunnels:
                    self._reply(connection, 503, "Service Unavailable")
                    record["outcome"] = "failed"
                    return
                self.tunnels += 1
            try:
                self._forward(connection, method, target, host, port, headers, remainder, raw_head,
                              record)
            finally:
                with self.lock:
                    self.tunnels -= 1
        except (OSError, ValueError):
            record["outcome"] = "failed"
        finally:
            try:
                connection.close()
            except OSError:
                pass
            record["seconds"] = round(time.monotonic() - started, 3)
            record["time"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            self._remember(record)

    def _forward(self, connection, method, target, host, port, headers, remainder, raw_head, record):
        upstream = None
        try:
            if self.upstream:
                upstream = socket.create_connection(self.upstream, timeout=self.connect_timeout)
            else:
                upstream = socket.create_connection((host, port), timeout=self.connect_timeout)
        except OSError:
            self._reply(connection, 502, "Bad Gateway")
            record["outcome"] = "failed"
            return
        try:
            upstream.settimeout(self.connect_timeout)
            if method.upper() == "CONNECT":
                if self.upstream:
                    # An upstream proxy performs the second hop itself, so it needs the
                    # original CONNECT request and its own answer.
                    upstream.sendall(raw_head + b"\r\n\r\n" + remainder)
                    answer = self._read_upstream_answer(upstream)
                    if answer is None:
                        self._reply(connection, 502, "Bad Gateway")
                        record["outcome"] = "failed"
                        return
                    connection.sendall(answer)
                else:
                    self._reply(connection, 200, "Connection Established")
                record["outcome"] = "established"
                sent, received = self._relay(connection, upstream, b"")
            elif self.upstream:
                upstream.sendall(raw_head + b"\r\n\r\n" + remainder)
                record["outcome"] = "established"
                sent, received = self._relay(connection, upstream, b"")
            else:
                upstream.sendall(self._origin_request(method, target, headers, remainder))
                record["outcome"] = "established"
                sent, received = self._relay(connection, upstream, b"")
            record["bytes_to_target"] = sent
            record["bytes_to_client"] = received
        except OSError:
            record["outcome"] = "failed"
        finally:
            try:
                upstream.close()
            except OSError:
                pass

    def _read_upstream_answer(self, upstream):
        """Read the answer the upstream proxy sent, bounded by the head limit."""
        data = b""
        while b"\r\n\r\n" not in data:
            try:
                chunk = upstream.recv(4096)
            except OSError:
                return None
            if not chunk:
                return None
            data += chunk
            if len(data) > self.max_header_bytes:
                return None
        return data

    def _relay(self, client, upstream, remainder):
        """Move bytes in both directions until one side stops or the idle timeout passes."""
        sent = received = 0
        last = time.monotonic()
        if remainder:
            try:
                upstream.sendall(remainder)
                sent += len(remainder)
            except OSError:
                return sent, received
        sockets = [client, upstream]
        while True:
            try:
                readable, _, _ = select.select(sockets, [], [], 0.5)
            except (OSError, ValueError):
                break
            if not readable:
                if time.monotonic() - last > self.idle_timeout:
                    break
                continue
            for source in readable:
                destination = upstream if source is client else client
                try:
                    chunk = source.recv(65536)
                except OSError:
                    chunk = b""
                if not chunk:
                    return sent, received
                last = time.monotonic()
                try:
                    destination.sendall(chunk)
                except OSError:
                    return sent, received
                if source is client:
                    sent += len(chunk)
                else:
                    received += len(chunk)
        return sent, received

    def _read_head(self, connection):
        """Return (request line, header block, trailing bytes, raw head), or None."""
        data = b""
        while b"\r\n\r\n" not in data:
            try:
                chunk = connection.recv(4096)
            except OSError:
                return None
            if not chunk:
                return None
            data += chunk
            if len(data) > self.max_header_bytes:
                self._reply(connection, 431, "Request Header Fields Too Large")
                return None
        head, _, remainder = data.partition(b"\r\n\r\n")
        lines = head.split(b"\r\n")
        if not lines or not lines[0]:
            return None
        try:
            return lines[0].decode("latin-1"), b"\r\n".join(lines[1:]), remainder, head
        except UnicodeDecodeError:
            return None

    def _destination(self, method, target):
        """Return the (host, port) of the request, or None when it is not a proxy request."""
        if method.upper() == "CONNECT":
            host, _, port = target.rpartition(":")
            if not host or not port.isdigit():
                return None
            name = self._host(host)
            return (name, int(port)) if name else None
        parts = urlsplit(target)
        if not parts.scheme or not parts.netloc:
            return None
        if parts.scheme.lower() != "http":
            return None
        try:
            port = parts.port or 80
        except ValueError:
            return None
        name = self._host(parts.hostname or "")
        return (name, port) if name else None

    @staticmethod
    def _host(name):
        """Return a usable destination host, or None when the name is not one."""
        name = (name or "").strip()
        if name.startswith("[") and name.endswith("]"):
            name = name[1:-1]
        if not name or len(name) > 253 or not HOST_PATTERN.match(name):
            return None
        return name

    @staticmethod
    def _origin_request(method, target, headers, remainder):
        """Rewrite an absolute request into the origin form and return the bytes to send."""
        parts = urlsplit(target)
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        lines = ["{} {} HTTP/1.1".format(method, path)]
        host_seen = False
        if headers:
            for line in headers.decode("latin-1").split("\r\n"):
                if not line:
                    continue
                if line.lower().startswith("host:"):
                    host_seen = True
                    lines.append("Host: " + parts.netloc)
                elif line.lower().startswith("proxy-"):
                    continue
                elif line.lower() == "connection: close":
                    continue
                else:
                    lines.append(line)
        if not host_seen:
            lines.append("Host: " + parts.netloc)
        lines.append("Connection: close")
        return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + remainder

    @staticmethod
    def _reply(connection, status, phrase):
        body = "HTTP/1.1 {} {}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".format(status, phrase)
        try:
            connection.sendall(body.encode("latin-1"))
        except OSError:
            pass

    def _remember(self, record):
        with self.lock:
            self.records.append(record)
            if len(self.records) > self.record_limit:
                del self.records[: len(self.records) - self.record_limit]

    @staticmethod
    def _parse_upstream(upstream):
        if not upstream:
            return None
        host, _, port = str(upstream).rpartition(":")
        if not host or not port.isdigit():
            raise ValueError("the upstream must be host:port")
        return (host, int(port))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the local observation proxy.")
    parser.add_argument("--port", type=int, default=18899, help="the port to listen on")
    parser.add_argument("--upstream", help="forward to this host:port instead of the origin")
    parser.add_argument("--allow-port", type=int, action="append", default=[],
                        help="allow another destination port; may be given several times")
    args = parser.parse_args(argv)
    ports = tuple(DEFAULT_ALLOWED_PORTS) + tuple(args.allow_port)
    try:
        gateway = LocalGateway(port=args.port, upstream=args.upstream, allowed_ports=ports)
    except ValueError as exc:
        print("local-gateway: {}".format(exc), file=sys.stderr)
        return 1
    try:
        port = gateway.start()
    except OSError as exc:
        print("local-gateway: cannot listen on port {}: {}".format(args.port, exc), file=sys.stderr)
        return 1
    print("local-gateway | http://{}:{}".format(gateway.host, port), flush=True)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        gateway.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
