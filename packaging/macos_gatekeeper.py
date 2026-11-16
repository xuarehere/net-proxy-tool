"""Record Gatekeeper policy and a simulated quarantined launch without changing host policy."""
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path


def report(root):
    if sys.platform != "darwin":
        return
    evidence = [f"## macOS download policy ({platform.machine()}, {platform.mac_ver()[0]})",
                "Runner policy and a simulated download marker on a separate extracted copy.",
                "This command-line launch does not exercise Finder or a physical user's security prompt.", "```text"]
    def record(name, command, env=None):
        try:
            result = subprocess.run(command, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=30, text=True, errors="replace")
            detail = result.stdout.strip()
            code = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            detail, code = str(exc), -1
        evidence.extend([f"{name} [exit {code}]", detail])
        return code

    with tempfile.TemporaryDirectory(prefix="gatekeeper ") as temp:
        base = Path(temp)
        copied = base / "package"
        shutil.copytree(root, copied, symlinks=True)
        executable = (copied / "runtime/bin/python3").resolve()
        record("spctl --status", ["spctl", "--status"])
        record("codesign runtime details", ["codesign", "-dv", "--verbose=2", str(executable)])
        record("assess extracted runtime", ["spctl", "-a", "-vv", "-t", "execute", str(executable)])
        marker = f"0083;{int(time.time()):x};Safari;{uuid.uuid4()}"
        if record("apply simulated quarantine to copy", ["xattr", "-r", "-w", "com.apple.quarantine",
                                                          marker, str(copied)]) == 0:
            record("read quarantine marker on executable", ["xattr", "-p", "com.apple.quarantine", str(executable)])
            record("assess quarantined runtime", ["spctl", "-a", "-vv", "-t", "execute", str(executable)])
            import socket
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = str(sock.getsockname()[1])
            env = dict(os.environ, NET_PROXY_CONFIG=str(base / "config.json"))
            command = str(copied / "net-proxy-tool")
            if record("first launch with marker", [command, port, "--no-browser"], env) == 0:
                record("stop same instance", [command, "--stop"], env)
    evidence.append("```")
    result = "\n".join(evidence) + "\n"
    print(result)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write(result)


if __name__ == "__main__":
    report(Path(sys.argv[1]).resolve())
