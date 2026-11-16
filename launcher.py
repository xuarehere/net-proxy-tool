"""Start the local console, wait for readiness and open the browser."""
import argparse
import contextlib
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import webbrowser

from sdk.config import atomic_json, data_dir, load_config


@contextlib.contextmanager
def launch_lock(directory):
    """Serialize launch and stop requests for this configuration."""
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / "launcher.lock").open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            if not stream.tell():
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def request(port, path, token=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
    try:
        if token:
            conn.request("POST", path, b"{}", {"Content-Type": "application/json",
                                               "X-Net-Proxy-Token": token})
        else:
            conn.request("GET", path)
        response = conn.getresponse()
        content = response.read(65536)
        return content if response.status == 200 else b""
    finally:
        conn.close()


def health(port):
    try:
        info = json.loads(request(port, "/api/health"))
        if info.get("service") == "net-proxy-tool" and info.get("status") == "ok":
            return info
    except (OSError, http.client.HTTPException, ValueError, AttributeError):
        pass
    return {}


def read_state(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def owns_console(state):
    if not state:
        return False
    expected = hashlib.sha256(state["token"].encode()).hexdigest()
    status = health(state["port"])
    return status.get("instance_id") == expected and status.get("pid") == state["pid"]


def stop(state, state_path):
    if not owns_console(state):
        print("No running console for this configuration.")
        state_path.unlink(missing_ok=True)
        return
    if not request(state["port"], "/api/shutdown", state["token"]):
        raise ValueError("The console did not accept the shutdown request.")
    deadline = time.monotonic() + 8
    while health(state["port"]).get("pid") == state["pid"]:
        if time.monotonic() >= deadline:
            raise ValueError("Shutdown timed out. Check console.log.")
        time.sleep(0.1)
    state_path.unlink(missing_ok=True)
    print("Console stopped.")


def start(port, directory, state, state_path):
    if owns_console(state):
        if port != state["port"]:
            raise ValueError(f"Console already uses port {state['port']}. Stop it before changing ports.")
        return
    if health(port):
        raise ValueError(f"Port {port} belongs to another console. Check the running configuration.")
    token = secrets.token_urlsafe(32)
    environment = dict(os.environ, NET_PROXY_INSTANCE_TOKEN=token, PYTHONUNBUFFERED="1",
                       PYTHONIOENCODING="utf-8", NET_PROXY_BIND="127.0.0.1")
    kwargs = ({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt"
              else {"start_new_session": True})
    log_path = directory / "console.log"
    with log_path.open("ab") as log:
        proc = subprocess.Popen([sys.executable, "-m", "web.server", str(port)],
                                cwd=str(Path(__file__).resolve().parent), env=environment,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, **kwargs)
    instance_id = hashlib.sha256(token.encode()).hexdigest()
    launched = False
    try:
        deadline = time.monotonic() + 12
        while proc.poll() is None:
            status = health(port)
            if status.get("instance_id") == instance_id and request(port, "/"):
                atomic_json(state_path, {"port": port, "pid": status["pid"], "token": token})
                launched = True
                return
            if time.monotonic() >= deadline:
                break
            time.sleep(0.15)
    finally:
        if not launched and proc.poll() is None:
            # A Windows venv can have a redirector PID distinct from the service.
            if health(port).get("instance_id") == instance_id:
                request(port, "/api/shutdown", token)
            else:
                proc.terminate()
            proc.wait(timeout=5)
    raise ValueError(f"Console could not start on port {port}. Check port availability and {log_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", type=int, nargs="?", help="override the configured port")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args(argv)
    try:
        directory = data_dir()
        state_path = directory / "instance.json"
        with launch_lock(directory):
            state = read_state(state_path)
            if args.stop:
                stop(state, state_path)
                return 0
            port = args.port if args.port is not None else int(load_config()["web_port"])
            if not 1 <= port <= 65535:
                raise ValueError("Port must be 1 through 65535.")
            start(port, directory, state, state_path)
        url = f"http://127.0.0.1:{port}/"
        print(f"Web console: {url}", flush=True)
        desktop = os.name == "nt" or sys.platform == "darwin" or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        if desktop and not args.no_browser:
            webbrowser.open(url)
        if not desktop:
            print(f"From your computer: ssh -N -L {port}:127.0.0.1:{port} USER@{socket.gethostname()}")
        return 0
    except (OSError, ValueError, KeyError, http.client.HTTPException, subprocess.SubprocessError) as exc:
        print(f"net-proxy-tool: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
