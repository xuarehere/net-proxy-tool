"""Node selection and target-side request regressions using isolated local services."""
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from sdk.config import load_config, save_config
from web import server


class NodeRequestTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        env = patch.dict(os.environ, NET_PROXY_CONFIG=str(Path(temp.name) / 'config.json'),
                         CURL_HOME=temp.name)
        env.start()
        self.addCleanup(env.stop)
        self.web = self.listen(server.ProxyConsoleHandler)
        cfg = load_config()
        cfg['gateways'] = [{'id': 'first', 'host': '127.0.0.1', 'port': 9001},
                           {'id': 'second', 'host': '127.0.0.1', 'port': 9002}]
        cfg['active_gateway_id'] = 'first'
        cfg['clients'] = [{'id': 'node', 'name': 'fixture', 'host': '127.0.0.1',
                           'bound_gateway_id': 'first', 'is_proxy_enabled': False}]
        save_config(cfg)

    def listen(self, handler):
        instance = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        worker = threading.Thread(target=instance.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(instance.server_close)
        self.addCleanup(worker.join, 2)
        self.addCleanup(instance.shutdown)
        return instance

    def api(self, path, body):
        conn = http.client.HTTPConnection(*self.web.server_address, timeout=20)
        try:
            conn.request('POST', path, json.dumps(body), {'Content-Type': 'application/json'})
            response = conn.getresponse()
            return response.status, json.load(response)
        finally:
            conn.close()

    def test_binding_readback_and_stale_actions(self):
        status, body = self.api('/api/clients/update', {'id': 'node', 'bound_gateway_id': 'second',
                                                     'binding_revision': 0})
        self.assertEqual(status, 200)
        self.assertEqual(body['client']['bound_gateway_id'], 'second')
        self.assertEqual(load_config()['clients'][0]['binding_revision'], 1)
        with patch.object(server, 'apply_node_proxy') as apply, patch.object(server, 'check_node_http') as check:
            for path in ('/api/node-switch', '/api/node-test'):
                status, result = self.api(path, {'node_id': 'node', 'gateway_id': 'first', 'action': 'on'})
                self.assertEqual(status, 409, result)
                status, result = self.api(path, {'node_id': 'node', 'gateway_id': 'second',
                                                'binding_revision': 0, 'action': 'on'})
                self.assertEqual(status, 409, result)
            apply.assert_not_called()
            check.assert_not_called()
        self.assertEqual(self.api('/api/clients/update', {'id': 'node', 'bound_gateway_id': 'missing'})[0], 400)
        self.assertEqual(self.api('/api/gateways/delete', {'id': 'second'})[0], 409)
        self.assertEqual(load_config()['clients'][0]['bound_gateway_id'], 'second')

    def test_binding_change_during_request_is_invalidated(self):
        def changed(*args, **kwargs):
            cfg = load_config()
            cfg['clients'][0]['bound_gateway_id'] = 'second'
            save_config(cfg)
            return {'online': True, 'status_line': 'HTTP 200'}
        with patch.object(server, 'check_node_http', side_effect=changed):
            self.assertEqual(self.api('/api/node-test', {'node_id': 'node', 'gateway_id': 'first'})[0], 409)

    def test_remote_execution_stages_and_explicit_proxy_flags(self):
        target = {'id': 'remote', 'host': 'fixture.invalid', 'ssh_user': 'tester', 'port': 2222,
                  'container_name': 'fixture', 'access_mode': 'docker_host'}
        gateway = {'id': 'first', 'host': 'proxy.invalid', 'port': 3128}
        complete = subprocess.CompletedProcess([], 0,
                    'NPT_SSH_READY\nNPT_EXEC_READY\nNPT_HTTP_RESULT:204|192.0.2.10|0.002\n', '')
        with patch.object(server, 'ssh_with_script', return_value=complete) as remote:
            result = server.check_node_http(target, gateway, 'http://origin.invalid/ok')
            self.assertTrue(result['online'])
            self.assertEqual(result['stages'], dict(ssh='passed', docker_exec='passed', curl='passed',
                                                   tcp='passed', http='passed'))
            command, script, _ = remote.call_args.args
            self.assertIn("printf 'NPT_SSH_READY", command[-1])
            self.assertIn('--proxy http://proxy.invalid:3128', script)
            self.assertIn("--noproxy ''", script)
            self.assertIn('curl -q ', script)
            self.assertIn('-u 0', command[-1])
        denied = subprocess.CompletedProcess([], 255, '', 'authentication refused')
        with patch.object(server, 'ssh_with_script', return_value=denied):
            result = server.check_node_http(target, gateway)
            self.assertEqual(result['stages']['ssh'], 'failed')
            self.assertFalse(result['online'])
            self.assertEqual(result['stages']['http'], 'not_reached')

    @unittest.skipUnless(shutil.which('curl.exe' if os.name == 'nt' else 'curl'), 'requires curl')
    def test_local_explicit_proxy_and_ordinary_request_take_distinct_paths(self):
        proxy_hits, origin_hits = [], []
        class Origin(BaseHTTPRequestHandler):
            def do_GET(self):
                origin_hits.append(self.path)
                self.send_response(204)
                self.end_headers()
            def log_message(self, *args):
                pass
        class Proxy(Origin):
            def do_GET(self):
                proxy_hits.append(self.path)
                self.send_response(200)
                self.end_headers()
        origin, proxy = self.listen(Origin), self.listen(Proxy)
        cfg = load_config()
        cfg['gateways'][0]['port'] = proxy.server_port
        save_config(cfg)
        env = {k: '' for k in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy',
                              'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY')}
        url = f'http://127.0.0.1:{origin.server_port}/fixed-health'
        with patch.dict(os.environ, env):
            status, result = self.api('/api/node-test', {'node_id': 'node', 'gateway_id': 'first',
                                                        'target_url': url})
        self.assertEqual(status, 200, result)
        self.assertEqual(result['explicit_proxy']['code'], 200)
        self.assertEqual(result['ordinary_request']['code'], 204)
        self.assertEqual(proxy_hits, [url])
        self.assertEqual(origin_hits, ['/fixed-health'])
        self.assertEqual(result['explicit_proxy']['transport'], 'local')
        self.assertEqual(result['ordinary_request']['request_mode'], 'ordinary_request')


if __name__ == '__main__':
    unittest.main()
