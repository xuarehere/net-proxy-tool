"""Exercise SSH -> Docker on an ephemeral Linux Actions runner using a second, loopback-only sshd."""
import getpass
import hashlib
import json
import os
import re
import socket
import subprocess
import tempfile
import time
import uuid
from contextlib import ExitStack
from pathlib import Path

from smoke import api
from test_node_requests import FIXTURE

ROOT = Path(__file__).resolve().parents[1]
BASE = "python:3.12-alpine"
USER_CONFIGS = [".curlrc", ".wgetrc", ".gitconfig", ".config/pip/pip.conf",
                ".net-proxy-switch.sh", ".bashrc", ".profile", ".bash_profile"]
SYSTEM_CONFIGS = ["/etc/curlrc", "/etc/gitconfig", "/etc/pip.conf", "/etc/apt/apt.conf.d/99net-proxy"]


def invoke(*args, check=True):
    return subprocess.run(args, check=check, stdout=subprocess.PIPE, text=True, timeout=300).stdout.strip()


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def host_snapshot():
    files = [Path.home() / name for name in USER_CONFIGS] + list(map(Path, SYSTEM_CONFIGS))
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None for p in files}


def container_snapshot(container):
    script = "import pathlib,hashlib,json; paths=" + repr(
        ["/root/" + name for name in USER_CONFIGS] + SYSTEM_CONFIGS)
    script += "; print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() " \
              "if pathlib.Path(p).is_file() else None for p in paths},sort_keys=True))"
    return invoke("docker", "exec", container, "python", "-c", script)


def run():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise RuntimeError("Run this sshd fixture on an ephemeral GitHub-hosted Linux runner.")
    prefix = "npt-host-" + uuid.uuid4().hex[:12]
    controller, target, sibling, fixture, network = [
        prefix + "-" + kind for kind in ("controller", "target", "sibling", "fixture", "net")]
    port, ssh_port = free_port(), free_port()
    while ssh_port == port:
        ssh_port = free_port()
    runner = getpass.getuser()
    original_host = host_snapshot()
    with tempfile.TemporaryDirectory() as tmp, ExitStack() as cleanup:
        directory = Path(tmp)
        invoke("docker", "build", "-t", prefix, str(ROOT))
        cleanup.callback(invoke, "docker", "image", "rm", prefix, check=False)
        node_image = prefix + "-node"
        with tempfile.TemporaryDirectory() as context:
            subprocess.run(["docker", "build", "-t", node_image, "-f", "-", context],
                           input=(ROOT / "packaging/ssh-target.Dockerfile").read_bytes(), check=True, timeout=300)
        cleanup.callback(invoke, "docker", "image", "rm", node_image, check=False)
        invoke("docker", "network", "create", "--internal", network)
        cleanup.callback(invoke, "docker", "network", "rm", network, check=False)
        fixture_script = directory / "fixture.py"
        fixture_script.write_text(FIXTURE, encoding="utf-8")
        invoke("docker", "run", "--name", fixture, "--network", network, "--network-alias", "fixture",
               "-v", str(fixture_script) + ":/fixture.py:ro", "-d", BASE, "python", "/fixture.py")
        cleanup.callback(invoke, "docker", "rm", "-f", fixture, check=False)
        for name in [target, sibling]:
            invoke("docker", "run", "--network", network, "--name", name, "-d", node_image, "sleep", "300")
            cleanup.callback(invoke, "docker", "rm", "-f", name, check=False)
            invoke("docker", "exec", name, "sh", "-ec", "printf 'silent\\n' > /root/.curlrc")
        original_sibling = container_snapshot(sibling)
        original_target = container_snapshot(target)
        invoke("docker", "run", "--network", "host", "--name", controller, "-e", "NET_PROXY_BIND=127.0.0.1",
               "-d", "--entrypoint", "python", prefix, "web/server.py", str(port))
        cleanup.callback(invoke, "docker", "rm", "-f", controller, check=False)
        invoke("docker", "exec", controller, "sh", "-ec",
               'mkdir -p ~/.ssh; chmod 700 ~/.ssh; ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519')
        pubkey = invoke("docker", "exec", controller, "sh", "-c", "cat ~/.ssh/id_ed25519.pub")
        authorized = directory / "authorized_keys"
        authorized.write_text("restrict " + pubkey + "\n", encoding="utf-8")
        host_key = directory / "host_key"
        invoke("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(host_key))
        pidfile = directory / "sshd.pid"
        conf = directory / "sshd_config"
        conf.write_text(f"""ListenAddress 127.0.0.1
Port {ssh_port}
HostKey {host_key}
PidFile {pidfile}
AuthorizedKeysFile {authorized}
StrictModes no
UsePAM yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
AllowUsers {runner}
DisableForwarding yes
""", encoding="utf-8")
        invoke("sudo", "-n", "install", "-d", "-m", "0755", "/run/sshd")
        log = directory / "sshd.log"
        log.touch(mode=0o600)
        invoke("sudo", "-n", "/usr/sbin/sshd", "-f", str(conf), "-E", str(log))
        for _ in range(30):
            if pidfile.exists():
                break
            time.sleep(0.1)
        ssh_pid = pidfile.read_text(encoding="ascii").strip()
        cleanup.callback(invoke, "sudo", "-n", "kill", ssh_pid, check=False)
        node = {"id": "host-test", "name": "docker via ssh", "host": "127.0.0.1", "ssh_host": "127.0.0.1",
                "ssh_user": runner, "port": ssh_port, "os_type": "docker", "access_mode": "docker_host",
                "container_name": target}
        for _ in range(20):
            try:
                if api(port, "/api/health")["status"] == "ok":
                    break
            except OSError:
                time.sleep(0.3)
        probe = ["docker", "exec", controller, "ssh", "-p", str(ssh_port),
                 "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
                 f"{runner}@127.0.0.1", f"id && command -v docker && docker inspect -f '{{{{.State.Running}}}}' {target}"]
        diagnostic = subprocess.run(probe, capture_output=True, text=True, timeout=15)
        if diagnostic.returncode != 0:
            details = diagnostic.stderr + log.read_text(encoding="utf-8", errors="replace")
            raise RuntimeError("SSH fixture preflight failed: " +
                               re.sub(r"SHA256:[a-zA-Z0-9+/=]+", "<key fingerprint>", details))
        print(diagnostic.stdout.strip())
        preflight = api(port, "/api/test-node-preflight", node)
        assert preflight.get("auth_ok") and preflight.get("success"), preflight
        assert api(port, "/api/gateways/add", {"name": "test", "host": "fixture", "port": 7890})["success"]
        node["bound_gateway_id"] = api(port, "/api/config")["gateways"][0]["id"]
        assert api(port, "/api/clients/add", node)["success"]
        expected_proxy_hits = 0
        payload = {"node_id": node["id"], "gateway_id": node["bound_gateway_id"],
                   "target_url": "http://fixture:8080/health"}
        for action, increase in [(None, 1), ("on", 2), ("off", 1)]:
            if action:
                result = api(port, "/api/node-switch", dict(payload, action=action))
                assert result.get("success"), result
            if action == "on":
                assert "fixture:7890" in invoke("docker", "exec", target, "cat", "/root/.curlrc")
            else:
                assert container_snapshot(target) == original_target
            result = api(port, "/api/node-test", payload)
            for mode in ("explicit_proxy", "ordinary_request"):
                request = result[mode]
                assert request["online"], result
                assert request["transport"] == "ssh_docker_exec", request
                assert request["stages"]["ssh"] == request["stages"]["docker_exec"] == "passed", request
            # A neighboring container performs its own ordinary request with no proxy changes.
            invoke("docker", "exec", sibling, "curl", "-fsS", "--max-time", "5", "http://fixture:8080/health")
            code = "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/hits').read().decode())"
            hits = json.loads(invoke("docker", "exec", fixture, "python", "-c", code))
            expected_proxy_hits += increase
            assert sum(hit["route"] == "proxy" for hit in hits) == expected_proxy_hits, hits
            assert container_snapshot(sibling) == original_sibling
            assert host_snapshot() == original_host
            print("SSH -> Docker", action or "before activation", "recorded proxy requests", expected_proxy_hits)
    print("Real SSH -> Docker requests, target restoration, and neighboring-container/host isolation passed.")


if __name__ == "__main__":
    run()
