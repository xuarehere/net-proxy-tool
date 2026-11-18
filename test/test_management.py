"""Management lifecycle checks with disposable configuration and no external node access."""
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from sdk.config import load_config, save_config
from web import server

ROOT = Path(__file__).resolve().parents[1]


class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='npt-management-')))
        self.path = self.directory / 'config.json'
        self.stack.enter_context(patch.dict(os.environ, NET_PROXY_CONFIG=str(self.path)))
        self.web = self.listen(server.ProxyConsoleHandler)

    def listen(self, handler):
        httpd = self.stack.enter_context(ThreadingHTTPServer(('127.0.0.1', 0), handler))
        worker = threading.Thread(target=httpd.serve_forever, daemon=True)
        worker.start()
        self.stack.callback(worker.join, 3)
        self.stack.callback(httpd.shutdown)
        return httpd

    def api(self, path, data=None, status=200, port=None):
        connection = http.client.HTTPConnection('127.0.0.1', port or self.web.server_port, timeout=15)
        try:
            connection.request('GET' if data is None else 'POST', path,
                               None if data is None else json.dumps(data), {'Content-Type': 'application/json'})
            response = connection.getresponse()
            body = json.load(response)
            self.assertEqual(response.status, status, body)
            return body
        finally:
            connection.close()

    def gateway(self, id):
        return self.api('/api/gateways/add', {'id': id, 'name': id, 'host': '127.0.0.1', 'port': 3128})['gateway']

    def test_gateway_lifecycle_and_rejected_update_are_persisted(self):
        self.gateway('first')
        self.gateway('second')
        self.api('/api/gateways/update', {'id': 'second', 'name': 'renamed', 'port': 3210})
        self.api('/api/gateways/update', {'id': 'second', 'port': 99999}, status=400)
        cfg = self.api('/api/config')
        self.assertEqual([(g['id'], g['port']) for g in cfg['gateways']], [('first', 3128), ('second', 3210)])
        self.assertEqual(cfg['gateways'][1]['name'], 'renamed')
        self.api('/api/gateways/delete', {'id': 'first'}, status=400)
        self.api('/api/set-active-gateway', {'gateway_id': 'second'})
        self.api('/api/gateways/delete', {'id': 'first'})
        self.api('/api/gateways/delete', {'id': 'first'}, status=404)
        self.assertEqual(load_config()['active_gateway_id'], 'second')
        self.assertEqual([g['id'] for g in load_config()['gateways']], ['second'])

    def test_batch_partial_failures_keep_state_and_have_per_node_audit(self):
        self.gateway('gateway')
        for id in ('ok', 'refused', 'exception'):
            self.api('/api/clients/add', {'id': id, 'name': id, 'host': 'fixture.invalid',
                                        'bound_gateway_id': 'gateway'})
        dispatched = []
        def dispatch(target, action, config):
            dispatched.append((target['id'], action, target['bound_gateway_id']))
            if target['id'] == 'exception':
                raise OSError('isolated transport error')
            return {'returncode': 0 if target['id'] == 'ok' else 1, 'stderr': 'isolated refusal'}
        with patch.object(server, 'apply_node_proxy', side_effect=dispatch):
            enabled = self.api('/api/nodes/batch-switch', {'action': 'on'})
            self.assertEqual((enabled['success'], enabled['success_count'], enabled['total']), (False, 1, 3))
            states = {c['id']: c['is_proxy_enabled'] for c in load_config()['clients']}
            self.assertEqual(states, {'ok': True, 'refused': False, 'exception': False})
            disabled = self.api('/api/nodes/batch-switch', {'action': 'off'})
            self.assertEqual(disabled['success_count'], 1)
        self.assertEqual(dispatched, [(id, action, 'gateway') for action in ('on', 'off')
                                      for id in ('ok', 'refused', 'exception')])
        self.assertTrue(all(not c['is_proxy_enabled'] for c in load_config()['clients']))
        logs = self.api('/api/audit-logs')['logs']
        observed = {(row['action'], row['node_id']): row['status'] for row in logs}
        for action in ('batch_on', 'batch_off'):
            self.assertEqual({id: observed[(action, id)] for id in ('ok', 'refused', 'exception')},
                             {'ok': 'success', 'refused': 'failed', 'exception': 'error'})

    def test_legacy_fields_survive_updates_and_are_not_returned(self):
        self.gateway('gateway')
        cfg = load_config()
        credentials = {name: 'synthetic-fixture-' + name
                       for name in ('ssh_pass', 'password', 'token', 'api_key', 'private_key')}
        cfg['clients'] = [dict(id='legacy', name='old', host='fixture.invalid',
                               bound_gateway_id='gateway', auth_type='password',
                               unknown_extension={'keep': True}, **credentials)]
        cfg['legacy_extension'] = {'keep': 'retained'}
        save_config(cfg)
        response = self.api('/api/clients/update', {'id': 'legacy', 'name': 'new', 'ssh_pass': ''})
        public = json.dumps([response, self.api('/api/config')])
        self.assertTrue(all(value not in public for value in credentials.values()))
        saved = load_config()
        self.assertEqual({name: saved['clients'][0][name] for name in credentials}, credentials)
        self.assertEqual(saved['clients'][0]['unknown_extension'], {'keep': True})
        self.assertEqual(saved['legacy_extension'], {'keep': 'retained'})

    def test_refused_preflight_never_attempts_an_identity(self):
        with socket.socket() as closed:
            closed.bind(('127.0.0.1', 0))
            port = closed.getsockname()[1]
        with patch.object(server, 'run_remote_ssh_script') as ssh:
            result = self.api('/api/test-node-preflight', {'host': '127.0.0.1', 'port': port,
                                                         'ssh_user': 'synthetic_fixture'})
            self.assertFalse(result['success'])
            self.assertFalse(result['tcp_ok'])
            ssh.assert_not_called()

    def test_missing_saved_binding_never_falls_back_to_default_gateway(self):
        self.gateway('default')
        cfg = load_config()
        cfg['clients'] = [{'id': 'legacy', 'name': 'legacy', 'host': 'fixture.invalid',
                           'bound_gateway_id': 'removed', 'is_proxy_enabled': False}]
        save_config(cfg)
        with patch.object(server, 'run_remote_ssh_script') as ssh:
            self.api('/api/node-switch', {'node_id': 'legacy', 'gateway_id': 'removed', 'action': 'on'}, status=400)
            ssh.assert_not_called()
        with patch.object(server, 'check_node_http', return_value={'online': False, 'status_line': 'not executed'}) as probe:
            result = self.api('/api/node-test', {'node_id': 'legacy', 'gateway_id': 'removed'})
            self.assertFalse(result['success'])
            self.assertIsNone(result['gateway_id'])
            self.assertFalse(result['explicit_proxy']['online'])
            self.assertEqual(probe.call_count, 1)
            self.assertNotIn('gateway', probe.call_args.kwargs)
        self.assertFalse(load_config()['clients'][0]['is_proxy_enabled'])

    def test_restart_retains_binding_credentials_and_custom_diagnostic_target(self):
        requests = []
        class Proxy(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(200)
                self.end_headers()
            def log_message(self, *args):
                pass
        proxy = self.listen(Proxy)
        cfg = load_config()
        cfg['gateways'] = [{'id': 'proxy', 'name': 'recording', 'host': '127.0.0.1', 'port': proxy.server_port}]
        cfg['active_gateway_id'] = 'proxy'
        cfg['clients'] = [{'id': 'legacy', 'name': 'legacy', 'host': 'fixture.invalid', 'bound_gateway_id': 'proxy',
                           'binding_revision': 3, 'ssh_pass': 'synthetic-restart-fixture', 'is_proxy_enabled': True}]
        url = 'http://diagnostic-fixture.invalid/controlled'
        cfg['diagnostic_targets'] = {'Private fixture': {'url': url, 'desc': 'local recording proxy'}}
        save_config(cfg)
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        def launcher(*args):
            result = subprocess.run([sys.executable, str(ROOT / 'launcher.py'), *args],
                                    cwd=self.directory, capture_output=True, text=True, encoding='utf-8', timeout=25)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.stack.callback(launcher, '--stop')
        for _ in range(2):
            launcher(str(port), '--no-browser')
            current = self.api('/api/config', port=port)
            node = current['clients'][0]
            self.assertEqual((node['bound_gateway_id'], node['binding_revision'], node['is_proxy_enabled']),
                             ('proxy', 3, True))
            self.assertNotIn('ssh_pass', node)
            self.assertEqual(load_config()['clients'][0]['ssh_pass'], 'synthetic-restart-fixture')
            self.assertEqual(current['diagnostic_targets'], cfg['diagnostic_targets'])
            self.assertEqual(requests, [])
            launcher('--stop')
        # The same API used by the advanced wizard consumes the configured targets.
        result = self.api('/api/status?gateway_id=proxy')
        self.assertEqual(requests, [url])
        self.assertEqual(result['targets'][0]['name'], 'Private fixture')
        self.assertEqual(result['targets'][0]['code'], 200)
        self.assertTrue(result['gateway']['path_verified'])


if __name__ == '__main__':
    unittest.main()
