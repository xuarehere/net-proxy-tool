"""Exercise real root/non-root login baselines in one disposable offline container."""
import argparse
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from web.node_baseline import capture_node_baseline, verify_node_baseline, wrap_login_script
from web.server import generate_provisioning_script


def main(image):
    name = 'npt-baseline-' + uuid.uuid4().hex[:12]
    target = {'id': 'isolated-root'}
    gateway = {'host': 'selected.invalid', 'port': 7890}
    proxy = 'http://selected.invalid:7890'

    def command(*args, **kwargs):
        return subprocess.run(args, capture_output=True, text=True, timeout=30, **kwargs)

    def runner(node, script, timeout=20):
        user = node.get('fixture_user', 'root')
        home = node.get('fixture_home', '/root' if user == 'root' else '/home/tester')
        result = subprocess.run(['docker', 'exec', '-i', '-u', user, '-e', 'HOME=' + home, name, 'sh'],
                                input=script.encode(), capture_output=True, timeout=timeout)
        return subprocess.CompletedProcess(result.args, result.returncode,
            result.stdout.decode('utf-8', 'replace'), result.stderr.decode('utf-8', 'replace'))

    def switch(node, action):
        return runner(node, wrap_login_script(generate_provisioning_script(proxy, 'localhost', action, owner=node['id'])))

    try:
        command('docker', 'run', '--rm', '--network', 'none', '--name', name, '-d',
                '--entrypoint', 'sleep', image, '600', check=True)
        for existing in ('', proxy, 'http://fixture-user:fixture-secret@original.invalid:3128'):
            # This is a fixture-owned system startup file; provisioning may not alter it.
            setup = "from pathlib import Path; import shlex; p=Path('/etc/profile.d/npt-fixture.sh'); " \
                    "p.write_text('export HTTP_PROXY='+shlex.quote(" + repr(existing) + ")+chr(10) if " + repr(existing) + " else '# empty fixture\\n')"
            command('docker', 'exec', name, 'python', '-c', setup, check=True)
            for node in (target, {'id': 'isolated-user', 'fixture_user': 'tester'}):
                baseline = capture_node_baseline(node, runner, gateway)
                assert baseline['ok'], baseline
                result = switch(node, 'on')
                assert result.returncode == 0, result.stderr
                active = capture_node_baseline(node, runner, gateway)
                assert active['managed']['state'] == 'enabled', active
                assert active['login']['proxy_variables']['HTTP_PROXY']['matches_selected_gateway'], active
                assert 'fixture-secret' not in str(active) + str(baseline)
                if node.get('fixture_user'):
                    # A different UID pointing at the same HOME cannot restore or take over.
                    other = {'id': 'different-account', 'fixture_home': '/home/tester'}
                    for action in ('on', 'off'):
                        refused = switch(other, action)
                        assert refused.returncode != 0
                    assert capture_node_baseline(node, runner, gateway)['files'] == active['files']
                result = switch(node, 'off')
                assert result.returncode == 0, result.stderr
                restored = verify_node_baseline(node, baseline, runner, gateway)
                assert restored['verified'], restored
        print('Offline Docker root/non-root: three login baselines, selected proxy activation, exact restoration, different-UID protection passed.')
    finally:
        command('docker', 'rm', '-f', name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node-image', required=True)
    main(parser.parse_args().node_image)
