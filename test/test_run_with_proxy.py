"""Regressions for the run_with_proxy tool."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import net_proxy_mcp
from net_proxy_mcp import McpError, ToolRegistry


class RunWithProxyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="npt-run-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.previous = os.environ.get("NET_PROXY_CONFIG")
        self.addCleanup(self.restore)
        config = self.directory / "config.json"
        config.write_text(json.dumps({
            "version": "1.4.3",
            "active_gateway_id": "gw",
            "gateways": [{"id": "gw", "name": "fixture", "host": "127.0.0.1", "port": 3128,
                          "protocol": "http", "is_default": True}],
            "clients": [],
            "no_proxy": "localhost,127.0.0.1",
        }), encoding="utf-8")
        os.environ["NET_PROXY_CONFIG"] = str(config)
        self.registry = ToolRegistry(start_directory=self.directory)

    def restore(self):
        if self.previous is None:
            os.environ.pop("NET_PROXY_CONFIG", None)
        else:
            os.environ["NET_PROXY_CONFIG"] = self.previous

    def call(self, **arguments):
        return self.registry.run_with_proxy(arguments)

    def test_the_child_receives_the_proxy_variables_and_the_parent_keeps_its_own(self):
        before = dict(os.environ)
        result = self.call(argv=[sys.executable, "-c", "import os; print(os.environ.get('HTTP_PROXY'))"])
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("http://127.0.0.1:3128", result["stdout"])
        self.assertEqual(dict(os.environ), before)
        self.assertEqual(result["proxy_url"], "http://127.0.0.1:3128")

    def test_the_argument_shape_is_refused(self):
        for argv in (None, [], "curl", [1], [""], [" "] * 65, ["ok", "\x00"]):
            with self.assertRaises(McpError) as caught:
                self.call(argv=argv)
            self.assertEqual(caught.exception.code, net_proxy_mcp.INVALID_PARAMS)

    def test_a_program_that_is_not_on_the_path_is_refused(self):
        with self.assertRaises(McpError) as caught:
            self.call(argv=["definitely-not-a-program-9f3a"])
        self.assertEqual(caught.exception.code, net_proxy_mcp.INVALID_PARAMS)

    def test_a_working_directory_outside_the_server_directory_is_refused(self):
        for cwd in ("/", str(self.directory.parent), "..", str(self.directory / ".." / ".." / "etc")):
            with self.assertRaises(McpError) as caught:
                self.call(argv=[sys.executable, "-c", "pass"], cwd=cwd)
            self.assertEqual(caught.exception.code, net_proxy_mcp.INVALID_PARAMS, cwd)

    def test_a_working_directory_inside_the_server_directory_is_accepted(self):
        inside = self.directory / "work"
        inside.mkdir()
        result = self.call(argv=[sys.executable, "-c", "print('ok')"], cwd=str(inside))
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["cwd"], str(inside))

    def test_a_timeout_stops_the_command(self):
        result = self.call(argv=[sys.executable, "-c", "import time; time.sleep(30)"], timeout=1)
        self.assertTrue(result["timed_out"])
        self.assertFalse(result["cancelled"])

    def test_a_timeout_stops_the_whole_process_tree(self):
        marker = self.directory / "grandchild.txt"
        grandchild = ("import time; time.sleep(5); open({!r}, 'w').write('x')".format(str(marker)))
        script = ("import subprocess, sys, time; "
                  "subprocess.Popen([sys.executable, '-c', {!r}]); time.sleep(30)").format(grandchild)
        result = self.call(argv=[sys.executable, "-c", script], timeout=1)
        self.assertTrue(result["timed_out"])
        time.sleep(6)
        self.assertFalse(marker.exists(), "the grandchild survived the timeout")

    def test_a_cancellation_stops_the_command(self):
        result = self.registry.run_with_proxy(
            {"argv": [sys.executable, "-c", "import time; time.sleep(30)"]}, lambda: True)
        self.assertTrue(result["cancelled"])
        self.assertFalse(result["timed_out"])

    def test_the_output_is_cut_at_the_limit(self):
        result = self.call(argv=[sys.executable, "-c", "print('x' * 5000)"], max_output_bytes=100)
        self.assertTrue(result["stdout_truncated"])
        self.assertLessEqual(len(result["stdout"]), 100)

    def test_the_audit_record_holds_no_argument(self):
        secret = "argument-value-that-must-not-be-audited"
        with patch("web.server.write_audit_log") as audit:
            self.call(argv=[sys.executable, "-c", "print('ok')", secret])
        self.assertEqual(audit.call_count, 1)
        args, kwargs = audit.call_args
        details = args[3] if len(args) > 3 else kwargs.get("details", "")
        self.assertNotIn(secret, details)
        self.assertIn("arguments=", details)
        self.assertIn("hash=", details)

    def test_no_gateway_is_refused(self):
        config = Path(os.environ["NET_PROXY_CONFIG"])
        config.write_text(json.dumps({"version": "1.4.3", "gateways": [], "clients": []}),
                          encoding="utf-8")
        with self.assertRaises(McpError) as caught:
            self.call(argv=[sys.executable, "-c", "pass"])
        self.assertEqual(caught.exception.code, net_proxy_mcp.INVALID_PARAMS)


if __name__ == "__main__":
    unittest.main()
