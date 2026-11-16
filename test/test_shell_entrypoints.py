"""Exercise the installed Bash wrappers in a disposable shell and home directory."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "requires POSIX Bash")
class ShellEntrypointTests(unittest.TestCase):
    def test_installed_switches_restore_export_attributes(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="proxy home ") as home:
            env = dict(os.environ, HOME=home, NET_PROXY_GATEWAY="127.0.0.1:9876",
                       NET_PROXY_CONFIG=str(Path(home) / "config.json"))
            script = r"""
set -eu
bash "$1/install-cli.sh"
export PATH="$HOME/.local/bin:$PATH"
unset http_proxy HTTP_PROXY https_proxy
http_proxy="shell value"
export HTTP_PROXY="prior 'quoted' value"
before=$(declare -p http_proxy HTTP_PROXY)
source proxy-on
[[ $http_proxy == http://127.0.0.1:9876 ]]
source proxy-on
source proxy-off
source proxy-off
[[ $(declare -p http_proxy HTTP_PROXY) == "$before" ]]
[[ -z ${https_proxy+x} ]]
"""
            result = subprocess.run(["bash", "-c", script, "test", str(root)], cwd=home,
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
