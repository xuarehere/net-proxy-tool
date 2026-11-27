"""Property P8 for the MCP server (spec: mcp-server, Requirements 2 and 6).

P8: the protocol stream is well formed. Every answer is a JSON-RPC object, every
request message is answered exactly once with its own identifier, and a message
without an identifier is never answered.
"""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from prop_support import example, given, st

import net_proxy_mcp
from net_proxy_mcp import McpServer, ToolRegistry

ROOT = Path(__file__).resolve().parents[1]

CURRENT_META = {
    net_proxy_mcp.META_VERSION: net_proxy_mcp.PROTOCOL_VERSION,
    net_proxy_mcp.META_CAPABILITIES: {},
}
METHODS = ("ping", "tools/list", "initialize", "server/discover")
NOTIFICATIONS = ("notifications/progress", "notifications/cancelled", "notifications/other")


class Collector:
    def __init__(self):
        self.lines = []

    def write(self, text):
        self.lines.append(text)

    def flush(self):
        pass


@st.composite
def message_sequence(draw):
    """A sequence of JSON-RPC messages; identifiers may repeat."""
    count = draw(st.integers(min_value=0, max_value=6))
    messages = []
    for index in range(count):
        kind = draw(st.sampled_from(["request", "notification"]))
        if kind == "request":
            messages.append({
                "jsonrpc": "2.0",
                "id": draw(st.integers(min_value=1, max_value=max(1, count))),
                "method": draw(st.sampled_from(METHODS)),
                "params": {"_meta": dict(CURRENT_META)},
            })
        else:
            params = {}
            if draw(st.booleans()) and count:
                params["requestId"] = draw(st.integers(min_value=1, max_value=count))
            messages.append({"jsonrpc": "2.0", "method": draw(st.sampled_from(NOTIFICATIONS)),
                             "params": params})
    return messages


class McpProtocolProperties(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="npt-mcp-prop-")
        self.addCleanup(temporary.cleanup)
        self.previous = os.environ.get("NET_PROXY_CONFIG")
        os.environ["NET_PROXY_CONFIG"] = str(Path(temporary.name) / "config.json")
        self.addCleanup(self.restore)

    def restore(self):
        if self.previous is None:
            os.environ.pop("NET_PROXY_CONFIG", None)
        else:
            os.environ["NET_PROXY_CONFIG"] = self.previous

    @example(messages=[
        {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {"_meta": dict(CURRENT_META)}},
        {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {"_meta": dict(CURRENT_META)}},
        {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}},
        {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}},
    ])
    @given(messages=message_sequence())
    def test_p8_every_request_is_answered_once_and_notifications_are_not(self, messages):
        collector = Collector()
        server = McpServer(registry=ToolRegistry(), stdin=io.StringIO(), stdout=collector)
        for message in messages:
            server.handle_line(json.dumps(message))
        server.executor.shutdown(wait=True)

        for line in collector.lines:
            if not line.strip():
                continue
            answer = json.loads(line)
            self.assertEqual(answer["jsonrpc"], "2.0")
            self.assertIn("id", answer)
            self.assertTrue("result" in answer or "error" in answer)
            self.assertNotEqual("result" in answer and "error" in answer, True)

        expected = sorted(message["id"] for message in messages if "id" in message)
        answered = sorted(json.loads(line)["id"] for line in collector.lines if line.strip())
        self.assertEqual(answered, expected)

    def test_duplicate_cancel_notifications_do_not_double_answer_queued_requests(self):
        import threading

        started = threading.Event()
        release = threading.Event()

        class BlockingRegistry(ToolRegistry):
            def list_gateways(self, arguments, cancel_check=None):
                started.set()
                release.wait(timeout=5)
                return {"ok": True}

        collector = Collector()
        server = McpServer(registry=BlockingRegistry(), stdin=io.StringIO(), stdout=collector, workers=1)
        server.handle_line(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "list_gateways", "arguments": {}},
        }))
        self.assertTrue(started.wait(timeout=2))
        server.handle_line(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}))
        server.handle_line(json.dumps({
            "jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1},
        }))
        server.handle_line(json.dumps({
            "jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1},
        }))
        release.set()
        server.executor.shutdown(wait=True)

        answered = [json.loads(line)["id"] for line in collector.lines if line.strip()]
        self.assertEqual(answered, [1, 1])


if __name__ == "__main__":
    unittest.main()
