---
inclusion: always
---
# Technology

- Python 3.8 or newer, standard library only at runtime. `[project].dependencies` in #[[file:pyproject.toml]] stays empty. Runtime code is the root scripts plus `sdk/`, `web/`, `bin/` and `tools/`; the stdlib hooks block third-party imports there. An optional import must sit inside `try/except ImportError`.
- Runtime code must also run on Python 3.8: no `match`, no `X | Y` annotations, no `list[str]`-style built-in generics outside strings, no `dict | dict`, no parenthesized context managers, no `str.removeprefix`, no `zip(strict=...)`. Modules added after 3.8 (`tomllib`, `zoneinfo`, `graphlib`) are allowed only inside `try/except ImportError`.
- Test-only tools come from `requirements-dev.txt`: Hypothesis for property tests (`test/test_prop_*.py`, skipped when Hypothesis is missing) and Playwright for browser checks (`packaging/test_browser_*.py`).
- Web server: a `ThreadingHTTPServer` subclass in `web/server.py`. Front end: plain HTML, CSS and JavaScript in `web/static/` with no build step, framework or CDN.
- Remote nodes: the system `ssh` client with a key or the askpass helper `web/ssh_askpass.py`, and `docker exec` through a host. Scripts sent to nodes (`web/*.sh`) are POSIX `sh` without bashisms, because containers may lack bash. Local helpers in `bin/` may use bash.
- Configuration: JSON at `NET_PROXY_CONFIG`, else `config.json` at the repository root, else the platform directory (`sdk/config.py: config_path`). Writes go through `atomic_json`.
- Packaging: a wheel (`packages = ["sdk", "web"]`), portable archives from `packaging/build_portable.py`, whose `FILES` allowlist must list every new runtime file, and the `Dockerfile`.
- Windows is a first-class platform: PowerShell is the default shell, run Python with `-X utf8`, and expect Chinese characters and spaces in paths.

Commands:

- Full suite: `python -X utf8 -m unittest discover -s test`, with `NET_PROXY_CONFIG` pointing at a file in a temporary directory.
- One module: `python -X utf8 -m unittest discover -s test -p test_management.py`.
- Guard checks by hand: `python -X utf8 tools/kiro/check_stdlib.py --all` and `python -X utf8 tools/kiro/scan_secrets.py --staged`.
- Development tools: `python -m pip install -r requirements-dev.txt`.
