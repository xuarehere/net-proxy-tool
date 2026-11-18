"""One-identity SSH authentication and optional disposable OpenSSH integration.

Set NET_PROXY_TEST_SSH_PASSWORD_IMAGE to an existing ssh-target.Dockerfile image
to exercise the native controller's OpenSSH password path. No image is pulled.
NET_PROXY_TEST_SSH_CONTROLLER_IMAGE additionally verifies a Linux controller.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

from sdk.config import load_config, save_config
from web import server, ssh_askpass


def wait_for_disposable_ssh(docker, name, port, timeout=30):
    """Read only this fixture's key, and wait for its published SSH protocol banner."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = docker('exec', name, 'cat', '/etc/ssh/ssh_host_ed25519_key.pub', check=False)
        key = result.stdout.decode('utf-8', 'replace').split()
        if result.returncode == 0 and result.stdout.endswith(b'\n') and len(key) >= 2 and key[0] == 'ssh-ed25519':
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.5) as connection:
                    if connection.recv(256).startswith(b'SSH-'):
                        return key
            except OSError:
                pass
        time.sleep(0.1)
    raise RuntimeError('Disposable SSH fixture did not produce its host key and accept SSH connections in time')


class SSHFixtureReadinessTests(unittest.TestCase):
    def test_waits_for_both_key_generation_and_ssh_listener(self):
        missing = subprocess.CompletedProcess([], 1, b'', b'')
        partial = subprocess.CompletedProcess([], 0, b'ssh-ed25519 fixture', b'')
        ready = subprocess.CompletedProcess([], 0, b'ssh-ed25519 fixture fixture@node\n', b'')
        with patch('time.sleep'), patch('socket.create_connection') as connect:
            connect.side_effect = [ConnectionRefusedError(), connect.return_value]
            connect.return_value.__enter__.return_value.recv.return_value = b'SSH-2.0-fixture\r\n'
            with patch('subprocess.run', side_effect=[missing, partial, ready, ready]) as docker:
                key = wait_for_disposable_ssh(docker, 'only-this-fixture', 2222)
                self.assertEqual(docker.call_count, 4)
                self.assertEqual(connect.call_count, 2)
                self.assertEqual(key[:2], ['ssh-ed25519', 'fixture'])


class SSHAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="npt-auth-")
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, NET_PROXY_CONFIG=str(Path(self.temp.name) / 'config.json'))
        env.start()
        self.addCleanup(env.stop)
        self.target = dict(id='node', name='fixture', host='node.invalid', port=2222, ssh_user='tester',
                           auth_type='password', ssh_pass='fixture-secret', access_mode='ssh',
                           identity_version=1, lifecycle_version=1, bound_gateway_id='g')
        cfg = load_config()
        cfg['clients'] = [self.target]
        cfg['gateways'] = [dict(id='g', host='proxy.invalid', port=3128)]
        save_config(cfg)

    def test_password_bridge_is_secret_free_and_scoped(self):
        secret = 'spaces % ! & " \' 中文'
        before = os.environ.copy()
        def execute(command, script, timeout, env):
            helper = Path(env['PATH'].split(os.pathsep)[0]) / env['SSH_ASKPASS'] if os.name == 'nt' else Path(env['SSH_ASKPASS'])
            self.assertTrue(helper.exists())
            self.assertNotIn(secret, helper.read_text())
            self.assertNotIn(secret, repr(command))
            self.assertEqual(env['NET_PROXY_SSH_PASSWORD'], secret)
            self.assertEqual(env['SSH_ASKPASS_REQUIRE'], 'force')
            for option in ('StrictHostKeyChecking=yes', 'NumberOfPasswordPrompts=1',
                           'PreferredAuthentications=password', 'PubkeyAuthentication=no',
                           'KbdInteractiveAuthentication=no', 'ProxyCommand=none', 'ProxyJump=none',
                           'Hostname=node.invalid', 'CanonicalizeHostname=no', 'ControlPath=none',
                           'PermitLocalCommand=no'):
                self.assertIn(option, command)
            self.assertEqual(script, 'action=on\ntrue')
            self.helper = helper
            result = subprocess.run([os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/c', str(helper)]
                                    if os.name == 'nt' else [str(helper)], env=env,
                                    capture_output=True, timeout=10, check=True)
            self.assertEqual(result.stdout.decode('utf-8').strip(), secret)
            return subprocess.CompletedProcess(command, 0, '', '')
        with patch.object(server, 'ssh_with_script', side_effect=execute):
            server.run_remote_ssh_script('node.invalid', 2222, 'tester', 'password', secret, 'action=on\ntrue')
        self.assertFalse(self.helper.exists())
        self.assertEqual(os.environ, before)

    def test_missing_password_never_falls_back_to_other_auth(self):
        with patch.object(server, 'ssh_with_script') as execute:
            for password in (None, '', 'line\nbreak'):
                with self.assertRaises(ValueError):
                    server.run_node_script(dict(self.target, ssh_pass=password), 'true')
            execute.assert_not_called()

    def test_saved_password_never_moves_to_different_destination(self):
        saved = server.preflight_target({'node_id': 'node', 'ssh_pass': ''})
        self.assertEqual(saved['ssh_pass'], self.target['ssh_pass'])
        for changed in ({'host': 'other.invalid'}, {'port': 2223}, {'ssh_user': 'other'},
                        {'access_mode': 'docker_host', 'container_name': 'worker'}):
            with self.assertRaises(ValueError):
                server.preflight_target(dict(changed, node_id='node', ssh_pass=''))
        manual = dict(host='new.invalid', port=22, ssh_user='new', auth_type='password', ssh_pass='new-secret')
        self.assertEqual(server.preflight_target(manual), manual)

    def test_identity_edit_requires_an_explicit_new_password(self):
        handler = object.__new__(server.ProxyConsoleHandler)
        request = dict(id='node', host='different.invalid', ssh_pass='', node_revision=0)
        handler.read_json_body = lambda: request
        handler.send_json = lambda *args, **kwargs: None
        with self.assertRaises(ValueError):
            handler.handle_client_update()
        self.assertEqual(load_config()['clients'][0]['host'], 'node.invalid')
        request.update(ssh_pass='replacement-secret')
        handler.handle_client_update()
        saved = load_config()['clients'][0]
        self.assertEqual(saved['host'], 'different.invalid')
        self.assertEqual(saved['ssh_pass'], 'replacement-secret')

    def test_timeout_removes_helper_without_mutating_parent_environment(self):
        before = os.environ.copy()
        def timeout(command, script, budget, env):
            self.helper = Path(env['PATH'].split(os.pathsep)[0]) / env['SSH_ASKPASS'] if os.name == 'nt' else Path(env['SSH_ASKPASS'])
            raise subprocess.TimeoutExpired(command, budget)
        with patch.object(server, 'ssh_with_script', side_effect=timeout):
            with self.assertRaises(subprocess.TimeoutExpired):
                server.run_node_script(self.target, 'true')
        self.assertFalse(self.helper.exists())
        self.assertEqual(os.environ, before)

    def test_docker_and_direct_use_same_auth_without_enrollment(self):
        with patch.object(server, 'run_remote_ssh_script', return_value=subprocess.CompletedProcess([], 0, '', '')) as execute:
            for mode in ('ssh', 'docker_host'):
                target = dict(self.target, access_mode=mode, container_name='worker')
                server.run_node_script(target, 'true')
                self.assertEqual(execute.call_args.args[:5], ('node.invalid', 2222, 'tester', 'password', 'fixture-secret'))
                self.assertIn('NPT_SSH_READY', execute.call_args.kwargs['remote_command'])
                if mode == 'docker_host':
                    self.assertIn('docker exec -i -u 0 worker sh', execute.call_args.kwargs['remote_command'])
        baseline = {'ok': True, 'execution_identity': {'user': 'tester'}}
        with patch.object(server, 'run_node_script', return_value=subprocess.CompletedProcess([], 0, '', '')) as execute, \
                patch.object(server.node_baseline, 'capture_node_baseline', return_value=baseline), \
                patch.object(server.node_baseline, 'inspect_node_state', return_value=dict(baseline,
                             managed={'state': 'enabled', 'owner_node_id': 'node'},
                             login={'proxy_variables': {key: {'matches_selected_gateway': True} for key in
                                    ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY')}})):
            cfg = dict(gateways=[dict(id='g', host='proxy.invalid', port=3128)], active_gateway_id='g')
            original = dict(self.target)
            result = server.apply_node_proxy(self.target, 'on', cfg)
            self.assertEqual(result['returncode'], 0)
            execute.assert_called_once()
            self.assertEqual(self.target['ssh_pass'], original['ssh_pass'])
            self.assertEqual(self.target['_node_baseline'], baseline)

    def test_key_auth_requires_trusted_host_and_cannot_prompt_password(self):
        with patch.object(server, 'ssh_with_script') as execute:
            server.run_remote_ssh_script('node.invalid', 22, 'tester', 'key', None, 'true')
        command = execute.call_args.args[0]
        self.assertIn('StrictHostKeyChecking=yes', command)
        self.assertIn('BatchMode=yes', command)
        self.assertIn('PasswordAuthentication=no', command)
        self.assertNotIn('env', execute.call_args.kwargs)


@unittest.skipUnless(os.environ.get('NET_PROXY_TEST_SSH_PASSWORD_IMAGE'), 'optional disposable SSH image')
class NativePasswordIntegration(unittest.TestCase):
    def test_one_disposable_identity_preflight_switch_probe_and_fail_closed(self):
        image = os.environ['NET_PROXY_TEST_SSH_PASSWORD_IMAGE']
        name = 'npt-auth-' + uuid.uuid4().hex[:10]
        def docker(*args, data=None, check=True):
            return subprocess.run(['docker', *args], input=data, capture_output=True, check=check, timeout=30)
        docker('image', 'inspect', image)
        # A single disposable account; password is set using stdin, never argv.
        docker('run', '--rm', '-d', '--name', name, '-p', '127.0.0.1::22', '--entrypoint', 'sh', image, '-ec',
               'ssh-keygen -A >/dev/null; python -m http.server 8080 --bind 127.0.0.1 >/dev/null 2>&1 & '
               'exec /usr/sbin/sshd -D -e -o PasswordAuthentication=yes -o PubkeyAuthentication=no '
               '-o KbdInteractiveAuthentication=no -o PermitRootLogin=no -o AllowUsers=tester')
        self.addCleanup(lambda: docker('rm', '-f', name, check=False))
        secret = 'Fixture-only ' + uuid.uuid4().hex + ' !%& 中文'
        docker('exec', '-i', name, 'chpasswd', data=('tester:' + secret + '\n').encode())
        port = int(docker('port', name, '22/tcp').stdout.decode().strip().rsplit(':', 1)[1])
        host_key = wait_for_disposable_ssh(docker, name, port)
        with tempfile.TemporaryDirectory(prefix='npt 中文 space-') as directory:
            path = Path(directory)
            known = path / 'known_hosts'
            known.write_text(f'[127.0.0.1]:{port} {host_key[0]} {host_key[1]}\n', encoding='ascii')
            unknown = path / 'unknown_hosts'
            unknown.write_text('', encoding='ascii')
            helper = path / 'ssh helper 中文.py'
            shutil.copyfile(ssh_askpass.__file__, helper)
            original = server.ssh_with_script
            selected_known = known
            def isolated(command, script, timeout, env=None):
                command = [command[0], '-F', 'none', '-o', 'UserKnownHostsFile="' + selected_known.as_posix() + '"',
                           '-o', 'GlobalKnownHostsFile=none', *command[1:]]
                return original(command, script, timeout, env)
            target = dict(id='one-node', name='disposable', host='127.0.0.1', port=port, ssh_user='tester',
                          auth_type='password', ssh_pass=secret, os_type='linux', bound_gateway_id='g')
            with patch.object(server, 'ssh_with_script', side_effect=isolated), \
                    patch.object(ssh_askpass, '__file__', str(helper)), \
                    patch.object(tempfile, 'tempdir', directory), \
                    patch.dict(os.environ, NET_PROXY_CONFIG=str(path / 'config.json')):
                cfg = load_config()
                cfg.update(clients=[target], gateways=[dict(id='g', host='127.0.0.1', port=8080)], active_gateway_id='g')
                save_config(cfg)
                handler = object.__new__(server.ProxyConsoleHandler)
                handler.read_json_body = lambda: dict(node_id='one-node', ssh_pass='')
                replies = []
                handler.send_json = lambda value, *args, **kwargs: replies.append(value)
                handler.handle_test_node_preflight()
                self.assertTrue(replies[-1]['success'], replies[-1])
                result = server.run_node_script(target, 'id -un\n')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('NPT_SSH_READY\ntester', result.stdout)
                for action in ('on', 'off'):
                    result = server.apply_node_proxy(target, action, cfg)
                    self.assertEqual(result.get('returncode'), 0, result)
                result = server.check_node_http(target, target_url='http://127.0.0.1:8080/')
                self.assertTrue(result['online'], result)
                self.assertEqual(result['code'], 200, result)
                # Unknown host keys fail before authentication; no enrollment or retries.
                selected_known = unknown
                result = server.run_node_script(target, 'true')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Host key verification failed', result.stderr)
                selected_known = known
                result = server.run_node_script(dict(target, ssh_pass='deliberately-invalid'), 'true')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('NPT_SSH_READY', result.stdout)
                self.assertNotIn(secret, result.stderr)
                self.assertFalse(list(path.glob('npt-askpass-*')))
                self.assertNotIn('NET_PROXY_SSH_PASSWORD', os.environ)
                self.assertEqual(load_config()['clients'][0]['auth_type'], 'password')
                self.assertEqual(docker('exec', name, 'test', '-e', '/home/tester/.ssh/authorized_keys', check=False).returncode, 1)
                logs = docker('logs', name).stderr.decode('utf-8', 'replace')
                self.assertEqual(logs.count('Failed password for tester'), 1, logs)
                controller_image = os.environ.get('NET_PROXY_TEST_SSH_CONTROLLER_IMAGE')
                if controller_image:
                    docker('image', 'inspect', controller_image)
                    # Share only this disposable node's network namespace. Password is stdin JSON.
                    script = '''
import json, pathlib, sys, tempfile
from unittest.mock import patch
from web import server
target, public_key = json.load(sys.stdin)
with tempfile.TemporaryDirectory() as directory:
    known = pathlib.Path(directory) / 'known_hosts'
    known.write_text('127.0.0.1 ' + public_key + '\\n', encoding='ascii')
    original = server.ssh_with_script
    def isolated(command, script, timeout, env=None):
        command = [command[0], '-F', 'none', '-o', 'UserKnownHostsFile=' + str(known),
                   '-o', 'GlobalKnownHostsFile=none', *command[1:]]
        return original(command, script, timeout, env)
    with patch.object(server, 'ssh_with_script', side_effect=isolated):
        result = server.run_node_script(target, 'id -un\\n')
        assert result.returncode == 0, result.stderr
        assert 'NPT_SSH_READY\\ntester' in result.stdout, result.stdout
print('POSIX_SSH_OK')
'''
                    linux_target = dict(target, port=22)
                    result = docker('run', '--rm', '-i', '--network', 'container:' + name,
                                    '-v', str(Path(__file__).resolve().parents[1]) + ':/code:ro', '-w', '/code',
                                    '--entrypoint', 'python', controller_image, '-c', script,
                                    data=json.dumps([linux_target, ' '.join(host_key[:2])]).encode())
                    self.assertIn(b'POSIX_SSH_OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
