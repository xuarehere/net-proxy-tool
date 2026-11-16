"""Build a wheel, install it into a clean venv, and invoke both console scripts outside the checkout."""
import contextlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import venv
from pathlib import Path

from smoke import api

ROOT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def workspace_directory():
    path = Path(tempfile.mkdtemp(prefix="wheel 中文 "))
    try:
        yield path
    finally:
        # Windows can retain the log or venv executable briefly after shutdown.
        deadline = time.monotonic() + 8
        while path.exists():
            try:
                shutil.rmtree(path)
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)


def main():
    with workspace_directory() as temp:
        tool_env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(temp), str(ROOT)],
                       cwd=temp, env=tool_env, check=True)
        env_dir = temp / "venv"
        venv.create(env_dir, with_pip=True)
        bin_dir = env_dir / ("Scripts" if os.name == "nt" else "bin")
        suffix = ".exe" if os.name == "nt" else ""
        python = bin_dir / ("python" + suffix)
        wheel, = temp.glob("*.whl")
        subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
                       cwd=temp, env=tool_env, check=True)
        env = dict(tool_env, NET_PROXY_CONFIG=str(temp / "config.json"))
        env.pop("PYTHONPATH", None)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        def console(name, *args):
            result = subprocess.run([str(bin_dir / (name + suffix)), *args], env=env, cwd=temp,
                                    stdout=subprocess.PIPE, encoding="utf-8", timeout=30, check=True)
            print(result.stdout.rstrip())
            return result.stdout
        console("net-proxy-tool", str(port), "--no-browser")
        try:
            assert api(port, "/api/health")["status"] == "ok"
            console("with-proxy", "--gateway", "127.0.0.1:19457", "--no-check", str(python), "-c",
                    "import os; assert os.environ['HTTP_PROXY']=='http://127.0.0.1:19457'")
        finally:
            stopped = console("net-proxy-tool", "--stop")
            assert "Console stopped." in stopped, stopped


if __name__ == "__main__":
    main()
