"""Shared diagnostics and release consistency regressions."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "kiro"))

from sdk.config import NO_PROXY, VERSION, proxy_url  # noqa: E402
from web import diagnostics  # noqa: E402
import check_release_consistency  # noqa: E402


def config(**overrides):
    base = {
        "version": "1.5.0",
        "active_gateway_id": "gw",
        "gateways": [{"id": "gw", "name": "fixture", "host": "127.0.0.1", "port": 3128,
                      "protocol": "http", "is_default": True}],
        "clients": [],
        "diagnostic_targets": {
            "First": {"url": "https://first.invalid/", "desc": "first"},
            "Second": {"url": "https://second.invalid/", "desc": "second"},
        },
    }
    base.update(overrides)
    return base


def fake_target_probe(name, info, proxy):
    return {"name": name, "url": info.get("url", ""), "proxy_url": proxy,
            "http_ok": True, "path_verified": True, "code": 200, "status": "online"}


class StatusReportTests(unittest.TestCase):
    def test_report_without_a_gateway_has_no_targets(self):
        report = diagnostics.status_report(config(gateways=[], active_gateway_id=""),
                                           tcp_probe=lambda host, port: (True, 1.0))
        self.assertIsNone(report["gateway"])
        self.assertEqual(report["targets"], [])
        self.assertTrue(report["timestamp"])

    def test_unreachable_gateway_is_reported_without_probing(self):
        probed = []

        def probe(name, info, proxy):
            probed.append(name)
            return fake_target_probe(name, info, proxy)

        report = diagnostics.status_report(config(), tcp_probe=lambda host, port: (False, "refused"),
                                           target_probe=probe)
        self.assertFalse(report["gateway"]["tcp_ok"])
        self.assertEqual(report["gateway"]["error"], "refused")
        self.assertEqual(report["targets"], [])
        self.assertEqual(probed, [])

    def test_reachable_gateway_probes_every_target_in_order(self):
        report = diagnostics.status_report(config(), tcp_probe=lambda host, port: (True, 2.5),
                                           target_probe=fake_target_probe)
        self.assertEqual([item["name"] for item in report["targets"]], ["First", "Second"])
        self.assertTrue(report["gateway"]["online"])
        self.assertTrue(report["gateway"]["path_verified"])
        self.assertEqual(report["gateway"]["latency_ms"], 2.5)
        self.assertEqual(report["targets"][0]["proxy_url"], "http://127.0.0.1:3128")

    def test_gateway_with_an_unusable_protocol_names_the_reason(self):
        broken = config(gateways=[{"id": "gw", "name": "fixture", "host": "127.0.0.1",
                                   "port": 3128, "protocol": "socks5"}])
        report = diagnostics.status_report(broken, tcp_probe=lambda host, port: (True, 1.0),
                                           target_probe=fake_target_probe)
        self.assertFalse(report["gateway"]["tcp_ok"])
        self.assertIn("HTTP", report["gateway"]["error"])
        self.assertEqual(report["targets"], [])


class NodeSummaryTests(unittest.TestCase):
    def test_summary_reports_the_effective_proxy(self):
        node = {"id": "node", "name": "fixture", "host": "192.0.2.10", "port": 22,
                "access_mode": "ssh", "auth_type": "key", "bound_gateway_id": "gw",
                "is_proxy_enabled": True, "managed_state": "enabled",
                "verification": {"verified": True, "status": "enabled"}}
        summary = diagnostics.node_summary(config(), node)
        self.assertEqual(summary["effective_proxy"], "http://127.0.0.1:3128")
        self.assertEqual(summary["gateway"]["id"], "gw")
        self.assertTrue(summary["is_proxy_enabled"])
        self.assertNotIn("ssh_pass", json.dumps(summary))

    def test_remote_node_on_a_loopback_gateway_is_warned(self):
        node = {"id": "node", "host": "192.0.2.10", "access_mode": "ssh", "bound_gateway_id": "gw"}
        summary = diagnostics.node_summary(config(), node)
        self.assertTrue(any("回环" in warning for warning in summary["warnings"]))

    def test_local_node_on_a_loopback_gateway_is_not_warned(self):
        node = {"id": "node", "host": "127.0.0.1", "access_mode": "local", "bound_gateway_id": "gw"}
        summary = diagnostics.node_summary(config(), node)
        self.assertEqual(summary["warnings"], [])

    def test_node_without_a_binding_is_warned(self):
        summary = diagnostics.node_summary(config(), {"id": "node", "host": "192.0.2.10",
                                                       "access_mode": "ssh"})
        self.assertIsNone(summary["effective_proxy"])
        self.assertTrue(any("绑定" in warning for warning in summary["warnings"]))

    def test_node_with_a_removed_gateway_is_warned(self):
        summary = diagnostics.node_summary(config(), {"id": "node", "host": "192.0.2.10",
                                                       "access_mode": "ssh", "bound_gateway_id": "gone"})
        self.assertTrue(any("已不存在" in warning for warning in summary["warnings"]))


class ProxyUrlTests(unittest.TestCase):
    def test_ipv6_hosts_are_bracketed_once(self):
        self.assertEqual(proxy_url("::1", 3128), "http://[::1]:3128")
        self.assertEqual(proxy_url("127.0.0.1", 3128), "http://127.0.0.1:3128")


class ReleaseConsistencyTests(unittest.TestCase):
    def build(self, directory, version="1.5.0", example_version="1.5.0", changelog="1.5.0"):
        root = Path(directory)
        (root / "sdk").mkdir(parents=True, exist_ok=True)
        (root / "sdk" / "config.py").write_text('VERSION = "{}"\n'.format(version), encoding="utf-8")
        (root / "pyproject.toml").write_text('[project]\nversion = "{}"\n'.format(version), encoding="utf-8")
        (root / "config.example.json").write_text(
            '{{"version": "{}", "no_proxy": "{}"}}\n'.format(example_version, NO_PROXY), encoding="utf-8")
        (root / "README.md").write_text(
            "下载 v{}\nhttps://example.invalid/releases/download/v{}/file.zip\n".format(version, version),
            encoding="utf-8")
        (root / "README.zh-CN.md").write_text(
            "下载 v{}\nhttps://example.invalid/releases/download/v{}/file.zip\n".format(version, version),
            encoding="utf-8")
        (root / "CHANGELOG.md").write_text("## [{}]\n\n- change\n".format(changelog), encoding="utf-8")
        return root

    def test_consistent_versions_report_no_mismatch(self):
        with tempfile.TemporaryDirectory(prefix="npt-release-") as directory:
            root = self.build(directory)
            found, mismatches = check_release_consistency.collect(root)
        self.assertEqual(mismatches, [])
        self.assertEqual(found["sdk/config.py"], "1.5.0")
        self.assertEqual(found["README.md"], ["1.5.0"])

    def test_a_stale_example_version_is_reported(self):
        with tempfile.TemporaryDirectory(prefix="npt-release-") as directory:
            root = self.build(directory, example_version="1.4.2")
            _, mismatches = check_release_consistency.collect(root)
        self.assertIn(("config.example.json", "1.4.2", "1.5.0"), mismatches)

    def test_a_stale_readme_link_is_reported(self):
        with tempfile.TemporaryDirectory(prefix="npt-release-") as directory:
            root = self.build(directory)
            (root / "README.zh-CN.md").write_text(
                "Download v1.4.3\nhttps://example.invalid/releases/download/v1.4.3/file.zip\n",
                encoding="utf-8")
            _, mismatches = check_release_consistency.collect(root)
        self.assertTrue(any(name == "README.zh-CN.md" for name, _, _ in mismatches))

    def test_a_different_example_bypass_list_is_reported(self):
        with tempfile.TemporaryDirectory(prefix="npt-release-") as directory:
            root = self.build(directory)
            (root / "config.example.json").write_text(
                '{"version": "1.5.0", "no_proxy": "localhost"}\n', encoding="utf-8")
            _, mismatches = check_release_consistency.collect(root)
        self.assertTrue(any(name.endswith("no_proxy") for name, _, _ in mismatches))

    def test_the_repository_state_is_reported_honestly(self):
        found, mismatches = check_release_consistency.collect(ROOT)
        self.assertEqual(found["sdk/config.py"], VERSION)
        self.assertEqual(mismatches, [], "the released state must agree everywhere")
        self.assertIn("README.md", found)
        self.assertIn("README.zh-CN.md", found)


if __name__ == "__main__":
    unittest.main()
