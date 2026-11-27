---
inclusion: always
---
# Repository layout

| Path | Contents |
| --- | --- |
| `launcher.py` | `net-proxy-tool` console script: single-instance lock, start and stop of the Web console |
| `with_proxy.py`, `bin/` | `with-proxy` CLI and shell helpers (`proxy-on`, `docker-proxy`, `session_env.py`) |
| `sdk/` | `config.py` (paths, load and save, `proxy_environment`, `resolve_gateway`, `VERSION`) and `proxy_session.py` |
| `web/server.py` | HTTP API and static file server for the console |
| `web/node_probe.py`, `web/node_baseline.py` | Remote node checks and read-only login-shell baselines |
| `web/*.sh` | POSIX scripts sent to nodes: `provision.sh`, `session_switch.sh`, `container_helpers.sh` |
| `web/static/` | `index.html`, `app.js`, `style.css` |
| `test/` | `unittest` suite; `test_prop_*.py` are Hypothesis properties; `prop_support.py` holds their settings |
| `packaging/` | Portable build, smoke tests, browser checks and Docker-based integration tests used by CI |
| `tools/kiro/` | Hook scripts: guards, secret scanner, stdlib check, related tests, session brief |
| `docs/` | Operations guides, architecture diagrams, `docs/kiro/` (MCP config and permission examples) |
| `.kiro/specs/<name>/` | `requirements.md`, `design.md`, `tasks.md` for each feature (`bugfix.md` for bug fixes) |
| `scratch/` | Git-ignored notes, logs, field data and the private denylist. Nothing here is published |

Conventions:

- New runtime modules go in `web/` or `sdk/` and get an entry in `packaging/build_portable.py: FILES`.
- Each test module is `test/test_<area>.py`. A test that writes configuration uses a temporary `NET_PROXY_CONFIG`.
- User-facing documentation comes in pairs: `QUICKSTART_EN.md` and `QUICKSTART.md`, `docs/operations_en.md` and `docs/operations.md`, and the READMEs. From v1.5.0 `README.md` is English and `README.zh-CN.md` Chinese; before that, `README.md` is Chinese and `README_EN.md` English. Change both files of a pair together.
- Release notes go in `CHANGELOG.md` under `## [x.y.z]`. The version lives in `sdk/config.py: VERSION` and `pyproject.toml` and must match.
