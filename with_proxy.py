#!/usr/bin/env python3
"""Run one command with the selected gateway in its child environment."""
import os
import socket
import subprocess
import sys

from sdk.config import load_config, proxy_environment, resolve_gateway


def check_gateway(host: str, port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def main():
    raw_args = sys.argv[1:]
    if not raw_args or raw_args in (["--help"], ["-h"]):
        print("Run one command using the gateway selected in the Web console.")
        print("Usage: with-proxy [--gateway HOST:PORT|ID] [--no-check] COMMAND [ARG ...]")
        print("Example: with-proxy curl -I https://example.com/")
        sys.exit(0 if raw_args else 1)

    explicit_gw = None
    skip_check = False
    cmd = []
    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        if arg in ("--gateway", "-g"):
            if i + 1 >= len(raw_args):
                sys.exit("--gateway requires a host:port or a gateway ID.")
            explicit_gw = raw_args[i + 1]
            i += 2
        elif arg.startswith("--gateway="):
            explicit_gw = arg.split("=", 1)[1]
            i += 1
        elif arg in ("--no-check", "-n"):
            skip_check = True
            i += 1
        else:
            cmd = raw_args[i:]
            break

    if not cmd:
        print("Specify a command to run.", file=sys.stderr)
        sys.exit(1)

    try:
        cfg = load_config()
        host, port = resolve_gateway(cfg, explicit_gw)
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))

    if not skip_check and not check_gateway(host, port):
        print(
            f"Gateway {host}:{port} is unreachable. Check its host and listening port.",
            file=sys.stderr
        )
        sys.exit(101)

    env = os.environ.copy()
    env.update(proxy_environment(cfg, host, port))

    try:
        ret = subprocess.run(cmd, env=env)
        sys.exit(ret.returncode)
    except KeyboardInterrupt:
        sys.exit(130)
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}", file=sys.stderr)
        sys.exit(127)
    except Exception as e:
        print(f"Command failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
