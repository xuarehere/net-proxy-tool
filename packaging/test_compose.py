"""Verify an empty Compose volume, persistence, and real SSH provisioning on a disposable target."""
import os
import socket
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from smoke import api

ROOT = Path(__file__).resolve().parents[1]


def main():
    project = "npt-check-" + uuid.uuid4().hex[:10]
    target = project + "-target"
    image = project + ":ssh-target"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, NET_PROXY_HOST_PORT=str(port))

    def run(args, stdin=None, check=True):
        proc = subprocess.run(args, cwd=ROOT, env=env, input=stdin, stdout=subprocess.PIPE,
                              check=check, timeout=450)
        return proc.stdout.decode("utf-8").strip()

    compose = ["docker", "compose", "-p", project]
    app = compose + ["exec", "-T", "net-proxy-tool"]
    try:
        run(compose + ["up", "--build", "-d", "--wait", "--wait-timeout", "60"])
        assert api(port, "/api/config")["gateways"] == []
        # Use an empty build context. The disposable SSH daemon never mounts the host socket or SSH keys.
        with tempfile.TemporaryDirectory() as context:
            run(["docker", "build", "-t", image, "-f", "-", context],
                (ROOT / "packaging/ssh-target.Dockerfile").read_bytes())
        run(["docker", "run", "--name", target, "--network", project + "_default",
             "--network-alias", "fixture-ssh", "-d", image])
        run(app + ["sh", "-ec", 'mkdir -p ~/.ssh; chmod 700 ~/.ssh; ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519'])
        key = run(app + ["sh", "-c", "cat ~/.ssh/id_ed25519.pub"])
        for _ in range(30):
            if run(["docker", "exec", target, "sh", "-c", "test -s /etc/ssh/ssh_host_ed25519_key.pub && echo ready"], check=False) == "ready":
                break
            time.sleep(0.1)
        host_key = " ".join(run(["docker", "exec", target, "cat", "/etc/ssh/ssh_host_ed25519_key.pub"]).split()[:2])
        run(app + ["sh", "-ec", "umask 077; cat > ~/.ssh/known_hosts"], ("fixture-ssh " + host_key + "\n").encode())
        run(["docker", "exec", "-i", "-u", "tester", target, "sh", "-ec",
             'umask 077; cat > /home/tester/.ssh/authorized_keys; printf "silent\\n" > /home/tester/.curlrc'],
            (key + "\n").encode())
        # docker exec -u changes UID but may retain root HOME; use explicit paths for assertions.
        node = {"id": "test-ssh", "name": "SSH fixture", "host": "fixture-ssh", "port": 22,
                "ssh_user": "tester", "auth_type": "key", "os_type": "linux", "access_mode": "ssh"}
        for attempt in range(10):
            auth = api(port, "/api/test-node-preflight", node)
            if auth.get("auth_ok"):
                break
            time.sleep(0.5)
        assert auth.get("auth_ok"), auth
        gateway = {"name": "Test gateway", "host": "fixture-ssh", "port": 7890, "protocol": "http"}
        assert api(port, "/api/gateways/add", gateway)["success"]
        cfg = api(port, "/api/config")
        node["bound_gateway_id"] = cfg["gateways"][0]["id"]
        assert api(port, "/api/clients/add", node)["success"]
        for action in ("on", "off"):
            switched = api(port, "/api/node-switch", {"node_id": node["id"], "action": action})
            assert switched.get("success"), switched
            content = run(["docker", "exec", target, "cat", "/home/tester/.curlrc"])
            assert (("fixture-ssh:7890" in content) if action == "on" else (content == "silent")), content
        run(compose + ["up", "--force-recreate", "-d", "--wait", "--wait-timeout", "60"])
        after = api(port, "/api/config")
        assert after["gateways"][0]["id"] == node["bound_gateway_id"]
        assert any(client["id"] == node["id"] for client in after["clients"])
        print("Compose first run, SSH authentication, remote activation/restoration and volume persistence passed.")
    finally:
        run(["docker", "rm", "-f", target], check=False)
        run(compose + ["down", "-v", "--rmi", "local"], check=False)
        run(["docker", "image", "rm", image], check=False)


if __name__ == "__main__":
    main()
