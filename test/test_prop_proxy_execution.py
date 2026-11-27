"""Property P9 for run_with_proxy (spec: proxy-execution, Requirement 2).

P9: the proxy variables of the selected gateway reach the child process in both
cases, and the environment of the server process is the same before and after.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from prop_support import given, st

from net_proxy_mcp import ToolRegistry

PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
SCRIPT = ("import json, os; print(json.dumps({key: os.environ.get(key) for key in "
          + repr(list(PROXY_KEYS) + ["NO_PROXY", "no_proxy"]) + "}))")
HOSTS = st.sampled_from(["127.0.0.1", "localhost", "proxy.invalid", "::1"])
BYPASS = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789.,*", min_size=1, max_size=40)


class ProxyExecutionProperties(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="npt-prop-run-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.previous = os.environ.get("NET_PROXY_CONFIG")
        self.addCleanup(self.restore)

    def restore(self):
        if self.previous is None:
            os.environ.pop("NET_PROXY_CONFIG", None)
        else:
            os.environ["NET_PROXY_CONFIG"] = self.previous

    @given(host=HOSTS, port=st.integers(min_value=1, max_value=65535), bypass=BYPASS)
    def test_p9_the_proxy_reaches_the_child_and_only_the_child(self, host, port, bypass):
        config = self.directory / "config.json"
        config.write_text(json.dumps({
            "version": "1.4.3",
            "active_gateway_id": "gw",
            "gateways": [{"id": "gw", "name": "fixture", "host": host, "port": port,
                          "protocol": "http", "is_default": True}],
            "clients": [],
            "no_proxy": bypass,
        }), encoding="utf-8")
        os.environ["NET_PROXY_CONFIG"] = str(config)
        registry = ToolRegistry(start_directory=self.directory)

        before = dict(os.environ)
        result = registry.run_with_proxy({"argv": [sys.executable, "-c", SCRIPT]})
        after = dict(os.environ)

        self.assertEqual(result["exit_code"], 0, result["stderr"])
        observed = json.loads(result["stdout"].strip())
        address = "[{}]".format(host) if ":" in host else host
        expected = "http://{}:{}".format(address, port)
        for key in PROXY_KEYS:
            self.assertEqual(observed[key], expected, key)
        self.assertEqual(observed["NO_PROXY"], bypass)
        self.assertEqual(observed["no_proxy"], bypass)
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
