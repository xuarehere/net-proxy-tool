#!/usr/bin/env python3
"""MCP server for net-proxy-tool: read-only diagnostics for coding agents.

The server speaks the Model Context Protocol over standard input and standard
output. Standard output carries protocol messages only; every log, warning and
traceback goes to standard error.

The tools report the same facts as the Web console, because they reuse the
console's own diagnostics. The server never writes the configuration, never
switches a node and never changes a gateway.

    python -X utf8 net_proxy_mcp.py --config /path/to/config.json
"""
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from sdk.config import VERSION, proxy_environment, proxy_url  # noqa: E402

PROTOCOL_VERSION = "2026-07-28"
LEGACY_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
SUPPORTED_VERSIONS = (PROTOCOL_VERSION,) + LEGACY_VERSIONS
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPABILITIES = "io.modelcontextprotocol/clientCapabilities"
META_CLIENT_INFO = "io.modelcontextprotocol/clientInfo"
META_SERVER_INFO = "io.modelcontextprotocol/serverInfo"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
UNSUPPORTED_VERSION = -32022
REQUEST_CANCELLED = -32800

DEFAULT_TARGET_URL = "https://www.google.com/"
MAX_TIMEOUT_SECONDS = 60
DEFAULT_TIMEOUT_SECONDS = 15
WORKER_COUNT = 4

MAX_ARGUMENTS = 64
MAX_ARGUMENT_LENGTH = 4096
MAX_RUN_TIMEOUT_SECONDS = 600
DEFAULT_RUN_TIMEOUT_SECONDS = 120
MAX_OUTPUT_BYTES = 256 * 1024
DEFAULT_OUTPUT_BYTES = 64 * 1024

SERVER_NAME = "net-proxy-tool"
SERVER_VERSION = VERSION
INSTRUCTIONS = (
    "This server reports the proxy state of net-proxy-tool. Use list_gateways and list_nodes for an "
    "overview, check_gateway to test one gateway, check_gateway_targets to test the configured sites, "
    "and test_node to run the console's two-path request against one node. The server is read-only: "
    "it never changes a gateway or a node."
)


class McpError(Exception):
    """A JSON-RPC error with an explicit code."""

    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = int(code)
        self.message = str(message)
        self.data = data


def request_version(params):
    """Return the protocol version a request declares, or None."""
    if not isinstance(params, dict):
        return None
    meta = params.get("_meta")
    if isinstance(meta, dict) and isinstance(meta.get(META_VERSION), str):
        return meta[META_VERSION]
    legacy = params.get("protocolVersion")
    if isinstance(legacy, str):
        return legacy
    return None


def validate_version(params, method):
    """Check the declared protocol version and the required meta fields."""
    version = request_version(params)
    if version is None:
        if method in ("initialize", "server/discover"):
            raise McpError(INVALID_PARAMS,
                           "params._meta must carry {} and {}".format(META_VERSION, META_CAPABILITIES))
        return None
    if version not in SUPPORTED_VERSIONS:
        raise McpError(UNSUPPORTED_VERSION, "Unsupported protocol version",
                       {"supported": list(SUPPORTED_VERSIONS), "requested": version})
    if version == PROTOCOL_VERSION:
        meta = params.get("_meta") if isinstance(params, dict) else None
        if not isinstance(meta, dict) or META_CAPABILITIES not in meta:
            raise McpError(INVALID_PARAMS, "params._meta must carry {}".format(META_CAPABILITIES))
    return version


def _read_capped(stream, limit, buffer):
    """Read a stream into `buffer` until the limit is reached or the stream ends."""
    while True:
        try:
            chunk = stream.read(4096)
        except (OSError, ValueError):
            break
        if not chunk:
            break
        if len(buffer) < limit:
            buffer.extend(chunk[: limit - len(buffer)])


def stop_process_tree(process):
    """Stop the child and every process it started."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=30, shell=False)
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (OSError, AttributeError):
            pass


def _run_program(argv, directory, environment, timeout, limit, cancel_check=None):
    """Run one command and collect a bounded amount of its output."""
    options = {"shell": False, "cwd": str(directory), "env": environment,
               "stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        options["start_new_session"] = True
    outcome = {"exit_code": None, "timed_out": False, "cancelled": False,
               "stdout": "", "stderr": "", "stdout_truncated": False, "stderr_truncated": False,
               "error": None}
    try:
        process = subprocess.Popen(argv, **options)
    except OSError as exc:
        outcome["error"] = type(exc).__name__
        return outcome
    out_buffer, err_buffer = bytearray(), bytearray()
    readers = [threading.Thread(target=_read_capped, args=(process.stdout, limit, out_buffer)),
               threading.Thread(target=_read_capped, args=(process.stderr, limit, err_buffer))]
    for reader in readers:
        reader.daemon = True
        reader.start()
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                process.wait(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                if cancel_check is not None and cancel_check():
                    outcome["cancelled"] = True
                elif time.monotonic() >= deadline:
                    outcome["timed_out"] = True
                else:
                    continue
                stop_process_tree(process)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
                break
    finally:
        for reader in readers:
            reader.join(timeout=5)
        for stream in (process.stdout, process.stderr):
            try:
                stream.close()
            except (OSError, ValueError):
                pass
    outcome["exit_code"] = process.returncode
    outcome["stdout_truncated"] = len(out_buffer) >= limit
    outcome["stderr_truncated"] = len(err_buffer) >= limit
    outcome["stdout"] = out_buffer.decode("utf-8", "replace")
    outcome["stderr"] = err_buffer.decode("utf-8", "replace")
    return outcome


def _contacted_hosts(observer):
    """The hosts the observation gateway saw, once each, in the order of first contact."""
    hosts = []
    for record in observer.records_list():
        if record.get("outcome") != "established":
            continue
        entry = {"host": record.get("host", ""), "port": record.get("port", 0)}
        if entry not in hosts:
            hosts.append(entry)
    return hosts


class ToolRegistry:
    """The tools the server offers, with their schemas and their answers."""

    def __init__(self, config_path=None, start_directory=None):
        self.config_path = config_path
        self.start_directory = Path(start_directory or os.getcwd()).resolve()
        self._server = None

    # -- helpers ---------------------------------------------------------
    def server(self):
        if self._server is None:
            from web import server as console
            self._server = console
        return self._server

    def configuration(self):
        server = self.server()
        with _temporary_config(self.config_path):
            return server.load_config()

    def public(self, value):
        return self.server().public_data(value)

    # -- tools -----------------------------------------------------------
    def list_gateways(self, arguments, cancel_check=None):
        cfg = self.configuration()
        gateways = []
        for gateway in cfg.get("gateways", []):
            gateways.append({
                "id": gateway.get("id"),
                "name": gateway.get("name"),
                "host": gateway.get("host"),
                "port": gateway.get("port"),
                "protocol": gateway.get("protocol", "http"),
                "description": gateway.get("description", ""),
                "is_default": bool(gateway.get("is_default")),
            })
        return {"gateways": gateways, "active_gateway_id": cfg.get("active_gateway_id", ""),
                "count": len(gateways)}

    def check_gateway(self, arguments, cancel_check=None):
        server = self.server()
        cfg = self.configuration()
        gateway = self._selected_gateway(cfg, arguments)
        target_url = arguments.get("target_url") or DEFAULT_TARGET_URL
        timeout = self._timeout(arguments.get("timeout"))
        server.diagnostic_url(target_url)
        proxy = server.gateway_url(gateway)
        result = server.check_http_target("Gateway probe", target_url, proxy, timeout=timeout)
        return self.public(dict(result, gateway_id=gateway.get("id")))

    def check_gateway_targets(self, arguments, cancel_check=None):
        from web import diagnostics
        server = self.server()
        cfg = self.configuration()
        gateway = self._selected_gateway(cfg, arguments)
        report = diagnostics.status_report(cfg, gateway.get("id"), tcp_probe=server.check_tcp_port,
                                           target_probe=server.check_http_target)
        return self.public(report)

    def list_nodes(self, arguments, cancel_check=None):
        from web import diagnostics
        cfg = self.configuration()
        summaries = [diagnostics.node_summary(cfg, node) for node in cfg.get("clients", [])]
        return {"nodes": summaries, "count": len(summaries)}

    def test_node(self, arguments, cancel_check=None):
        server = self.server()
        cfg = self.configuration()
        node_id = arguments.get("node_id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise McpError(INVALID_PARAMS, "node_id is required")
        target = next((node for node in cfg.get("clients", []) if node.get("id") == node_id), None)
        if target is None:
            raise McpError(INVALID_PARAMS, "no node is registered with the id {!r}".format(node_id))
        gateway = server.resolve_gateway_info(cfg, target.get("bound_gateway_id"))
        target_url = arguments.get("target_url") or server.DEFAULT_TEST_URL
        result = server.check_node_requests(target, gateway, target_url)
        return self.public(result)

    def run_with_proxy(self, arguments, cancel_check=None):
        """Run one command with the proxy variables of a gateway."""
        server = self.server()
        cfg = self.configuration()
        argv = self._validated_argv(arguments.get("argv"))
        gateway = self._selected_gateway(cfg, arguments)
        directory = self._working_directory(arguments.get("cwd"))
        timeout = self._bounded_number(arguments.get("timeout"), DEFAULT_RUN_TIMEOUT_SECONDS,
                                       MAX_RUN_TIMEOUT_SECONDS, "timeout")
        limit = int(self._bounded_number(arguments.get("max_output_bytes"), DEFAULT_OUTPUT_BYTES,
                                         MAX_OUTPUT_BYTES, "max_output_bytes"))
        environment = dict(os.environ)
        upstream = "{}:{}".format(gateway["host"], int(gateway["port"]))
        observer = None
        if arguments.get("inspect"):
            from web.local_gateway import LocalGateway
            observer = LocalGateway(port=0, upstream=upstream, allowed_ports=(80, 443))
            try:
                observer.start()
            except OSError as exc:
                raise McpError(INTERNAL_ERROR, "the observation gateway cannot start",
                               {"type": type(exc).__name__})
            upstream = "{}:{}".format(observer.host, observer.port)
        try:
            environment.update(proxy_environment(cfg, *upstream.rsplit(":", 1)))
            program = shutil.which(argv[0])
            if not program:
                raise McpError(INVALID_PARAMS, "{!r} is not on the search path".format(argv[0]))
            if os.name == "nt" and program.lower().endswith((".bat", ".cmd")):
                raise McpError(INVALID_PARAMS, "a .bat or .cmd program needs a command interpreter")
            digest = hashlib.sha256("\0".join(argv).encode("utf-8", "replace")).hexdigest()[:16]
            started = time.monotonic()
            outcome = _run_program([program] + list(argv[1:]), directory, environment, timeout, limit,
                                   cancel_check)
            outcome.update(program=argv[0], argument_count=len(argv), argument_hash=digest,
                           cwd=str(directory), duration_ms=round((time.monotonic() - started) * 1000),
                           gateway={"id": gateway.get("id"), "host": gateway.get("host"),
                                    "port": int(gateway.get("port") or 0)},
                           proxy_url=proxy_url(gateway["host"], int(gateway["port"])))
            if observer is not None:
                outcome["contacted_hosts"] = _contacted_hosts(observer)
                outcome["observed"] = True
        finally:
            if observer is not None:
                observer.stop()
        self._audit_run(outcome)
        return outcome

    # -- internals -------------------------------------------------------
    def _audit_run(self, outcome):
        server = self.server()
        status = "success" if outcome.get("exit_code") == 0 and not outcome.get("timed_out") else "failed"
        server.write_audit_log(
            "mcp_run_with_proxy", "-", status,
            "program={} arguments={} hash={} exit={}".format(
                outcome.get("program"), outcome.get("argument_count"),
                outcome.get("argument_hash"), outcome.get("exit_code")))

    @staticmethod
    def _validated_argv(value):
        if not isinstance(value, list) or not value or len(value) > MAX_ARGUMENTS:
            raise McpError(INVALID_PARAMS, "argv must hold between 1 and {} arguments".format(MAX_ARGUMENTS))
        for item in value:
            if not isinstance(item, str) or not item:
                raise McpError(INVALID_PARAMS, "every argument must be a non-empty string")
            if "\x00" in item or len(item) > MAX_ARGUMENT_LENGTH:
                raise McpError(INVALID_PARAMS,
                               "an argument must be at most {} characters and contain no NUL".format(
                                   MAX_ARGUMENT_LENGTH))
        return list(value)

    def _working_directory(self, value):
        if value is None:
            return self.start_directory
        if not isinstance(value, str) or not value.strip():
            raise McpError(INVALID_PARAMS, "cwd must be a path inside the server directory")
        try:
            candidate = Path(value).resolve()
        except OSError:
            raise McpError(INVALID_PARAMS, "cwd must be a path inside the server directory")
        try:
            candidate.relative_to(self.start_directory)
        except ValueError:
            raise McpError(INVALID_PARAMS,
                           "cwd must be inside {}".format(self.start_directory))
        return candidate

    @staticmethod
    def _bounded_number(value, default, maximum, name):
        if value is None:
            return default
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise McpError(INVALID_PARAMS, "{} must be a number".format(name))
        if value <= 0:
            raise McpError(INVALID_PARAMS, "{} must be greater than zero".format(name))
        return min(float(value), float(maximum))

    # -- internals -------------------------------------------------------
    def _selected_gateway(self, cfg, arguments):
        server = self.server()
        gateway_id = arguments.get("gateway_id")
        address = arguments.get("address")
        if gateway_id:
            gateway = server.resolve_gateway_info(cfg, gateway_id)
            if not gateway:
                raise McpError(INVALID_PARAMS, "no gateway is registered with the id {!r}".format(gateway_id))
            return gateway
        if address:
            if not isinstance(address, str):
                raise McpError(INVALID_PARAMS, "address must be a host:port string")
            host, _, port = address.rpartition(":")
            if not host or not port.isdigit():
                raise McpError(INVALID_PARAMS, "address must be a host:port string")
            gateway = {"id": "address", "name": address, "host": host, "port": int(port),
                       "protocol": "http"}
            server.gateway_url(gateway)
            return gateway
        gateway = server.resolve_gateway_info(cfg)
        if not gateway:
            raise McpError(INVALID_PARAMS, "no gateway is configured")
        return gateway

    @staticmethod
    def _timeout(value):
        if value is None:
            return DEFAULT_TIMEOUT_SECONDS
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise McpError(INVALID_PARAMS, "timeout must be a number of seconds")
        if value <= 0:
            raise McpError(INVALID_PARAMS, "timeout must be greater than zero")
        return min(float(value), float(MAX_TIMEOUT_SECONDS))


class _temporary_config:
    """Point the configuration lookup at another file for one block."""

    def __init__(self, path):
        self.path = path
        self.previous = None

    def __enter__(self):
        if self.path:
            self.previous = os.environ.get("NET_PROXY_CONFIG")
            os.environ["NET_PROXY_CONFIG"] = str(self.path)
        return self

    def __exit__(self, *exc_info):
        if self.path:
            if self.previous is None:
                os.environ.pop("NET_PROXY_CONFIG", None)
            else:
                os.environ["NET_PROXY_CONFIG"] = self.previous
        return False


class McpServer:
    """The message loop, the worker pool and the protocol writer."""

    def __init__(self, registry=None, stdin=None, stdout=None, workers=WORKER_COUNT):
        self.registry = registry or ToolRegistry()
        self.stdin = stdin if stdin is not None else sys.stdin
        self.protocol_stream = stdout if stdout is not None else sys.stdout
        self.write_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self.futures = {}
        self.cancelled = set()
        self.negotiated_version = None

    # -- writing ---------------------------------------------------------
    def write(self, payload):
        line = json.dumps(payload, ensure_ascii=False)
        with self.write_lock:
            self.protocol_stream.write(line + "\n")
            self.protocol_stream.flush()

    def send_result(self, request_id, result):
        self.write({"jsonrpc": "2.0", "id": request_id, "result": result})

    def send_error(self, request_id, code, message, data=None):
        error = {"code": int(code), "message": str(message)}
        if data is not None:
            error["data"] = data
        self.write({"jsonrpc": "2.0", "id": request_id, "error": error})

    # -- reading ---------------------------------------------------------
    def run(self):
        for line in self.stdin:
            self.handle_line(line)
        self.executor.shutdown(wait=True)

    def handle_line(self, line):
        text = line.strip()
        if not text:
            return
        try:
            message = json.loads(text)
        except ValueError:
            self.send_error(None, PARSE_ERROR, "Parse error")
            return
        if not isinstance(message, dict):
            self.send_error(None, INVALID_REQUEST, "Invalid Request")
            return
        method = message.get("method")
        if not isinstance(method, str) or not method:
            self.send_error(message.get("id"), INVALID_REQUEST, "Invalid Request")
            return
        params = message.get("params")
        if not isinstance(params, dict):
            params = {}
        if "id" not in message or message.get("id") is None:
            self.handle_notification(method, params)
            return
        request_id = message.get("id")
        future = self.executor.submit(self.answer, request_id, method, params)
        self.futures[request_id] = future

    def handle_notification(self, method, params):
        if method == "notifications/cancelled":
            request_id = params.get("requestId")
            if request_id is None:
                request_id = params.get("id")
            self.cancelled.add(request_id)
            future = self.futures.get(request_id)
            # A request that has not started is cancelled here, and its answer is
            # sent here too: a cancelled request still receives exactly one answer.
            if future is not None and future.cancel():
                self.send_error(request_id, REQUEST_CANCELLED, "Request cancelled")
            return
        # Every other notification is accepted and answered with nothing.

    def answer(self, request_id, method, params):
        try:
            result = self.dispatch(method, params, request_id)
        except McpError as exc:
            self.send_error(request_id, exc.code, exc.message, exc.data)
            return
        except Exception as exc:
            print("mcp: internal error: {}".format(type(exc).__name__), file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            self.send_error(request_id, INTERNAL_ERROR, "Internal error",
                            {"type": type(exc).__name__})
            return
        if request_id in self.cancelled:
            self.send_error(request_id, REQUEST_CANCELLED, "Request cancelled")
            return
        self.send_result(request_id, result)

    # -- methods ---------------------------------------------------------
    def dispatch(self, method, params, request_id=None):
        if method == "initialize":
            version = validate_version(params, method)
            self.negotiated_version = version or LEGACY_VERSIONS[0]
            return {
                "protocolVersion": self.negotiated_version,
                "capabilities": self.capabilities(),
                "serverInfo": self.server_info(),
            }
        if method == "server/discover":
            validate_version(params, method)
            return {
                "resultType": "complete",
                "supportedVersions": list(SUPPORTED_VERSIONS),
                "capabilities": self.capabilities(),
                "_meta": {META_SERVER_INFO: self.server_info()},
                "instructions": INSTRUCTIONS,
            }
        if method == "tools/list":
            return {"tools": self.tool_descriptions()}
        if method == "tools/call":
            return self.call_tool(params, self._cancelled_check(request_id))
        if method == "ping":
            return {}
        raise McpError(METHOD_NOT_FOUND, "Unknown method {!r}".format(method))

    def _cancelled_check(self, request_id):
        """A callable that tells a running tool whether its request was cancelled."""
        if request_id is None:
            return None
        return lambda: request_id in self.cancelled

    def capabilities(self):
        return {"tools": {"listChanged": False}}

    def server_info(self):
        return {"name": SERVER_NAME, "version": SERVER_VERSION}

    def tool_descriptions(self):
        return [
            {"name": "list_gateways", "description": "List the configured HTTP proxy gateways.",
             "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
             "annotations": {"readOnlyHint": True}},
            {"name": "check_gateway", "description":
                "Send one request through a gateway and report the final HTTP status.",
             "inputSchema": {"type": "object", "properties": {
                 "gateway_id": {"type": "string", "description": "A saved gateway identifier."},
                 "address": {"type": "string", "description": "A host:port address to use instead."},
                 "target_url": {"type": "string", "description": "The URL to request."},
                 "timeout": {"type": "number", "description": "Seconds, at most 60."}},
                 "additionalProperties": False},
             "annotations": {"readOnlyHint": True}},
            {"name": "check_gateway_targets", "description":
                "Probe every configured diagnostic site through one gateway.",
             "inputSchema": {"type": "object", "properties": {
                 "gateway_id": {"type": "string", "description": "A saved gateway identifier."}},
                 "additionalProperties": False},
             "annotations": {"readOnlyHint": True}},
            {"name": "list_nodes", "description":
                "List the registered nodes with their effective proxy and warnings.",
             "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
             "annotations": {"readOnlyHint": True}},
            {"name": "test_node", "description":
                "Run the console's ordinary request and explicit proxy request against one node.",
             "inputSchema": {"type": "object", "properties": {
                 "node_id": {"type": "string", "description": "A registered node identifier."},
                 "target_url": {"type": "string", "description": "The URL to request."}},
                 "required": ["node_id"], "additionalProperties": False},
             "annotations": {"readOnlyHint": True}},
            {"name": "run_with_proxy", "description":
                "Run one command with the proxy variables of a gateway, without a shell.",
             "inputSchema": {"type": "object", "properties": {
                 "argv": {"type": "array", "items": {"type": "string"},
                          "description": "The program and its arguments, one to sixty-four items."},
                 "gateway_id": {"type": "string", "description": "A saved gateway identifier."},
                 "address": {"type": "string", "description": "A host:port address to use instead."},
                 "cwd": {"type": "string", "description": "A directory inside the server directory."},
                 "timeout": {"type": "number", "description": "Seconds, at most 600."},
                 "max_output_bytes": {"type": "number", "description": "Bytes, at most 262144."},
                 "inspect": {"type": "boolean",
                             "description": "Observe the hosts the command reaches and report them."}},
                 "required": ["argv"], "additionalProperties": False},
             "annotations": {"readOnlyHint": False}},
        ]

    def call_tool(self, params, cancel_check=None):
        name = params.get("name")
        arguments = params.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}
        handler = {
            "list_gateways": self.registry.list_gateways,
            "check_gateway": self.registry.check_gateway,
            "check_gateway_targets": self.registry.check_gateway_targets,
            "list_nodes": self.registry.list_nodes,
            "test_node": self.registry.test_node,
            "run_with_proxy": self.registry.run_with_proxy,
        }.get(name)
        if handler is None:
            raise McpError(INVALID_PARAMS, "Unknown tool {!r}".format(name))
        try:
            payload = handler(arguments, cancel_check)
        except McpError:
            raise
        except Exception as exc:
            print("mcp: tool {} failed: {}".format(name, type(exc).__name__), file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {"content": [{"type": "text", "text": "{} failed: {}".format(name, type(exc).__name__)}],
                    "structuredContent": {"success": False, "error": type(exc).__name__},
                    "isError": True}
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        return {"content": [{"type": "text", "text": text}],
                "structuredContent": payload,
                "isError": False}


def redirect_stdout_to_stderr():
    """Keep the protocol stream clean: ordinary output goes to standard error."""
    sys.stdout = sys.stderr


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve net-proxy-tool diagnostics over MCP.")
    parser.add_argument("--config", help="path to the console configuration file")
    args = parser.parse_args(argv)
    redirect_stdout_to_stderr()
    server = McpServer(registry=ToolRegistry(args.config))
    try:
        server.run()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print("mcp: server stopped: {}".format(type(exc).__name__), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
