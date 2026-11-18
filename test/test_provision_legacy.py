"""Reversible explicit activation over an account's existing legacy configuration."""
import os
from pathlib import Path
import stat
import shutil
import subprocess
import tempfile
import unittest

from web import server


@unittest.skipUnless(os.name != 'nt' and os.geteuid() != 0, 'requires isolated non-root POSIX account')
class LegacyProvisionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='npt-legacy-')
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.env = dict(os.environ, HOME=str(self.home), CURL_HOME='', XDG_CONFIG_HOME='')
        self.proxy = 'http://127.0.0.1:7890'
        self.original = {
            '.curlrc': (b'silent\nproxy = "http://fixture-user:fixture-secret@old.invalid:3128"\n', 0o640),
            '.net-proxy-switch.sh': (b'export HTTP_PROXY="http://old.invalid:3128"\n', 0o700),
            '.profile': (b'# before\n# --- NET-PROXY-TOOL-START ---\n'
                         b'export HTTP_PROXY="http://old.invalid:3128"\n'
                         b'export http_proxy="http://old.invalid:3128"\n'
                         b'# --- NET-PROXY-TOOL-END ---\nexport CUSTOM=unchanged\n', 0o644),
            '.config/pip/pip.conf': (b'[global]\nproxy = http://fixture-user:fixture-secret@old.invalid:3128\n', 0o600),
        }
        for name, (body, mode) in self.original.items():
            path = self.home / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            path.chmod(mode)

    def switch(self, action, proxy=None):
        return subprocess.run(['sh'], input=server.generate_provisioning_script(proxy or self.proxy, 'localhost', action),
                              env=self.env, text=True, capture_output=True, timeout=10)

    def assert_original(self):
        for name, (body, mode) in self.original.items():
            path = self.home / name
            self.assertEqual(path.read_bytes(), body, name)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode, name)
        self.assertFalse((self.home / '.wgetrc').exists())
        self.assertFalse((self.home / '.bashrc').exists())

    def test_explicit_on_preserves_existing_credentials_modes_and_absence(self):
        refused = self.switch('off')
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('Nothing was changed', refused.stderr)
        self.assertFalse((self.home / '.local/state/net-proxy-tool').exists())
        self.assert_original()
        result = self.switch('on')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('restoration baseline', result.stdout)
        self.assertNotIn('fixture-secret', result.stdout + result.stderr)
        state = self.home / '.local/state/net-proxy-tool'
        self.assertTrue((state / 'wgetrc/absent').is_file())
        self.assertEqual((state / 'curlrc/original').read_bytes(), self.original['.curlrc'][0])
        for proxy in (self.proxy, 'http://127.0.0.1:7891', self.proxy):
            result = self.switch('on', proxy)
            self.assertEqual(result.returncode, 0, result.stderr)
            shell = subprocess.run(['sh', '-c', '. "$HOME/.profile"; printf "%s" "$HTTP_PROXY"'],
                                   env=self.env, text=True, capture_output=True, check=True)
            self.assertEqual(shell.stdout, proxy)
        result = self.switch('off')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_original()
        self.assertNotEqual(self.switch('off').returncode, 0)
        self.assert_original()

    def test_same_gateway_is_still_a_baseline_and_manual_edits_block_restore(self):
        self.proxy = 'http://old.invalid:3128'
        self.assertEqual(self.switch('on').returncode, 0)
        managed_curl = (self.home / '.curlrc').read_bytes()
        edited = self.home / '.profile'
        edited.write_bytes(edited.read_bytes() + b'# manual edit\n')
        for action in ('on', 'off'):
            result = self.switch(action)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Edited since activation', result.stderr)
            self.assertEqual((self.home / '.curlrc').read_bytes(), managed_curl)
            self.assertTrue(edited.read_bytes().endswith(b'# manual edit\n'))
        self.assertEqual((self.home / '.local/state/net-proxy-tool/curlrc/original').read_bytes(),
                         self.original['.curlrc'][0])

    def test_profile_marker_without_legacy_helper_is_preserved(self):
        (self.home / '.net-proxy-switch.sh').unlink()
        del self.original['.net-proxy-switch.sh']
        result = self.switch('on')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Legacy v1.3', result.stdout)
        self.assertEqual(self.switch('off').returncode, 0)
        self.assert_original()
        self.assertFalse((self.home / '.net-proxy-switch.sh').exists())

    def test_incomplete_or_nested_profile_block_refuses_all_writes(self):
        profile = self.home / '.profile'
        original = profile.read_bytes()
        for invalid in (original.replace(b'# --- NET-PROXY-TOOL-END ---\n', b''),
                        original.replace(b'# --- NET-PROXY-TOOL-START ---\n', b''),
                        original.replace(b'# --- NET-PROXY-TOOL-START ---\n',
                                         b'# --- NET-PROXY-TOOL-START ---\n' * 2)):
            profile.write_bytes(invalid)
            self.original['.profile'] = (invalid, 0o644)
            result = self.switch('on')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Incomplete legacy proxy block', result.stderr)
            self.assert_original()
            self.assertFalse((self.home / '.local/state/net-proxy-tool/curlrc').exists())

    def test_legacy_bashrc_before_noninteractive_return_uses_selected_gateway(self):
        bashrc = self.home / '.bashrc'
        original = (self.original['.profile'][0] + b'[ -z "$PS1" ] && return\nexport AFTER_RETURN=1\n')
        bashrc.write_bytes(original)
        bashrc.chmod(0o640)
        result = self.switch('on')
        self.assertEqual(result.returncode, 0, result.stderr)
        shell = subprocess.run(['sh', '-c', '. "$HOME/.bashrc"; printf "%s" "$HTTP_PROXY"'],
                               env=dict(self.env, PS1=''), text=True, capture_output=True, check=True)
        self.assertEqual(shell.stdout, self.proxy)
        result = self.switch('off')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(bashrc.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(bashrc.stat().st_mode), 0o640)

    @unittest.skipUnless(shutil.which('git'), 'requires git to reproduce configuration failure')
    def test_generation_failure_leaves_all_files_unchanged_and_can_restore(self):
        git = self.home / '.gitconfig'
        git.write_bytes(b'[invalid\n')
        git.chmod(0o600)
        result = self.switch('on')
        self.assertNotEqual(result.returncode, 0)
        self.assert_original()
        self.assertEqual(git.read_bytes(), b'[invalid\n')
        self.assertEqual(self.switch('off').returncode, 0)
        self.assert_original()
        self.assertEqual(git.read_bytes(), b'[invalid\n')

    def seed_partial_snapshot(self, key, name, *, applied=False, next_copy=False):
        directory = self.home / '.local/state/net-proxy-tool' / key
        directory.mkdir(parents=True, exist_ok=True)
        path = self.home / name
        (directory / 'path').write_text(str(path) + '\n')
        if path.exists():
            shutil.copy2(path, directory / 'original')
        else:
            (directory / 'absent').touch()
        if applied or next_copy:
            path.write_bytes(b'# staged managed fixture\n')
            shutil.copy2(path, directory / ('applied' if applied else 'next'))
        return directory

    def test_historical_partial_activation_restores_only_actual_snapshots(self):
        self.seed_partial_snapshot('curlrc', '.curlrc', applied=True)
        self.seed_partial_snapshot('pip', '.config/pip/pip.conf')
        self.seed_partial_snapshot('wgetrc', '.wgetrc', next_copy=True)
        # Interrupted before copying any baseline: leave the unrelated existing file intact.
        empty = self.home / '.local/state/net-proxy-tool/git'
        empty.mkdir()
        git = self.home / '.gitconfig'
        git.write_bytes(b'# no complete snapshot\n')
        (empty / 'path').write_text(str(git) + '\n')
        result = self.switch('off')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_original()
        self.assertEqual(git.read_bytes(), b'# no complete snapshot\n')

    def test_operator_edit_after_partial_preparation_is_not_overwritten(self):
        self.seed_partial_snapshot('curlrc', '.curlrc', applied=True)
        self.seed_partial_snapshot('pip', '.config/pip/pip.conf')
        pip = self.home / '.config/pip/pip.conf'
        pip.write_bytes(b'# operator update\n')
        curl = (self.home / '.curlrc').read_bytes()
        result = self.switch('off')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Edited since snapshot preparation', result.stderr)
        self.assertEqual((self.home / '.curlrc').read_bytes(), curl)
        self.assertEqual(pip.read_bytes(), b'# operator update\n')

    def test_unreadable_baseline_blocks_restore_before_any_target_write(self):
        self.assertEqual(self.switch('on').returncode, 0)
        managed = {name: (self.home / name).read_bytes() for name in self.original}
        baseline = self.home / '.local/state/net-proxy-tool/pip/original'
        baseline.chmod(0)
        try:
            result = self.switch('off')
            self.assertNotEqual(result.returncode, 0)
            for name, contents in managed.items():
                self.assertEqual((self.home / name).read_bytes(), contents, name)
        finally:
            baseline.chmod(self.original['.config/pip/pip.conf'][1])
        self.assertEqual(self.switch('off').returncode, 0)
        self.assert_original()

    def test_unreadable_source_blocks_activation_without_deleting_partial_snapshot_target(self):
        pip = self.home / '.config/pip/pip.conf'
        pip.chmod(0)
        try:
            result = self.switch('on')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((self.home / '.curlrc').read_bytes(), self.original['.curlrc'][0])
            self.assertEqual((self.home / '.net-proxy-switch.sh').read_bytes(), self.original['.net-proxy-switch.sh'][0])
            self.assertFalse((self.home / '.wgetrc').exists())
        finally:
            pip.chmod(self.original['.config/pip/pip.conf'][1])
        self.assertEqual(self.switch('off').returncode, 0)
        self.assert_original()


if __name__ == '__main__':
    unittest.main()
