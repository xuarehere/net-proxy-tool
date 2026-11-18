"""Local-only SSH integration with a recording proxy, origin, and disposable identities.

Requires already available images. No image pull or package installation is performed.
The node image must contain sshd, curl, useradd or adduser, passwd and ssh-keygen.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = r'''
import http.client, json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
hits = []
class Origin(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/hits':
            body = json.dumps(hits).encode()
        else:
            hits.append({'route':'origin', 'path':self.path})
            body = b'fixture healthy'
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*args): pass
class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != 'http://fixture:8080/health':
            self.send_error(400)
            return
        hits.append({'route':'proxy', 'path':self.path})
        conn = http.client.HTTPConnection('127.0.0.1',8080)
        conn.request('GET','/health')
        resp = conn.getresponse()
        data = resp.read()
        self.send_response(resp.status)
        self.end_headers()
        self.wfile.write(data)
        conn.close()
    def log_message(self,*args): pass
threading.Thread(target=ThreadingHTTPServer(('0.0.0.0',7890),Proxy).serve_forever,daemon=True).start()
ThreadingHTTPServer(('0.0.0.0',8080),Origin).serve_forever()
'''


def main(node_image, controller_image):
    prefix = 'npt-requests-' + uuid.uuid4().hex[:10]
    network, controller, target, fixture = [prefix + '-' + role for role in ('net','controller','node','fixture')]
    def run(*args, data=None, check=True):
        result = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=check, timeout=60)
        return result.stdout.decode('utf-8').strip()
    for image in (node_image, controller_image, 'python:3.12-alpine'):
        run('docker', 'image', 'inspect', image, '--format', '{{.Id}}')
    port = 8899
    def api(port, path, payload=None, expected_status=200):
        script = ("import http.client,json,sys; path,payload,expected=json.load(sys.stdin); "
                  "c=http.client.HTTPConnection('127.0.0.1',8899,timeout=35); "
                  "c.request('POST' if payload is not None else 'GET',path,"
                  "json.dumps(payload) if payload is not None else None,{'Content-Type':'application/json'}); "
                  "r=c.getresponse(); data=r.read().decode(); assert r.status==expected,(r.status,data); print(data)")
        return json.loads(run('docker','exec','-i',controller,'python','-c',script,
                              data=json.dumps([path,payload,expected_status]).encode()))
    with tempfile.TemporaryDirectory(prefix='npt-fixture-') as tmp:
        fixture_script = Path(tmp) / 'fixture.py'
        fixture_script.write_text(FIXTURE, encoding='utf-8')
        try:
            run('docker','network','create','--internal',network)
            run('docker','run','--rm','-d','--name',fixture,'--network',network,'--network-alias','fixture',
                '-v',str(fixture_script)+':/fixture.py:ro','python:3.12-alpine','python','/fixture.py')
            run('docker','run','--rm','-d','--name',controller,'--network',network,
                '-v',str(ROOT)+':/code:ro',
                '-w','/code','-e','NET_PROXY_CONFIG=/tmp/config.json','-e','NET_PROXY_BIND=0.0.0.0',
                '--entrypoint','python',controller_image,'web/server.py','8899')
            run('docker','exec',controller,'sh','-ec',
                'mkdir -p ~/.ssh; chmod 700 ~/.ssh; ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519')
            public_key = run('docker','exec',controller,'sh','-c','cat ~/.ssh/id_ed25519.pub')
            node_start = (
                'if command -v useradd >/dev/null; then useradd -m -d /tmp/npt-user -s /bin/sh npttester; '
                'else adduser -D -h /tmp/npt-user -s /bin/sh npttester; fi && passwd -d npttester >/dev/null && '
                'mkdir -p /tmp/npt-user/.ssh /run/sshd && chmod 700 /tmp/npt-user/.ssh && '
                'chown npttester:npttester /tmp/npt-user/.ssh && '
                'ssh-keygen -q -t ed25519 -N "" -f /tmp/npt-host-key && '
                'exec /usr/sbin/sshd -D -e -f /dev/null -h /tmp/npt-host-key '
                '-o PasswordAuthentication=no -o KbdInteractiveAuthentication=no '
                '-o PermitUserEnvironment=yes '
                '-o AuthorizedKeysFile=/tmp/npt-user/.ssh/authorized_keys -o AllowUsers=npttester')
            run('docker','run','--rm','-d','--name',target,'--network',network,'--network-alias','node',
                '--entrypoint','sh',node_image,'-ec',node_start)
            for _ in range(30):
                if run('docker','exec',target,'sh','-c','test -s /tmp/npt-host-key.pub && echo ready',check=False) == 'ready':
                    break
                time.sleep(0.2)
            run('docker','exec','-i','-u','npttester',target,'sh','-ec',
                'umask 077; cat > /tmp/npt-user/.ssh/authorized_keys; printf "silent\\n" > /tmp/npt-user/.curlrc',
                data=(public_key+'\n').encode())
            host_key = ' '.join(run('docker','exec',target,'cat','/tmp/npt-host-key.pub').split()[:2])
            run('docker','exec','-i',controller,'sh','-ec','umask 077; cat > ~/.ssh/known_hosts',
                data=('node ' + host_key + '\n').encode())
            run('docker','exec','-u','npttester',target,'sh','-ec',
                'mkdir -p "/tmp/npt-user/curl config" "/tmp/npt-user/xdg config"; '
                'printf "silent\\n" > "/tmp/npt-user/curl config/.curlrc"; '
                'printf "show-error\\n" > "/tmp/npt-user/xdg config/curlrc"; '
                'printf "CURL_HOME=/tmp/npt-user/curl config\\nXDG_CONFIG_HOME=/tmp/npt-user/xdg config\\n" '
                '> /tmp/npt-user/.ssh/environment')
            for _ in range(30):
                try:
                    if api(port,'/api/health')['status']=='ok': break
                except (OSError,ValueError,subprocess.CalledProcessError): time.sleep(0.2)
            else:
                raise RuntimeError(run('docker','logs',controller))
            gateway = api(port,'/api/gateways/add',{'name':'recording fixture','host':'fixture','port':7890})['gateway']
            node = {'id':'ssh-test','name':'isolated SSH target','host':'node','port':22,'ssh_user':'npttester',
                    'auth_type':'key','access_mode':'ssh','os_type':'linux','bound_gateway_id':gateway['id']}
            assert api(port,'/api/clients/add',node)['success']
            assert api(port,'/api/test-node-preflight',node)['auth_ok']
            def hits():
                code = "import urllib.request; print(urllib.request.urlopen('http://fixture:8080/hits').read().decode())"
                return json.loads(run('docker','exec',fixture,'python','-c',code))
            payload = {'node_id':'ssh-test','gateway_id':gateway['id'],'target_url':'http://fixture:8080/health'}
            expected_proxy_hits = 0
            for context in ('CURL_HOME', 'XDG_CONFIG_HOME'):
                for action, expected_increment in ((None,1),('on',2),('off',1)):
                    if context == 'CURL_HOME' and action == 'off':
                        # Restoration must use the recorded path even if a later login changes its environment.
                        run('docker','exec','-u','npttester',target,'sh','-ec',
                            'printf "XDG_CONFIG_HOME=/tmp/npt-user/xdg config\\n" > /tmp/npt-user/.ssh/environment')
                        changed = api(port,'/api/node-switch',dict(payload,action='on'),expected_status=502)
                        assert not changed['success']
                    if action:
                        assert api(port,'/api/node-switch',dict(payload,action=action))['success']
                    result = api(port,'/api/node-test',payload)
                    assert result['explicit_proxy']['online'], result
                    assert result['ordinary_request']['online'], result
                    assert result['explicit_proxy']['stages']['ssh'] == 'passed', result
                    assert result['explicit_proxy']['peer']['port'] == 7890, result
                    assert result['ordinary_request']['proxy_evidence']['status'] == (
                        'matches_explicit_peer' if action == 'on' else 'different_peer'), result
                    identity = result['ordinary_request']['execution_identity']
                    assert identity['user'] == 'npttester' and identity['home'] == '/tmp/npt-user', identity
                    selected = ('/tmp/npt-user/curl config/.curlrc' if context == 'CURL_HOME' and action != 'off'
                                else '/tmp/npt-user/xdg config/curlrc')
                    assert identity['curl_config'] == selected, identity
                    expected_proxy_hits += expected_increment
                    seen = hits()
                    assert sum(h['route']=='proxy' for h in seen) == expected_proxy_hits, seen
                    print('SSH node', context, action or 'before activation', 'proxy request count', expected_proxy_hits)
            restored = run('docker','exec',target,'cat','/tmp/npt-user/.curlrc')
            assert restored == 'silent', restored
            assert run('docker','exec',target,'cat','/tmp/npt-user/curl config/.curlrc') == 'silent'
            assert run('docker','exec',target,'cat','/tmp/npt-user/xdg config/curlrc') == 'show-error'
            assert run('docker','exec',target,'sh','-c','test ! -e /tmp/npt-user/.net-proxy-switch.sh && echo restored')=='restored'
            print('Real SSH GETs used the selected proxy and normal node configuration, and off restored the original file.')
        finally:
            for name in (controller,target,fixture):
                run('docker','rm','-f',name,check=False)
            run('docker','network','rm',network,check=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node-image',required=True)
    parser.add_argument('--controller-image',default='net-proxy-tool-net-proxy-tool:latest')
    args=parser.parse_args()
    main(args.node_image,args.controller_image)
