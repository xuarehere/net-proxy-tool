"""Properties P1-P6 for console-hardening (Requirements 1, 3, 4 and 7)."""
from contextlib import ExitStack
import http.client
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import threading
import unittest
import urllib.parse
from unittest.mock import patch

from prop_support import example, given, st
from sdk.config import NO_PROXY, atomic_json, load_config, proxy_environment, save_config
from web import server


JSON_SCALAR = st.one_of(
    st.none(), st.booleans(), st.integers(min_value=-10 ** 9, max_value=10 ** 9),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=40),
)
JSON_VALUE = st.recursive(
    JSON_SCALAR,
    lambda children: st.one_of(st.lists(children, max_size=4),
                               st.dictionaries(st.text(max_size=20), children, max_size=4)),
    max_leaves=12,
)
HOSTS = st.one_of(
    st.from_regex(r"[a-z](?:[a-z0-9-]{0,20}[a-z0-9])?(?:\.[a-z][a-z0-9-]{0,12}){0,2}", fullmatch=True),
    st.ip_addresses(v=4).map(str),
    st.ip_addresses(v=6).map(str),
)
SENSITIVE = ("ssh_pass", "password", "token", "api_key", "private_key",
             "_node_baseline", "_node_restored_baseline")


@st.composite
def sensitive_key(draw):
    source = draw(st.sampled_from(SENSITIVE))
    flips = draw(st.lists(st.booleans(), min_size=len(source), max_size=len(source)))
    return "".join(char.upper() if flip else char.lower() for char, flip in zip(source, flips))


def sensitive_keys(value):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in SENSITIVE:
                found.append(key)
            found.extend(sensitive_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(sensitive_keys(child))
    return found


class ConsolePureProperties(unittest.TestCase):
    @given(host=HOSTS, port=st.integers(min_value=1, max_value=65535),
           bypass=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789.,*:/%[]-", max_size=80))
    def test_p1_proxy_url_round_trip(self, host, port, bypass):
        environment = proxy_environment({"no_proxy": bypass}, host, port)
        proxy_values = {environment[key] for key in
                        ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")}
        self.assertEqual(len(proxy_values), 1)
        url = proxy_values.pop()
        parsed = urllib.parse.urlsplit(url)
        self.assertEqual((parsed.hostname, parsed.port), (host, port))
        self.assertEqual((environment["no_proxy"], environment["NO_PROXY"]), (bypass, bypass))
        self.assertEqual(server.gateway_url({"host": host, "port": port, "protocol": "HTTP"}), url)
        if ":" in host:
            self.assertEqual((url.count("["), url.count("]")), (1, 1))

    @given(value=JSON_VALUE)
    @example(value=None)
    @example(value={})
    def test_p2_validators_return_legal_values_or_value_error(self, value):
        calls = [
            lambda: server.text_field(value, "field", maximum=255),
            lambda: server.integer_field(value, "field", 0, 65535),
            lambda: server.boolean_field(value, "field"),
            lambda: server.normalize_protocol(value),
            lambda: server.validate_host_port(value, value),
            lambda: server.validate_bypass(value),
            lambda: server.diagnostic_url(value),
            lambda: server.diagnostic_command(value),
            lambda: server.gateway_url(value),
            lambda: server.validate_api_payload("/api/test-host", {"host": value, "port": value}),
            lambda: server.validate_client(value),
        ]
        for call in calls:
            try:
                result = call()
            except ValueError:
                continue
            except Exception as exc:
                self.fail("validator raised {} for {!r}".format(type(exc).__name__, value))
            self.assertIsNotNone(result)

    @given(path=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789/_-", max_size=40),
           query=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789=&_-", max_size=40))
    def test_p3_url_and_curl_forms_round_trip(self, path, query):
        url = "https://example.com/" + path
        if query:
            url += "?" + query
        direct = server.diagnostic_command({"target_url": url})
        curl = server.diagnostic_command({"command": "curl --url " + shlex.quote(url)})
        self.assertEqual(direct, curl)
        self.assertEqual(direct["method"], "GET")

    @given(marker=st.sampled_from(["$(", "`", "\n", "\r"]), suffix=st.text(max_size=30))
    @example(marker="\n", suffix="")
    def test_p3_shell_interpolation_and_newlines_are_rejected(self, marker, suffix):
        with self.assertRaises(ValueError):
            server.diagnostic_command({"command": "curl https://example.com/" + marker + suffix})

    @given(tree=JSON_VALUE, key=sensitive_key(), depth=st.integers(min_value=0, max_value=8))
    def test_p4_sensitive_keys_are_removed_at_every_depth(self, tree, key, depth):
        value = {"kept": tree, key: "private-sentinel"}
        for index in range(depth):
            value = {"level{}".format(index): [value], "sibling": index}
        cleaned = server.public_data(value)
        self.assertEqual(sensitive_keys(cleaned), [])
        self.assertNotIn("private-sentinel", repr(cleaned))

    @given(extension=JSON_VALUE)
    def test_p5_configuration_extensions_round_trip(self, extension):
        with tempfile.TemporaryDirectory(prefix="npt-prop-config-") as directory:
            path = Path(directory) / "config.json"
            with patch.dict(os.environ, NET_PROXY_CONFIG=str(path)):
                config = load_config()
                config["generated_extension"] = extension
                save_config(config)
                self.assertEqual(load_config()["generated_extension"], extension)

    def test_p5_failed_replace_preserves_original_bytes(self):
        with tempfile.TemporaryDirectory(prefix="npt-prop-atomic-") as directory:
            path = Path(directory) / "config.json"
            original = b'{"kept": true}\n'
            path.write_bytes(original)
            with patch("sdk.config.os.replace", side_effect=OSError("fixture replacement failure")):
                with self.assertRaises(OSError):
                    atomic_json(path, {"replacement": True})
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob(".net-proxy-*")), [])


POST_ENDPOINTS = (
    "/api/config", "/api/shutdown", "/api/set-active-gateway", "/api/test-gateway",
    "/api/test-host", "/api/test-node-preflight", "/api/clients/add", "/api/clients/update",
    "/api/clients/delete", "/api/node-switch", "/api/nodes/batch-switch",
    "/api/nodes/health-check-all", "/api/node-test", "/api/gateways/add",
    "/api/gateways/update", "/api/gateways/delete", "/api/run",
)
RECOGNIZED_FIELDS = tuple(server._STRING_FIELD_LIMITS) + tuple(server._INTEGER_FIELD_RANGES) + (
    "confirm_execution_mode", "tags", "nodes", "unknown_extension",
)
POST_PAYLOADS = st.dictionaries(st.sampled_from(RECOGNIZED_FIELDS), JSON_VALUE, max_size=8)


class GeneratedPostProperties(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory(prefix="npt-prop-http-"))
        self.stack.enter_context(patch.dict(os.environ, NET_PROXY_CONFIG=str(Path(directory) / "config.json")))
        self.stack.enter_context(patch.object(server, "check_tcp_port", return_value=(False, "fixture offline")))
        self.stack.enter_context(patch.object(server, "check_http_target", return_value={
            "status": "offline", "http_ok": False, "path_verified": False, "error": "fixture offline"}))
        self.stack.enter_context(patch.object(server, "run_diagnostic_request", return_value={
            "success": False, "error": "fixture offline", "headers": "", "preview": ""}))
        self.stack.enter_context(patch.object(server, "check_node_requests", return_value={
            "success": False, "online": False, "error": "fixture offline"}))
        self.stack.enter_context(patch.object(server, "apply_node_proxy", return_value={
            "returncode": 1, "managed_state": "unknown", "error": "fixture offline",
            "verification": {"verified": False, "status": "unknown"}}))
        completed = subprocess.CompletedProcess([], 1, "", "fixture offline")
        self.stack.enter_context(patch.object(server, "run_remote_ssh_script", return_value=completed))
        self.stack.enter_context(patch.object(server, "run_node_script", return_value=completed))
        self.stack.enter_context(patch.object(server.node_baseline, "capture_node_baseline", return_value={
            "ok": False, "execution_identity": {}, "managed": {"state": "unknown"}}))

        class QuietHandler(server.ProxyConsoleHandler):
            def log_message(self, *args):
                pass

        self.web = self.stack.enter_context(server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler))
        worker = threading.Thread(target=self.web.serve_forever, daemon=True)
        worker.start()
        self.stack.callback(worker.join, 3)
        self.stack.callback(self.web.shutdown)

    def reset_config(self):
        config = load_config()
        config.update(
            gateways=[{"id": "gw", "name": "fixture", "host": "127.0.0.1", "port": 3128,
                       "protocol": "http", "is_default": True}],
            active_gateway_id="gw",
            clients=[{"id": "node", "name": "fixture", "host": "localhost", "port": 22,
                      "access_mode": "local", "auth_type": "key", "bound_gateway_id": "gw",
                      "node_revision": 0, "binding_revision": 0, "identity_version": 1,
                      "lifecycle_version": 1, "is_proxy_enabled": False, "managed_state": "unknown"}],
            archived_clients=[], no_proxy=NO_PROXY, diagnostic_targets={},
        )
        save_config(config)

    def request(self, endpoint, payload):
        connection = http.client.HTTPConnection(*self.web.server_address, timeout=5)
        try:
            connection.request("POST", endpoint, json.dumps(payload), {"Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, response.headers.get_content_type(), response.read()
        finally:
            connection.close()

    @given(payload=POST_PAYLOADS)
    @example(payload={"host": "127.0.0.1", "port": 22})
    @example(payload={"id": "gw", "name": "fixture", "host": "127.0.0.1", "port": 3128,
                      "protocol": " HTTP ", "description": ""})
    @example(payload={"name": chr(0xD800), "host": "127.0.0.1", "port": 3128})
    @example(payload={"id": "node", "name": "fixture", "host": "localhost", "port": 22,
                      "access_mode": "local", "auth_type": "key", "bound_gateway_id": "gw",
                      "node_revision": 0, "binding_revision": 0, "confirm_execution_mode": True,
                      "tags": [], "description": ""})
    @example(payload={"node_id": "node", "node_revision": 0, "binding_revision": 0,
                      "gateway_id": "gw", "action": "off"})
    @example(payload={"action": "off", "nodes": [{"node_id": "node", "node_revision": 0,
                                                     "binding_revision": 0, "gateway_id": "gw"}]})
    @example(payload={"target_url": "http://example.invalid/", "gateway_id": "gw"})
    @example(payload={"no_proxy": "localhost,127.0.0.1"})
    @example(payload={"command": "curl https://example.invalid/", "gateway_id": "gw"})
    def test_p6_generated_post_bodies_do_not_cause_input_shape_500s(self, payload):
        self.reset_config()
        for endpoint in POST_ENDPOINTS:
            status, content_type, raw = self.request(endpoint, payload)
            self.assertNotEqual(status, 500, (endpoint, payload, raw[:500]))
            if content_type == "application/json":
                response = json.loads(raw)
                self.assertEqual(sensitive_keys(response), [])
            else:
                self.assertEqual(content_type, "text/event-stream")
                events = [json.loads(line[6:]) for line in raw.decode("utf-8").splitlines()
                          if line.startswith("data: ")]
                self.assertTrue(events)
                self.assertTrue(all(not sensitive_keys(event) for event in events))


if __name__ == "__main__":
    unittest.main()
