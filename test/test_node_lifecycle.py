"""Lifecycle regressions: isolated config, fixed observations, no remote access."""
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
import copy
import http.client
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from sdk.config import load_config, save_config
from web import server


def outcome(action, verified=True):
    return {'returncode': 0 if verified else 1,
            'managed_state': ('enabled' if action == 'on' else 'disabled') if verified else 'unknown',
            'verification': {'verified': verified, 'status': 'restored' if verified else 'unknown',
                             'verification_scope': 'login_and_managed_files'},
            'error': None if verified else 'Independent verification could not confirm restoration'}


def matching_login():
    return {'proxy_variables': {key: {'present': True, 'matches_selected_gateway': True}
                                for key in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY')}}


class NodeLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory(prefix='npt-lifecycle-'))
        self.stack.enter_context(patch.dict(os.environ, NET_PROXY_CONFIG=str(Path(directory) / 'config.json')))
        # Any accidental unmocked transport must fail locally rather than touch a node.
        self.transport = self.stack.enter_context(patch.object(
            server, 'run_remote_ssh_script', side_effect=AssertionError('Unexpected remote execution')))
        cfg = load_config()
        cfg.update(gateways=[{'id': 'gw', 'name': 'fixture', 'host': 'proxy.invalid', 'port': 3128}],
                   active_gateway_id='gw', clients=[])
        save_config(cfg)
        self.web = self.stack.enter_context(ThreadingHTTPServer(('127.0.0.1', 0), server.ProxyConsoleHandler))
        worker = threading.Thread(target=self.web.serve_forever, daemon=True)
        worker.start()
        self.stack.callback(worker.join, 3)
        self.stack.callback(self.web.shutdown)

    def api(self, path, body=None, status=200):
        connection = http.client.HTTPConnection(*self.web.server_address, timeout=10)
        try:
            connection.request('GET' if body is None else 'POST', path,
                               None if body is None else json.dumps(body), {'Content-Type': 'application/json'})
            response = connection.getresponse()
            result = json.load(response)
            self.assertEqual(response.status, status, result)
            return result
        finally:
            connection.close()

    def add(self, **values):
        request = dict(name='fixture', host='node.invalid', port=2222, ssh_user='tester',
                       auth_type='key', access_mode='ssh', bound_gateway_id='gw')
        request.update(values)
        return self.api('/api/clients/add', request)['client']

    def stored(self, node_id):
        return next(item for item in load_config()['clients'] if item['id'] == node_id)

    def active(self, **values):
        node = self.add(**values)
        cfg = load_config()
        saved = next(item for item in cfg['clients'] if item['id'] == node['id'])
        saved.update(is_proxy_enabled=True, managed_state='enabled',
                     _node_baseline={'ok': True, 'managed': {'state': 'disabled'}, 'private_marker': 'baseline-private'})
        save_config(cfg)
        return saved

    def selection(self, node):
        return {'node_id': node['id'], 'node_revision': node.get('node_revision', 0),
                'gateway_id': node.get('bound_gateway_id', '')}

    def test_active_delete_failed_verification_keeps_registration_and_credentials(self):
        node = self.active(id='kept', auth_type='password', ssh_pass='old-fixture-secret')
        with patch.object(server, 'apply_node_proxy', return_value=outcome('off', False)) as apply:
            response = self.api('/api/clients/delete', {'id': node['id'], 'node_revision': node['node_revision']}, 502)
        self.assertEqual(apply.call_args.args[1], 'off')
        saved = self.stored('kept')
        self.assertEqual(saved['ssh_pass'], 'old-fixture-secret')
        self.assertTrue(saved['is_proxy_enabled'])
        self.assertEqual(saved['managed_state'], 'unknown')
        self.assertIn('_node_baseline', saved)
        self.assertEqual(load_config().get('archived_clients', []), [])
        self.assertNotIn('old-fixture-secret', json.dumps(response))
        self.assertNotIn('baseline-private', json.dumps(response))

    def test_verified_delete_archive_contains_no_credentials_and_readd_uses_new_input(self):
        node = self.active(id='remembered', auth_type='password', ssh_pass='deleted-secret',
                           tags=['private tag'], description='private description')
        cfg = load_config()
        cfg['clients'][0]['unknown_extension'] = {'token': 'hidden-extension'}
        save_config(cfg)
        with patch.object(server, 'apply_node_proxy', return_value=outcome('off')):
            self.api('/api/clients/delete', {'id': node['id'], 'node_revision': node['node_revision']})
        cfg = load_config()
        self.assertEqual(cfg['clients'], [])
        archive = cfg['archived_clients'][0]
        self.assertEqual(archive['bound_gateway_id'], 'gw')
        self.assertFalse({'ssh_pass', 'auth_type', '_node_baseline', 'unknown_extension', 'tags', 'description'} & archive.keys())
        self.assertNotIn('deleted-secret', json.dumps(cfg))
        self.api('/api/clients/add', {'name': 'again', 'host': node['host'], 'port': node['port'],
                                    'ssh_user': 'tester', 'auth_type': 'password'}, 400)
        restored = self.add(id='ignored-new-id', auth_type='password', ssh_pass='new-fixture-secret', bound_gateway_id='')
        self.assertEqual(restored['id'], 'remembered')
        self.assertEqual(restored['bound_gateway_id'], 'gw')
        self.assertGreater(restored['node_revision'], node['node_revision'])
        self.assertEqual(self.stored('remembered')['ssh_pass'], 'new-fixture-secret')
        self.assertNotIn('ssh_pass', restored)
        self.assertFalse(restored['is_proxy_enabled'])
        self.assertEqual(load_config()['archived_clients'], [])

    def test_active_identity_edit_restoration_failure_keeps_original_destination(self):
        node = self.active(id='edit', auth_type='password', ssh_pass='original-secret')
        with patch.object(server, 'apply_node_proxy', return_value=outcome('off', False)) as apply:
            self.api('/api/clients/update', {'id': node['id'], 'node_revision': node['node_revision'],
                                            'host': 'new.invalid', 'ssh_user': 'new-user',
                                            'ssh_pass': 'replacement-secret'}, 502)
        self.assertEqual(apply.call_args.args[0]['host'], 'node.invalid')
        self.assertEqual(apply.call_args.args[1], 'off')
        saved = self.stored('edit')
        self.assertEqual((saved['host'], saved['ssh_user'], saved['ssh_pass']),
                         ('node.invalid', 'tester', 'original-secret'))

    def test_binding_edit_invalidates_verification_without_dispatch_or_changing_recorded_enablement(self):
        node = self.active(id='rebind')
        cfg = load_config()
        cfg['gateways'].append({'id': 'other', 'name': 'other', 'host': 'other-proxy.invalid', 'port': 8080})
        cfg['clients'][0].update(applied_gateway_id='gw', verification={'verified': True, 'status': 'enabled'})
        save_config(cfg)
        with patch.object(server, 'apply_node_proxy') as apply, patch.object(server, 'run_node_script') as execute:
            response = self.api('/api/clients/update', {'id': node['id'], 'node_revision': node['node_revision'],
                                                       'bound_gateway_id': 'other'})
            apply.assert_not_called()
            execute.assert_not_called()
        saved = self.stored(node['id'])
        self.assertEqual(saved['bound_gateway_id'], 'other')
        self.assertEqual(saved['applied_gateway_id'], 'gw')
        self.assertTrue(saved['is_proxy_enabled'])
        self.assertEqual(saved['managed_state'], 'unknown')
        self.assertFalse(saved['verification']['verified'])
        self.assertEqual(saved['_node_baseline'], node['_node_baseline'])
        self.assertEqual(response['client']['managed_state'], 'unknown')

    def test_gateway_address_edit_invalidates_bound_node_revision_before_any_dispatch(self):
        node = self.active(id='gateway-edit')
        with patch.object(server, 'apply_node_proxy') as apply, patch.object(server, 'run_node_script') as execute:
            self.api('/api/gateways/update', {'id': 'gw', 'host': 'new-proxy.invalid', 'port': 3129})
            saved = self.stored(node['id'])
            self.assertEqual(saved['bound_gateway_id'], 'gw')
            self.assertEqual(saved['node_revision'], node['node_revision'] + 1)
            self.assertEqual(saved['binding_revision'], node.get('binding_revision', 0) + 1)
            self.assertEqual(saved['managed_state'], 'unknown')
            self.assertTrue(saved['is_proxy_enabled'])
            self.api('/api/node-switch', dict(self.selection(node), action='on'), 409)
            apply.assert_not_called()
            execute.assert_not_called()

    def test_changed_or_unknown_execution_identity_prevents_write_and_preserves_baseline(self):
        identity = {'uid': '1000', 'user': 'tester', 'home': '/home/tester', 'shell': '/bin/sh'}
        node = self.active(id='execution-guard')
        baseline = {'ok': True, 'execution_identity': identity, 'managed': {'state': 'disabled'}}
        for changed in ('saved_destination', 'uid', 'home', 'shell', 'unknown'):
            with self.subTest(changed=changed):
                cfg = load_config()
                target = cfg['clients'][0]
                target['_node_baseline'] = copy.deepcopy(baseline)
                target['applied_identity'] = list(server.node_ssh_identity(target))
                if changed == 'saved_destination':
                    target['applied_identity'][1] = 'previous.invalid'
                observed_identity = dict(identity)
                if changed in identity:
                    observed_identity[changed] = 'different-' + observed_identity[changed]
                observed = {'ok': changed != 'unknown', 'execution_identity': observed_identity}
                with patch.object(server.node_baseline, 'capture_node_baseline', return_value=observed), \
                        patch.object(server, 'run_node_script') as execute:
                    result = server.apply_node_proxy(target, 'off', cfg)
                self.assertNotEqual(result['returncode'], 0)
                self.assertEqual(result['managed_state'], 'unknown')
                self.assertEqual(target['_node_baseline'], baseline)
                self.assertNotIn('pending_action', target)
                execute.assert_not_called()

    def test_delete_restored_node_rechecks_read_only_and_preserves_registration_on_failure(self):
        node = self.active(id='restored-delete')
        verified = {'verified': True, 'status': 'restored', 'verification_scope': 'login_and_managed_files',
                    'checks': {'identity': True, 'managed_files': True}, 'observation': {}}
        with patch.object(server.node_baseline, 'verify_node_baseline', return_value=verified) as verify, \
                patch.object(server.node_baseline, 'capture_node_baseline') as capture, \
                patch.object(server, 'run_node_script', return_value=subprocess.CompletedProcess([], 0, '', '')) as execute:
            self.api('/api/node-switch', dict(self.selection(node), action='off'))
            restored = self.stored(node['id'])['_node_restored_baseline']
            execute.reset_mock()
            verify.reset_mock()
            # A failed deletion and its retry must only inspect the already restored baseline.
            for status in (False, True):
                verify.return_value = dict(verified, verified=status, status='restored' if status else 'changed')
                current = self.stored(node['id'])
                self.api('/api/clients/delete', {'id': node['id'], 'node_revision': current['node_revision']},
                         200 if status else 502)
                self.assertEqual(verify.call_args.args[1], restored)
                execute.assert_not_called()
                capture.assert_not_called()
                if not status:
                    self.assertEqual(self.stored(node['id'])['managed_state'], 'unknown')
                    self.assertEqual(load_config().get('archived_clients', []), [])
            self.assertEqual(verify.call_count, 2)
        self.assertEqual(load_config()['clients'], [])

    def test_stale_or_missing_versions_reject_all_mutations_before_dispatch(self):
        first, second = self.active(id='first'), self.active(id='second', port=2223)
        with patch.object(server, 'apply_node_proxy') as apply:
            for revision in (None, -1):
                version = {} if revision is None else {'node_revision': revision}
                for route, body in (('/api/clients/delete', {'id': first['id']}),
                                    ('/api/clients/update', {'id': first['id'], 'name': 'stale'}),
                                    ('/api/node-switch', {'node_id': first['id'], 'action': 'off'})):
                    self.api(route, dict(body, **version), 409)
            selections = [self.selection(first), dict(self.selection(second), node_revision=-1)]
            self.api('/api/nodes/batch-switch', {'action': 'off', 'nodes': selections}, 409)
            apply.assert_not_called()
        self.assertEqual(self.stored('first')['node_revision'], first['node_revision'])

    def test_concurrent_same_version_switch_is_dispatched_once(self):
        node = self.add(id='concurrent')
        entered, release = threading.Event(), threading.Event()
        def dispatch(target, action, config):
            entered.set()
            self.assertTrue(release.wait(5), 'test did not release isolated dispatch')
            return outcome(action)
        request = dict(self.selection(node), action='on')
        with patch.object(server, 'apply_node_proxy', side_effect=dispatch) as apply, ThreadPoolExecutor(2) as pool:
            first = pool.submit(self.api, '/api/node-switch', request)
            self.assertTrue(entered.wait(5))
            second = pool.submit(self.api, '/api/node-switch', request, 409)
            release.set()
            self.assertTrue(first.result(timeout=5)['success'])
            self.assertFalse(second.result(timeout=5)['success'])
        self.assertEqual(apply.call_count, 1)
        self.assertEqual(self.stored(node['id'])['node_revision'], node['node_revision'] + 1)

    def test_imported_archive_cannot_restore_secrets_or_stale_baseline(self):
        cfg = load_config()
        cfg['archived_clients'] = [dict(id='old-archive', name='old', host='node.invalid', port=2222,
                                        access_mode='ssh', ssh_user='tester', bound_gateway_id='gw',
                                        node_revision=8, ssh_pass='archived-password', token='archived-token',
                                        unknown_extension={'password': 'archived-extension'},
                                        _node_baseline={'private': 'archived-baseline'})]
        save_config(cfg)
        node = self.add(bound_gateway_id='', ssh_pass='irrelevant-key-password')
        self.assertEqual(node['id'], 'old-archive')
        self.assertEqual(node['bound_gateway_id'], 'gw')
        self.assertEqual(node['node_revision'], 9)
        saved = self.stored(node['id'])
        self.assertFalse({'ssh_pass', 'token', '_node_baseline', 'unknown_extension'} & saved.keys())

    def test_legacy_local_record_requires_explicit_confirmation_without_dispatch(self):
        cfg = load_config()
        cfg['clients'] = [{'id': 'legacy-local', 'name': 'legacy', 'host': '127.0.0.1',
                           'is_proxy_enabled': True, 'bound_gateway_id': 'gw'}]
        save_config(cfg)
        with patch.object(server, 'run_node_script') as execute, \
                patch.object(server.node_baseline, 'capture_node_baseline') as capture:
            self.api('/api/node-switch', {'node_id': 'legacy-local', 'node_revision': 0, 'action': 'off'}, 400)
            confirmed = self.api('/api/clients/update', {'id': 'legacy-local', 'node_revision': 0,
                                'access_mode': 'local', 'confirm_execution_mode': True})
            execute.assert_not_called()
            capture.assert_not_called()
        self.assertEqual(confirmed['client']['access_mode'], 'local')
        self.assertFalse(confirmed['client']['identity_confirmation_required'])
        self.assertTrue(self.stored('legacy-local')['is_proxy_enabled'])

    def test_batch_only_dispatches_explicit_nodes_and_prevalidates_unbound_nodes(self):
        first, second = self.add(id='first'), self.add(id='second', port=2223, bound_gateway_id='')
        with patch.object(server, 'apply_node_proxy', return_value=outcome('on')) as apply:
            self.api('/api/nodes/batch-switch', {'action': 'on'}, 400)
            self.api('/api/nodes/batch-switch', {'action': 'on', 'nodes': [self.selection(first), self.selection(second)]}, 400)
            apply.assert_not_called()
            result = self.api('/api/nodes/batch-switch', {'action': 'on', 'nodes': [self.selection(first)]})
        self.assertEqual(result['total'], 1)
        self.assertEqual([call.args[0]['id'] for call in apply.call_args_list], ['first'])
        self.assertTrue(self.stored('first')['is_proxy_enabled'])
        self.assertFalse(self.stored('second')['is_proxy_enabled'])

    def test_add_same_identity_is_idempotent_and_same_host_different_port_has_unique_id(self):
        first = self.active(auth_type='password', ssh_pass='retained-secret')
        before = self.stored(first['id'])
        duplicate = self.add(id='not-used', name='do-not-overwrite', auth_type='password', ssh_pass='not-used')
        self.assertEqual(duplicate['id'], first['id'])
        self.assertEqual(self.stored(first['id']), before)
        second = self.add(port=2223)
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(len(load_config()['clients']), 2)

    def test_local_mode_is_explicit_and_ssh_localhost_uses_transport(self):
        ssh = self.add(id='ssh', host='127.0.0.1', port=22)
        local = self.add(id='local', host='127.0.0.1', port=22, access_mode='local')
        self.assertNotEqual(server.management_identity(ssh), server.management_identity(local))
        self.transport.side_effect = None
        self.transport.return_value = subprocess.CompletedProcess([], 0, '', '')
        server.run_node_script(ssh, 'printf fixed')
        self.transport.assert_called_once()
        self.assertEqual(self.transport.call_args.args[:3], ('127.0.0.1', 22, 'tester'))
        self.transport.reset_mock()
        if os.name == 'nt':
            with self.assertRaisesRegex(ValueError, 'Windows'):
                server.run_node_script(local, 'printf fixed')
        else:
            with patch.object(server.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
                server.run_node_script(local, 'printf fixed')
                self.assertEqual(run.call_args.args[0], ['sh'])
        self.transport.assert_not_called()

    def test_journal_precedes_write_and_independent_verification_controls_three_states(self):
        node = self.add(id='journal')
        identity = {'uid': '1000', 'user': 'tester', 'home': '/home/tester', 'shell': '/bin/sh'}
        baseline = {'ok': True, 'execution_identity': identity, 'managed': {'state': 'disabled'},
                    'private_marker': 'original-baseline'}
        for action, verified, expected_state in (('on', True, 'enabled'), ('on', False, 'unknown'),
                                                  ('off', True, 'disabled'), ('off', False, 'unknown')):
            with self.subTest(action=action, verified=verified):
                cfg = load_config()
                target = next(item for item in cfg['clients'] if item['id'] == node['id'])
                target.pop('_node_baseline', None)
                if action == 'off':
                    target['_node_baseline'] = copy.deepcopy(baseline)
                events = []
                def journal(saved):
                    events.append(('save', copy.deepcopy(saved['clients'][0])))
                def execute(target, script, timeout):
                    self.assertEqual(events[0][0], 'save')
                    self.assertEqual(events[0][1]['pending_action'], action)
                    self.assertEqual(events[0][1]['_node_baseline'], baseline)
                    events.append(('execute', script))
                    return subprocess.CompletedProcess([], 0, '', '')
                verification = dict(outcome('off', verified)['verification'], observation={'secret': 'not-public'})
                with patch.object(server.node_baseline, 'capture_node_baseline', return_value=copy.deepcopy(baseline)), \
                        patch.object(server.node_baseline, 'inspect_node_state', return_value={
                            'ok': True, 'execution_identity': identity, 'login': matching_login(),
                            'managed': {'state': 'enabled' if verified else 'unknown', 'owner_node_id': node['id']}}), \
                        patch.object(server.node_baseline, 'verify_node_baseline', return_value=verification), \
                        patch.object(server, 'save_config', side_effect=journal), \
                        patch.object(server, 'run_node_script', side_effect=execute):
                    result = server.apply_node_proxy(target, action, cfg)
                self.assertEqual(result['managed_state'], expected_state)
                self.assertEqual(result['returncode'], 0 if verified else 1)
                self.assertEqual(result['verification']['verified'], verified)
                self.assertNotIn('observation', result['verification'])
                self.assertEqual([event[0] for event in events], ['save', 'execute'])

    def test_enabled_observation_requires_same_execution_identity_and_owner(self):
        node = self.add(id='identity-check')
        identity = {'uid': '1000', 'user': 'tester', 'home': '/home/tester', 'shell': '/bin/sh'}
        baseline = {'ok': True, 'execution_identity': identity, 'managed': {'state': 'disabled'}}
        for observed_identity, owner in ((dict(identity, uid='0'), node['id']), (identity, 'other-node')):
            with self.subTest(identity=observed_identity, owner=owner):
                cfg = load_config()
                with patch.object(server.node_baseline, 'capture_node_baseline', return_value=baseline), \
                        patch.object(server.node_baseline, 'inspect_node_state', return_value={
                            'ok': True, 'execution_identity': observed_identity, 'login': matching_login(),
                            'managed': {'state': 'enabled', 'owner_node_id': owner}}), \
                        patch.object(server, 'run_node_script', return_value=subprocess.CompletedProcess([], 0, '', '')):
                    result = server.apply_node_proxy(cfg['clients'][0], 'on', cfg)
                self.assertEqual(result['managed_state'], 'unknown')
                self.assertNotEqual(result['returncode'], 0)
                self.assertFalse(result['verification']['verified'])

    def test_managed_files_without_matching_fresh_login_environment_are_not_enabled(self):
        node = self.add(id='login-check')
        identity = {'uid': '1000', 'user': 'tester', 'home': '/home/tester', 'shell': '/bin/sh'}
        baseline = {'ok': True, 'execution_identity': identity, 'managed': {'state': 'disabled'}}
        for variable in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY'):
            with self.subTest(variable=variable):
                login = matching_login()
                login['proxy_variables'][variable]['matches_selected_gateway'] = False
                cfg = load_config()
                with patch.object(server.node_baseline, 'capture_node_baseline', return_value=baseline), \
                        patch.object(server.node_baseline, 'inspect_node_state', return_value={
                            'ok': True, 'execution_identity': identity, 'login': login,
                            'managed': {'state': 'enabled', 'owner_node_id': node['id']}}), \
                        patch.object(server, 'run_node_script', return_value=subprocess.CompletedProcess([], 0, '', '')):
                    result = server.apply_node_proxy(cfg['clients'][0], 'on', cfg)
                self.assertEqual(result['managed_state'], 'unknown')
                self.assertFalse(result['verification']['verified'])
                self.assertFalse(result['verification']['checks']['login_proxy'])

    def test_old_record_without_restoration_evidence_never_dispatches_off(self):
        self.add(id='no-snapshot')
        for managed in ({'state': 'disabled'}, {'state': 'enabled'}, {'state': 'partial'},
                        {'state': 'unknown', 'restoration_manifest': {'fixture': 'hash'}}):
            with self.subTest(managed=managed):
                cfg = load_config()
                cfg['clients'][0].pop('lifecycle_version', None)
                with patch.object(server.node_baseline, 'capture_node_baseline', return_value={'ok': True, 'managed': managed}), \
                        patch.object(server, 'run_node_script') as execute:
                    result = server.apply_node_proxy(cfg['clients'][0], 'off', cfg)
                self.assertNotEqual(result['returncode'], 0)
                self.assertEqual(result['managed_state'], 'unknown')
                self.assertNotIn('_node_baseline', cfg['clients'][0])
                execute.assert_not_called()

    def test_repeated_off_verifies_saved_restored_baseline_without_rewriting(self):
        node = self.active(id='repeat-off')
        observed_login = matching_login()
        for value in observed_login['proxy_variables'].values():
            value['fingerprint'] = 'fixture-login-fingerprint'
        verification = {'verified': True, 'status': 'restored', 'verification_scope': 'login_and_managed_files',
                        'checks': {'identity': True, 'managed_files': True}, 'observation': {
                            'login': observed_login}}
        with patch.object(server.node_baseline, 'capture_node_baseline') as capture, \
                patch.object(server.node_baseline, 'verify_node_baseline', return_value=verification) as verify, \
                patch.object(server, 'run_node_script', return_value=subprocess.CompletedProcess([], 0, '', '')) as execute:
            for _ in range(2):
                current = self.stored(node['id'])
                result = self.api('/api/node-switch', dict(self.selection(current), action='off'))
                self.assertEqual(result['managed_state'], 'disabled')
                self.assertTrue(result['verification']['restored_environment']['proxy_present'])
                self.assertTrue(result['verification']['restored_environment']['matches_selected_gateway'])
                self.assertEqual(result['verification']['restored_environment']['matched_gateway'],
                                 {'id': 'gw', 'host': 'proxy.invalid', 'port': 3128})
                self.assertNotIn('baseline-private', json.dumps(result))
                self.assertNotIn('fixture-login-fingerprint', json.dumps(result))
            self.assertEqual(execute.call_count, 1)
            self.assertEqual(verify.call_count, 2)
            capture.assert_not_called()
        saved = self.stored(node['id'])
        self.assertNotIn('_node_baseline', saved)
        self.assertIn('_node_restored_baseline', saved)
        self.assertNotIn('_node_restored_baseline', self.api('/api/config')['clients'][0])

    def test_failed_journal_or_baseline_read_prevents_configuration_write(self):
        node = self.add(id='journal-failure')
        for baseline in ({'ok': False}, {'ok': True, 'managed': {'state': 'disabled'}}):
            with self.subTest(baseline=baseline):
                cfg = load_config()
                target = cfg['clients'][0]
                with patch.object(server.node_baseline, 'capture_node_baseline', return_value=baseline), \
                        patch.object(server, 'save_config', side_effect=OSError('disk fixture failure')), \
                        patch.object(server, 'run_node_script') as execute:
                    result = server.apply_node_proxy(target, 'on', cfg)
                self.assertNotEqual(result['returncode'], 0)
                execute.assert_not_called()
        self.assertEqual(self.stored(node['id'])['managed_state'], 'unknown')


if __name__ == '__main__':
    unittest.main()
