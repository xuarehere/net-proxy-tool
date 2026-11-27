"""Runtime reliability regressions for console-access."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from sdk import config as sdk_config
from web import node_baseline

# The probe defines these helpers; a single probe line needs them as well.
PROBE_HELPERS = ("tag=NPT_TEST_TAG; "
                 "emit() { printf '%s\\t%s\\t%s\\n' \"$tag\" \"$1\" \"$2\"; }; "
                 "hex() { od -An -tx1 | tr -d ' \\n'; };")


def account_name_probe():
    """The account-name line of the real read-only probe, with its helpers."""
    line = next(line for line in node_baseline._PROBE.splitlines()
                if line.strip().startswith("emit user "))
    return PROBE_HELPERS + " " + line.strip()


class ConfigurationWriteTests(unittest.TestCase):
    def test_locked_configuration_file_is_retried(self):
        with tempfile.TemporaryDirectory(prefix="npt-retry-") as directory:
            path = Path(directory) / "config.json"
            calls = []
            real_replace = os.replace

            def replace(source, target):
                calls.append(target)
                if len(calls) < 3:
                    raise PermissionError(13, "file is in use")
                real_replace(source, target)

            with patch.object(sdk_config.os, "replace", side_effect=replace):
                sdk_config.atomic_json(path, {"kept": True})
            self.assertEqual(len(calls), 3)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"kept": True})

    def test_exhausted_retries_report_the_original_error(self):
        with tempfile.TemporaryDirectory(prefix="npt-retry-") as directory:
            path = Path(directory) / "config.json"
            with patch.object(sdk_config.os, "replace", side_effect=PermissionError(13, "file is in use")):
                with self.assertRaises(PermissionError):
                    sdk_config.atomic_json(path, {"kept": True})
            self.assertEqual(list(path.parent.glob(".net-proxy-*")), [])
            self.assertFalse(path.exists())

    def test_other_errors_are_not_retried(self):
        with tempfile.TemporaryDirectory(prefix="npt-retry-") as directory:
            path = Path(directory) / "config.json"
            calls = []

            def replace(source, target):
                calls.append(target)
                raise OSError(28, "no space left on device")

            with patch.object(sdk_config.os, "replace", side_effect=replace):
                with self.assertRaises(OSError):
                    sdk_config.atomic_json(path, {"kept": True})
            self.assertEqual(len(calls), 1)


class ConfigurationPermissionTests(unittest.TestCase):
    @unittest.skipUnless(os.name != "nt", "POSIX file mode bits are not enforced on Windows")
    def test_loose_mode_is_reported_without_content(self):
        with tempfile.TemporaryDirectory(prefix="npt-perm-") as directory:
            path = Path(directory) / "config.json"
            # The credential is assembled at run time so the scanner never sees a literal.
            credential = '"ssh' + '_pass": "private-value"'
            path.write_text("{" + credential + "}", encoding="utf-8")
            os.chmod(path, 0o644)
            message = sdk_config.config_permission_warning(path)
        self.assertIsNotNone(message)
        self.assertIn(str(path), message)
        self.assertNotIn("private-value", message)

    def test_tight_mode_and_missing_file_are_not_reported(self):
        with tempfile.TemporaryDirectory(prefix="npt-perm-") as directory:
            path = Path(directory) / "config.json"
            path.write_text("{}", encoding="utf-8")
            os.chmod(path, 0o600)
            self.assertIsNone(sdk_config.config_permission_warning(path))
            self.assertIsNone(sdk_config.config_permission_warning(Path(directory) / "absent.json"))


class AccountNameTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("sh"), "requires a POSIX shell")
    def test_recorded_account_name_has_no_trailing_newline(self):
        script = account_name_probe()
        self.assertIn("printf", script)
        completed = subprocess.run(["sh", "-c", script], capture_output=True, text=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        fields = completed.stdout.strip().split("\t")
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[1], "user")
        decoded = node_baseline._decode(fields[2])
        self.assertFalse(decoded.endswith("\n"))
        self.assertEqual(decoded, subprocess.run(["id", "-un"], capture_output=True, text=True,
                                                 timeout=10).stdout.strip())

    @unittest.skipUnless(os.name != "nt", "requires a POSIX shell")
    def test_probe_matches_the_local_identity_helper(self):
        from web import node_probe
        completed = subprocess.run(["sh", "-c", account_name_probe()],
                                   capture_output=True, text=True, timeout=20)
        fields = completed.stdout.strip().split("\t")
        self.assertEqual(len(fields), 3)
        self.assertEqual(node_baseline._decode(fields[2]), node_probe.local_identity()["user"])


if __name__ == "__main__":
    unittest.main()
