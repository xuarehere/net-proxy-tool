---
inclusion: fileMatch
fileMatchPattern: ["web/**/*.py", "web/**/*.sh", "net_proxy_mcp.py", "with_proxy.py", "launcher.py", "bin/**", "sdk/**/*.py", "tools/kiro/**"]
---
# Security rules for runtime code

Console API (`web/server.py`):

- Every request passes the Host and Origin checks in `parse_request`. Non-loopback clients also need the access token (`NET_PROXY_ACCESS_TOKEN`, or the generated one), sent as the `npt_access` cookie. IPv4-mapped loopback counts as loopback.
- Validate input at the handler boundary: typed fields, lengths and ranges, and host or port syntax. Bad input returns 400 with a message; a body that is not `application/json` returns 415.
- Unexpected errors return 500 with an `error_id` only. Log the traceback with the same id to the console log, never to the client.
- Responses go through `public_data`, which removes `ssh_pass`, `password`, `token`, `api_key`, `private_key` and node baselines at any depth. New sensitive fields must be added there.
- Audit entries (`write_audit_log`) record who did what (client address, action, node or gateway id) with ISO timestamps. They never record secrets or full command lines.

Processes and remote commands:

- Build commands as argument lists. No `shell=True`, no string concatenation into a shell command. Quote with `shlex.quote` only for the POSIX scripts sent to nodes.
- Every subprocess and socket has a timeout. Long jobs must be cancellable.
- Kill the whole process tree on timeout: `os.killpg` on POSIX, `taskkill /T /F` on Windows.

MCP server (`net_proxy_mcp.py`):

- stdout carries JSON-RPC messages only. Logs and warnings go to stderr.
- Tools never write configuration. `run_with_proxy` runs without a shell, refuses `.bat` and `.cmd` on Windows, keeps `cwd` inside the server's start directory, and caps time and output.

Local gateway (`web/local_gateway.py`):

- Bind 127.0.0.1 only. Allow CONNECT and absolute-URI requests to ports 80 and 443 unless the operator adds ports. Enforce header size, connection count and idle limits.

Secrets in the repository:

- Never print git remote URLs or `config.json`. Use `git remote` and `tools/kiro/redacted_config.py`.
- Test fixtures that look like credentials are assembled at run time, or carry `pragma: allowlist secret` on the same line.
