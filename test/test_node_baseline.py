"""Fresh-login observations and byte/mode preserving lifecycle in isolated HOME."""
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

from web.node_baseline import capture_node_baseline, verify_node_baseline, wrap_login_script
from web.server import generate_provisioning_script


class BaselineFailureTests(unittest.TestCase):
    def test_missing_login_output_is_not_verified_and_stderr_is_not_exposed(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, 'other startup output', 'fixture-secret'))
        result = capture_node_baseline({}, runner)
        self.assertFalse(result['ok'])
        self.assertNotIn('fixture-secret', str(result))
        self.assertFalse(verify_node_baseline({}, None, runner)['verified'])


@unittest.skipUnless(os.name != 'nt' and hasattr(os, 'geteuid') and os.geteuid() != 0,
                     'requires isolated non-root POSIX account')
class LoginBaselineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='npt-baseline-')
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.env = {key: value for key, value in os.environ.items() if key.lower() not in
                    ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
        self.env.update(HOME=str(self.home), CURL_HOME='', XDG_CONFIG_HOME='', HISTFILE='/dev/null')
        self.gateway = {'host': 'selected.invalid', 'port': 7890}
        self.proxy = 'http://selected.invalid:7890'
        self.target = {'id': 'isolated-account'}

    def runner(self, target, script, timeout=20):
        return subprocess.run(['sh'], input=script, env=self.env, text=True, capture_output=True, timeout=timeout)

    def switch(self, action, *, owner='isolated-account'):
        script = generate_provisioning_script(self.proxy, 'localhost', action, owner=owner)
        return self.runner(self.target, script)

    def write(self, name, contents, mode=0o640):
        path = self.home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        path.chmod(mode)
        return path

    def capture(self):
        result = capture_node_baseline(self.target, self.runner, self.gateway)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['execution_identity']['home'], str(self.home))
        return result

    def test_three_initial_proxy_baselines_return_to_same_fresh_login(self):
        for old in ('', self.proxy, 'http://fixture-user:fixture-secret@old.invalid:3128'):
            with self.subTest(initial=bool(old), same=old == self.proxy):
                profile = self.write('.profile', '# user profile\n' + (
                    'export HTTP_PROXY=' + shlex.quote(old) + '\nexport https_proxy=' + shlex.quote(old) + '\n' if old else ''))
                baseline = self.capture()
                original = profile.read_bytes()
                self.assertEqual(self.switch('on').returncode, 0)
                active = self.capture()
                self.assertEqual(active['managed']['state'], 'enabled')
                self.assertEqual(active['managed']['owner_node_id'], self.target['id'])
                self.assertTrue(active['login']['proxy_variables']['HTTP_PROXY']['matches_selected_gateway'])
                self.assertNotIn('fixture-secret', str(active) + str(baseline))
                self.assertEqual(self.switch('off').returncode, 0)
                verified = verify_node_baseline(self.target, baseline, self.runner, self.gateway)
                self.assertTrue(verified['verified'], verified)
                self.assertEqual(verified['verification_scope'], 'login_and_managed_files')
                self.assertEqual(profile.read_bytes(), original)

    def test_permissions_created_directories_and_preexisting_state_survive_exactly(self):
        profile = self.write('.profile', '# baseline\n', 0o600)
        git = self.write('.gitconfig', '[user]\n\tname = fixture\n', 0o640)
        state = self.home / '.local/state/net-proxy-tool'
        state.mkdir(parents=True)
        state.chmod(0o750)
        (state / 'curlrc').mkdir(mode=0o710)
        owner = self.write('.local/state/net-proxy-tool/owner-uid', str(os.geteuid()) + '\n', 0o640)
        old_node = self.write('.local/state/net-proxy-tool/owner-node-id', 'historical-inactive-node\n', 0o600)
        old_path = self.write('.local/state/net-proxy-tool/curlrc/path', str(self.home / '.curlrc') + '\n', 0o600)
        original = {path: (path.read_bytes(), path.stat().st_mode, int(path.stat().st_mtime))
                    for path in (profile, git, owner, old_node, old_path)}
        baseline = self.capture()
        self.assertFalse((self.home / '.config').exists())
        self.assertEqual(self.switch('on').returncode, 0)
        self.assertEqual(self.switch('off').returncode, 0)
        for path, expected in original.items():
            self.assertEqual((path.read_bytes(), path.stat().st_mode, int(path.stat().st_mtime)), expected)
        self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o750)
        self.assertEqual(stat.S_IMODE((state / 'curlrc').stat().st_mode), 0o710)
        self.assertEqual(sorted(p.name for p in state.iterdir()), ['curlrc', 'owner-node-id', 'owner-uid'])
        self.assertFalse((self.home / '.config').exists())
        self.assertTrue(verify_node_baseline(self.target, baseline, self.runner, self.gateway)['verified'])

    def test_no_preexisting_directories_leave_no_tool_created_tree_after_off(self):
        self.write('.profile', '# fixture\n')
        self.assertEqual(self.switch('on').returncode, 0)
        self.assertEqual(self.switch('off').returncode, 0)
        self.assertFalse((self.home / '.config').exists())
        self.assertFalse((self.home / '.local').exists())

    def test_manual_permission_change_blocks_restore_and_other_node_cannot_take_over(self):
        self.write('.profile', '# fixture\n')
        self.assertEqual(self.switch('on').returncode, 0)
        path = self.home / '.curlrc'
        applied = path.read_bytes()
        for action in ('on', 'off'):
            result = self.switch(action, owner='different-registration')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_bytes(), applied)
        path.chmod(0o644)
        self.assertNotEqual(self.switch('off').returncode, 0)
        self.assertEqual(path.read_bytes(), applied)
        path.chmod(0o600)
        self.assertEqual(self.switch('off').returncode, 0)

    def test_restore_old_active_snapshot_can_verify_files_without_guessing_old_login(self):
        self.write('.profile', '# fixture\nexport HTTP_PROXY=http://original.invalid:3128\n')
        self.assertEqual(self.switch('on').returncode, 0)
        active = self.capture()
        self.assertEqual(self.switch('off').returncode, 0)
        result = verify_node_baseline(self.target, active, self.runner, self.gateway)
        self.assertTrue(result['verified'], result)
        self.assertEqual(result['verification_scope'], 'managed_files_only')

    def test_changed_external_login_source_is_not_mistaken_for_success(self):
        profile = self.write('.profile', '# fixture\n')
        baseline = self.capture()
        self.assertEqual(self.switch('on').returncode, 0)
        self.assertEqual(self.switch('off').returncode, 0)
        profile.write_text('export HTTP_PROXY=http://changed.invalid:3128\n')
        result = verify_node_baseline(self.target, baseline, self.runner, self.gateway)
        self.assertFalse(result['verified'])
        self.assertFalse(result['checks']['proxy_environment'])

    def test_failure_during_apply_rolls_back_prior_target_and_retry_can_restore(self):
        self.write('.profile', '# fixture\n')
        curl = self.write('.curlrc', '# original curl\n')
        wget = self.write('.wgetrc', '# original wget\n')
        real_cp = shutil.which('cp')
        wrapper = self.write('fixture-bin/cp', '#!/bin/sh\nfor last; do :; done\n'
                             'if [ "$last" = "$HOME/.wgetrc" ] && [ ! -f "$HOME/failure-injected" ]; then\n'
                             '  : > "$HOME/failure-injected"; exit 1\nfi\nexec ' + shlex.quote(real_cp) + ' "$@"\n', 0o700)
        self.env['PATH'] = str(wrapper.parent) + os.pathsep + self.env['PATH']
        original = curl.read_bytes()
        result = self.switch('on')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.home / 'failure-injected').exists())
        self.assertEqual(curl.read_bytes(), original)
        self.assertEqual(wget.read_text(), '# original wget\n')
        self.assertFalse((self.home / '.local/state/net-proxy-tool/lock').exists())
        self.assertFalse(list((self.home / '.local/state/net-proxy-tool').glob('.transaction.*')))
        self.assertEqual(self.switch('off').returncode, 0)

    def test_login_only_curl_home_is_the_same_context_for_activation_and_restoration(self):
        self.write('.profile', 'export CURL_HOME="$HOME/custom-curl"\n')
        curl = self.write('custom-curl/.curlrc', '# original active curl\n', 0o640)
        original = curl.read_bytes()
        baseline = self.capture()
        self.assertEqual(baseline['login']['curl']['path'], str(curl))
        for action in ('on', 'off'):
            script = generate_provisioning_script(self.proxy, 'localhost', action, owner=self.target['id'])
            result = self.runner(self.target, wrap_login_script(script))
            self.assertEqual(result.returncode, 0, result.stderr)
            if action == 'on':
                self.assertIn(self.proxy.encode(), curl.read_bytes())
        self.assertEqual(curl.read_bytes(), original)
        self.assertTrue(verify_node_baseline(self.target, baseline, self.runner, self.gateway)['verified'])

    def test_other_snapshot_account_is_not_overwritten(self):
        owner = self.write('.local/state/net-proxy-tool/owner-uid', str(os.geteuid() + 1000) + '\n')
        original = owner.read_bytes()
        result = self.switch('on')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(owner.read_bytes(), original)
        self.assertFalse((self.home / '.curlrc').exists())


if __name__ == '__main__':
    unittest.main()
