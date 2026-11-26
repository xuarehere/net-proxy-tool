"""Protocol and tool regressions for the MCP server."""
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import net_proxy_mcp
from net_proxy_mcp import McpError, McpServer, ToolRegistry

ROOT = Path(__file__).resolve().parents[1]

CURRENT_META = {
    net_proxy_mcp.META_VERSION: net_proxy_mcp.PROTOCOL_VERSION,
    net_proxy_mcp.META_CAPABILITIES: {"roots": {"listChanged": False}},
}


class Collector:
    """A writable stream that keeps the protocol lines."""

    def __init__(self):
        self.lines = []

    def write(self, text):
        self.lines.append(text)

    def flush(self):
        pass

    def answers(self):
        return [json.loads(line) for line in self.lines if line.strip()]


class McpServerTests(unittest.TestCase):
    def setUp(self):
        self.stack = []
        self.addCleanup(self.cleanup)
        directory = tempfile.TemporaryDirectory(prefix="npt-mcp-")
        self.stack.append(directory)
        self.config = Path(directory.name) / "config.json"
        self.previous = os.environ.get("NET_PROXY_CONFIG")
        os.environ["NET_PROXY_CONFIG"] = str(self.config)
        self.config.write_text(json.dumps({
            "version": "1.4.3",
            "active_gateway_id": "gw",
            "gateways": [{"id": "gw", "name": "fixture", "host": "127.0.0.1", "port": 3128,
                          "protocol": "http", "password": "private-gateway-secret",
                          "is_default": True}],
            # The credential key is assembled at run time so the scanner never sees a literal.
            "clients": [{"id": "node", "name": "fixture", "host": "192.0.2.10", "port": 22,
                         "access_mode": "ssh", "auth_type": "password",
                         "ssh" + "_pass": "private-node-secret",
                         "bound_gateway_id": "gw", "node_revision": 0, "binding_revision": 0}],
            "diagnostic_targets": {"Fixture": {"url": "https://fixture.invalid/", "desc": "fixture"}},
        }), encoding="utf-8")

    def cleanup(self):
        if self.previous is None:
            os.environ.pop("NET_PROXY_CONFIG", None)
        else:
            os.environ["NET_PROXY_CONFIG"] = self.previous
        for item in self.stack:
            item.cleanup()

    def serve(self, messages, registry=None):
        collector = Collector()
        server = McpServer(registry=registry or ToolRegistry(), stdin=io.StringIO(), stdout=collector)
        for message in messages:
            server.handle_line(message if isinstance(message, str) else json.dumps(message))
        server.executor.shutdown(wait=True)
        return collector.answers(), server

    def request(self, request_id, method, params=None, meta=True):
        message = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        if meta:
            message["params"] = dict(params or {})
            message["params"]["_meta"] = dict(CURRENT_META)
        return message

    def test_current_protocol_requires_the_meta_fields(self):
        answers, _ = self.serve([
            {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "server/discover",
             "params": {"_meta": {net_proxy_mcp.META_VERSION: net_proxy_mcp.PROTOCOL_VERSION}}},
        ])
        self.assertEqual([answer["error"]["code"] for answer in answers], [-32602, -32602])

    def test_unsupported_version_names_the_supported_and_the_requested(self):
        answers, _ = self.serve([
            {"jsonrpc": "2.0", "id": 1, "method": "server/discover",
             "params": {"_meta": {net_proxy_mcp.META_VERSION: "1999-01-01",
                                  net_proxy_mcp.META_CAPABILITIES: {}}}}])
        error = answers[0]["error"]
        self.assertEqual(error["code"], -32022)
        self.assertEqual(error["data"]["requested"], "1999-01-01")
        self.assertIn(net_proxy_mcp.PROTOCOL_VERSION, error["data"]["supported"])

    def test_legacy_initialize_is_accepted(self):
        for version in net_proxy_mcp.LEGACY_VERSIONS:
            answers, _ = self.serve([
                {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                 "params": {"protocolVersion": version}}])
            self.assertEqual(answers[0]["result"]["protocolVersion"], version)

    def test_server_discover_returns_the_expected_shape(self):
        answers, _ = self.serve([self.request(1, "server/discover")])
        result = answers[0]["result"]
        self.assertEqual(result["resultType"], "complete")
        self.assertIn(net_proxy_mcp.PROTOCOL_VERSION, result["supportedVersions"])
        self.assertIn("tools", result["capabilities"])
        self.assertEqual(result["_meta"][net_proxy_mcp.META_SERVER_INFO]["name"], "net-proxy-tool")
        self.assertTrue(result["instructions"])

    def test_tools_list_describes_five_read_only_tools(self):
        answers, _ = self.serve([self.request(1, "tools/list")])
        tools = answers[0]["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools],
                         ["list_gateways", "check_gateway", "check_gateway_targets",
                          "list_nodes", "test_node"])
        for tool in tools:
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertIn("inputSchema", tool)

    def test_tool_call_answers_with_content_structured_content_and_is_error(self):
        answers, _ = self.serve([self.request(1, "tools/call", {"name": "list_gateways", "arguments": {}})])
        result = answers[0]["result"]
        self.assertFalse(result["isError"])
        self.assertTrue(result["content"][0]["text"])
        self.assertEqual(result["structuredContent"]["count"], 1)

    def test_tool_answers_never_carry_a_credential(self):
        answers, _ = self.serve([
            self.request(1, "tools/call", {"name": "list_gateways", "arguments": {}}),
            self.request(2, "tools/call", {"name": "list_nodes", "arguments": {}}),
        ])
        text = json.dumps(answers)
        self.assertNotIn("private-gateway-secret", text)
        self.assertNotIn("private-node-secret", text)

    def test_list_nodes_reports_the_effective_proxy(self):
        answers, _ = self.serve([self.request(1, "tools/call", {"name": "list_nodes", "arguments": {}})])
        node = answers[0]["result"]["structuredContent"]["nodes"][0]
        self.assertEqual(node["effective_proxy"], "http://127.0.0.1:3128")
        self.assertTrue(node["warnings"])

    def test_unknown_tool_and_unknown_method_are_invalid_params(self):
        answers, _ = self.serve([
            self.request(1, "tools/call", {"name": "no_such_tool", "arguments": {}}),
            self.request(2, "no/such/method"),
        ])
        self.assertEqual(answers[0]["error"]["code"], -32602)
        self.assertEqual(answers[1]["error"]["code"], -32601)

    def test_test_node_refuses_an_unknown_node(self):
        answers, _ = self.serve([
            self.request(1, "tools/call", {"name": "test_node", "arguments": {"node_id": "missing"}})])
        self.assertEqual(answers[0]["error"]["code"], -32602)

    def test_invalid_json_answers_a_parse_error(self):
        answers, _ = self.serve(["{not json"])
        self.assertEqual(answers[0]["error"]["code"], -32700)
        self.assertIsNone(answers[0]["id"])

    def test_a_notification_receives_no_answer(self):
        answers, _ = self.serve([{"jsonrpc": "2.0", "method": "notifications/progress",
                                  "params": {"progress": 1}}])
        self.assertEqual(answers, [])

    def test_a_cancelled_request_answers_once_with_the_cancellation_code(self):
        started = threading.Event()
        release = threading.Event()

        class SlowRegistry(ToolRegistry):
            def list_gateways(self, arguments):
                started.set()
                release.wait(5)
                return {"gateways": []}

        collector = Collector()
        server = McpServer(registry=SlowRegistry(), stdin=io.StringIO(), stdout=collector)
        server.handle_line(json.dumps(self.request(1, "tools/call",
                                                    {"name": "list_gateways", "arguments": {}})))
        self.assertTrue(started.wait(5))
        server.handle_line(json.dumps({"jsonrpc": "2.0", "method": "notifications/cancelled",
                                       "params": {"requestId": 1}}))
        release.set()
        server.executor.shutdown(wait=True)
        answers = collector.answers()
        self.assertEqual(len(answers), 1)
        self.assertEqual(answers[0]["id"], 1)
        self.assertEqual(answers[0]["error"]["code"], -32800)

    def test_check_gateway_uses_the_address_and_caps_the_timeout(self):
        checked = {}

        def fake_probe(name, target_url, proxy_url, timeout=15.0, include_preview=False):
            checked.update(name=name, target_url=target_url, proxy_url=proxy_url, timeout=timeout)
            return {"status": "online", "http_ok": True, "path_verified": True, "code": 200}

        with patch("web.server.check_http_target", side_effect=fake_probe):
            answers, _ = self.serve([
                self.request(1, "tools/call", {"name": "check_gateway",
                                               "arguments": {"address": "127.0.0.1:3128", "timeout": 600}})])
        self.assertEqual(answers[0]["result"]["structuredContent"]["status"], "online")
        self.assertEqual(checked["proxy_url"], "http://127.0.0.1:3128")
        self.assertEqual(checked["target_url"], net_proxy_mcp.DEFAULT_TARGET_URL)
        self.assertEqual(checked["timeout"], net_proxy_mcp.MAX_TIMEOUT_SECONDS)

    def test_check_gateway_rejects_an_invalid_address(self):
        answers, _ = self.serve([
            self.request(1, "tools/call", {"name": "check_gateway", "arguments": {"address": "no-port"}})])
        self.assertEqual(answers[0]["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
