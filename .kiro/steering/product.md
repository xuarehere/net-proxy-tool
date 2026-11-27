---
inclusion: always
---
# Product: net-proxy-tool

net-proxy-tool sends chosen workloads through an existing HTTP proxy (a "gateway") and leaves the rest of the machine alone. Its users are developers and operators whose servers, containers or edge devices reach the internet only through a proxy, for example a lab behind a Clash or Mihomo workstation.

Entry points:

- Web console (`launcher.py`, `web/server.py`, port 8899, loopback only unless `--bind` or `NET_PROXY_BIND`): add gateways, send a test request through a gateway, and switch remote Linux accounts and Docker containers on or off over SSH or `docker exec`.
- CLI `with-proxy` (`with_proxy.py`, `bin/`): run one command with proxy variables set for that child process only.
- Python SDK `sdk.proxy_session.ProxySession`: proxy variables inside a `with` block, restored when it exits.
- New in v1.5.0: an MCP server for coding agents (`net_proxy_mcp.py`), a built-in local observation gateway (`web/local_gateway.py`) so the tool can be tried without a proxy, an access token for consoles reachable from other hosts, and an English and Chinese UI.

Promises that every change must keep:

1. Zero pollution: proxy settings reach only the chosen process, account or container, and switching a node off restores its previous state exactly. See `zero-pollution.md`.
2. Honest diagnostics: a test reports the final HTTP status, or the host and step where the request stopped. It never guesses.
3. No runtime dependencies: download, extract and run. Release archives bundle Python.
4. Local secrets: SSH passwords stay in the console configuration. The API, logs, MCP results and error messages never contain them.

Out of scope for v1.5.0: SOCKS5 gateways, gateway authentication, a gateway "entry type" data model, and configuration writes from MCP.
