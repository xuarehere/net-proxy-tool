"""Secret-free OpenSSH askpass bridge for the controller's current Python runtime."""
from contextlib import contextmanager
import os
from pathlib import Path
import sys
import tempfile


@contextmanager
def password_environment(password):
    """Keep credentials only in this SSH child's environment, never on disk/argv."""
    if not isinstance(password, str) or not password or any(c in password for c in "\r\n\0"):
        raise ValueError("请填写此节点的有效 SSH 密码（不能包含换行或 NUL）")
    windows = os.name == "nt"
    # Both trampolines contain only variable names; paths and password are not interpolated.
    trampoline = ('@echo off\r\n@setlocal DisableDelayedExpansion\r\n'
                  '"%NET_PROXY_ASKPASS_PYTHON%" "%NET_PROXY_ASKPASS_SCRIPT%"\r\n') if windows else (
                  '#!/bin/sh\nexec "$NET_PROXY_ASKPASS_PYTHON" "$NET_PROXY_ASKPASS_SCRIPT"\n')
    with tempfile.TemporaryDirectory(prefix="npt-askpass-") as directory:
        helper = Path(directory) / (Path(directory).name + (".bat" if windows else ".sh"))
        helper.write_bytes(trampoline.encode("ascii"))
        helper.chmod(0o700)
        env = os.environ.copy()
        env.update(NET_PROXY_SSH_PASSWORD=password, NET_PROXY_ASKPASS_PYTHON=sys.executable,
                   NET_PROXY_ASKPASS_SCRIPT=str(Path(__file__).resolve()),
                   SSH_ASKPASS=helper.name if windows else str(helper),
                   SSH_ASKPASS_REQUIRE="force", DISPLAY="net-proxy-tool")
        if windows:
            # Windows OpenSSH 9.x misdecodes non-ASCII SSH_ASKPASS absolute paths.
            # A unique ASCII basename is resolved via the child's Unicode PATH.
            env["PATH"] = str(helper.parent) + os.pathsep + env.get("PATH", "")
        try:
            yield env
        finally:
            env.pop("NET_PROXY_SSH_PASSWORD", None)


def main():
    password = os.environ.get("NET_PROXY_SSH_PASSWORD", "")
    if not password or any(c in password for c in "\r\n\0"):
        return 1
    sys.stdout.buffer.write(password.encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
