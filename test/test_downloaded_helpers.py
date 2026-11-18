"""Run the downloadable shell helpers with pre-existing proxy settings."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from web import server


def download(path):
    received = []
    cfg = {"active_gateway_id": "test", "gateways": [{"id": "test", "host": "proxy.test", "port": 3128}]}
    with patch.object(server, "load_config", return_value=cfg):
        server.ProxyConsoleHandler.serve_get(SimpleNamespace(path=path, send_text=received.append))
    return received[0]


@unittest.skipUnless(os.name == "posix", "requires a POSIX shell")
class DownloadedHelperTests(unittest.TestCase):
    def test_session_restores_original_exported_unexported_and_missing_values(self):
        for shell in set(filter(None, [shutil.which("sh"), shutil.which("bash")])):
            script = ("set -eu\nunset no_proxy; HTTP_PROXY='before test'; export HTTP_PROXY; "
                      "unset http_proxy; http_proxy='local value'; export NO_PROXY=''\n"
                      + download("/proxy-on") + download("/proxy-on")
                      + 'test "$HTTP_PROXY" = http://proxy.test:3128\n'
                      + download("/proxy-off") + download("/proxy-off")
                      + """test "$HTTP_PROXY" = 'before test'
test "$http_proxy" = 'local value'
! printenv http_proxy
test "${no_proxy+x}" != x
test "$(printenv NO_PROXY)" = ''
test "$(printenv HTTP_PROXY)" = 'before test'
""")
            with self.subTest(shell=shell):
                subprocess.run([shell, "-c", script], check=True)

    def test_installer_preserves_collisions_and_edited_helpers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            init = download("/container-init.sh").replace("/etc/net-proxy-tool-console-helpers", str(root / "state"))
            profile, wrapper = root / "profile", root / "wrapper"
            init = init.replace("/etc/profile.d/net-proxy-switch.sh", str(profile)).replace("/usr/local/bin/with-proxy", str(wrapper))
            def run(*args):
                return subprocess.run(["sh", "-s", "--", *args], input=init, text=True, capture_output=True)
            profile.write_text("pre-existing\n")
            self.assertNotEqual(run().returncode, 0)
            self.assertEqual(profile.read_text(), "pre-existing\n")
            self.assertFalse(wrapper.exists())
            profile.unlink()
            self.assertEqual(run().returncode, 0)
            installed = wrapper.read_bytes()
            wrapper.write_text("operator edit")
            self.assertNotEqual(run("--uninstall").returncode, 0)
            self.assertEqual(wrapper.read_text(), "operator edit")
            wrapper.write_bytes(installed)
            self.assertEqual(run("--uninstall").returncode, 0)
            self.assertEqual(list(root.iterdir()), [])
