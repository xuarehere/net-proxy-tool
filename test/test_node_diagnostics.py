"""Observe real curl's destination/redirects without contacting an external service."""
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from web import server


class RecordingProxy(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.hits.append(self.path)
        self.server.auth.append(bool(self.headers.get('Authorization')))
        suffix = self.path.rsplit('/', 1)[-1]
        code, location = 200, None
        if suffix == 'start':
            code, location = 302, 'http://fixture.invalid/final'
        elif suffix == 'credentials':
            code, location = 302, 'http://not-a-real-user:not-a-real-secret@fixture.invalid/final'
        elif suffix == 'file':
            code, location = 302, 'file:///does-not-exist'
        elif suffix == 'loop':
            code, location = 302, '/loop'
        elif suffix.startswith('hop'):
            code, location = 302, '/hop' + str(int(suffix[3:]) + 1)
        elif suffix == 'denied':
            code = 403
        self.send_response(code)
        self.send_header('Set-Cookie', 'fixture=synthetic-response-secret')
        if location:
            self.send_header('Location', location)
        self.end_headers()

    def do_CONNECT(self):
        self.server.hits.append('CONNECT ' + self.path)
        self.send_response(407)
        self.end_headers()


@unittest.skipUnless(shutil.which('curl.exe' if os.name == 'nt' else 'curl'), 'requires curl')
class NodeDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.home = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        env = {name: '' for name in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy',
                                     'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'XDG_CONFIG_HOME')}
        env['CURL_HOME'] = str(self.home)
        self.stack.enter_context(patch.dict(os.environ, env))
        self.proxy = self.stack.enter_context(ThreadingHTTPServer(('127.0.0.1', 0), RecordingProxy))
        self.proxy.hits = []
        self.proxy.auth = []
        worker = threading.Thread(target=self.proxy.serve_forever, daemon=True)
        worker.start()
        self.stack.callback(worker.join, 2)
        self.stack.callback(self.proxy.shutdown)
        self.node = {'id': 'local', 'host': '127.0.0.1', 'access_mode': 'local', 'identity_version': 1}
        self.gateway = {'id': 'selected', 'host': '127.0.0.1', 'port': self.proxy.server_port}

    def probe(self, suffix):
        return server.check_node_http(self.node, self.gateway, 'http://fixture.invalid/' + suffix)

    def test_redirect_keeps_selected_proxy_and_reports_first_final_peer(self):
        result = self.probe('start')
        self.assertTrue(result['online'], result)
        self.assertEqual((result['first_status'], result['final_status']), (302, 200))
        self.assertEqual(result['peer'], {'ip': '127.0.0.1', 'port': self.proxy.server_port})
        self.assertEqual(result['proxy_evidence']['status'], 'selected_proxy')
        self.assertEqual(result['exit_evidence']['status'], 'not_checked')
        self.assertIsNone(result['business_ok'])
        self.assertEqual(result['business_auth']['status'], 'not_checked')
        self.assertEqual(self.proxy.hits, ['http://fixture.invalid/start', 'http://fixture.invalid/final'])
        self.assertEqual(result['execution_identity']['curl_home'], str(self.home))

    def test_rejects_unsafe_redirects_and_bounds_loops(self):
        self.proxy.hits.clear()
        credentials = self.probe('credentials')
        self.assertEqual(credentials['error_type'], 'redirect_credentials', credentials)
        self.assertFalse(credentials['online'])
        self.assertEqual(self.proxy.auth, [False])
        self.assertEqual(len(self.proxy.hits), 1)
        for suffix in ('file',):
            self.proxy.hits.clear()
            result = self.probe(suffix)
            self.assertFalse(result['online'])
            self.assertEqual(result['error_type'], 'redirect_policy', result)
            self.assertEqual(len(self.proxy.hits), 1)
        self.assertEqual(self.probe('loop')['error_type'], 'redirect_limit')
        result = self.probe('hop0')
        self.assertEqual(result['error_type'], 'redirect_limit')
        self.assertEqual(len(result['hops']), 6)

    def test_native_cross_host_redirect_preserves_proxy_but_does_not_forward_account_auth(self):
        (self.home / '.curlrc').write_text(
            f'proxy = "http://127.0.0.1:{self.proxy.server_port}"\n'
            'user = "synthetic-user:synthetic-password"\nbasic\nlocation-trusted\n', encoding='utf-8')
        result = server.check_node_http(self.node, target_url='http://first.invalid/start')
        self.assertTrue(result['online'], result)
        self.assertEqual((result['first_status'], result['final_status']), (302, 200))
        self.assertEqual(self.proxy.hits, ['http://first.invalid/start', 'http://fixture.invalid/final'])
        self.assertEqual(self.proxy.auth, [True, False])
        self.assertEqual(result['hops'][0]['peer'], {'ip': None, 'port': None})
        self.assertEqual(result['hops'][-1]['peer']['port'], self.proxy.server_port)
        self.assertNotIn('synthetic-password', repr(result))
        self.assertNotIn('synthetic-response-secret', repr(result))

    def test_missing_gateway_keeps_ordinary_request_result(self):
        with patch.object(server, 'check_node_http', return_value={'online': True, 'status_line': 'HTTP 200'}):
            result = server.check_node_requests(self.node, None, 'http://fixture.invalid/final')
        self.assertTrue(result['ordinary_request']['online'])
        self.assertFalse(result['explicit_proxy']['online'])
        self.assertIsNone(result['gateway_id'])
        self.assertFalse(result['success'])

    def test_connect_denial_is_not_an_origin_http_response(self):
        result = server.check_node_http(self.node, self.gateway, 'https://fixture.invalid/')
        self.assertFalse(result['online'])
        self.assertEqual(result['connect_status'], 407)
        self.assertEqual(result['error_type'], 'proxy_auth')
        self.assertIsNone(result['first_status'])
        self.assertIsNone(result['final_status'])
        self.assertEqual(result['stages']['tls'], 'not_reached')
        self.assertEqual(self.proxy.hits, ['CONNECT fixture.invalid:443'])

    def test_ordinary_request_uses_account_curl_home_and_compares_peers(self):
        path = self.home / '.curlrc'
        original = f'proxy = "http://127.0.0.1:{self.proxy.server_port}"\n'.encode()
        path.write_bytes(original)
        result = server.check_node_requests(self.node, self.gateway, 'http://fixture.invalid/final')
        self.assertTrue(result['ordinary_request']['online'], result)
        self.assertEqual(result['ordinary_request']['execution_identity']['curl_config'], str(path))
        self.assertEqual(result['ordinary_request']['proxy_evidence']['status'], 'matches_explicit_peer')
        self.assertEqual(path.read_bytes(), original)
        denied = self.probe('denied')
        self.assertFalse(denied['business_ok'])
        self.assertEqual(denied['business_auth']['status'], 'denied')
        self.assertEqual(denied['proxy_evidence']['status'], 'selected_proxy')

    def test_tls_failure_and_execution_identity_are_not_hidden_by_tcp(self):
        metadata = ('NPT_SSH_READY\nNPT_EXEC_READY\nNPT_META_UID:1001\nNPT_META_USER:fixture\n'
                    'NPT_META_HOME:/fixture/home\nNPT_META_CURL_CONFIG:/fixture/xdg/curlrc\n'
                    'NPT_CODE:000\nNPT_IP:192.0.2.1\nNPT_PORT:3128\nNPT_CONNECT:200\nNPT_VERIFY:20\n')
        complete = subprocess.CompletedProcess([], 60, metadata, 'certificate rejected')
        target = {'id': 'ssh', 'host': 'fixture.invalid', 'port': 2222, 'ssh_user': 'fixture'}
        with patch.object(server, 'run_node_script', return_value=complete):
            result = server.check_node_http(target, {'host': 'proxy.invalid', 'port': 3128}, 'https://fixture.invalid/')
        self.assertTrue(result['auth_ok'])
        self.assertEqual(result['execution_identity']['uid'], '1001')
        self.assertEqual(result['execution_identity']['home'], '/fixture/home')
        self.assertEqual(result['error_type'], 'tls_certificate')
        self.assertEqual(result['stages']['tcp'], 'passed')
        self.assertEqual(result['stages']['tls'], 'failed')
        self.assertFalse(result['online'])


if __name__ == '__main__':
    unittest.main()
