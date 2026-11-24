---
inclusion: always
---
# Zero pollution

The tool changes only what the user selected, and it can undo exactly what it changed.

Processes:

- `with-proxy`, `ProxySession` and the MCP tool `run_with_proxy` put proxy variables into the child environment (or the `with` block). The parent environment, shell profiles and system proxy settings stay untouched. Tests prove this by comparing the parent environment before and after.
- The proxy variable set is `sdk/config.py: proxy_environment`: `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` and `NO_PROXY` in upper and lower case. Never add a variable in one place only.

Remote nodes (`web/provision.sh`, `web/session_switch.sh`, `web/container_helpers.sh`):

- Before the first change, snapshot every managed file under `$HOME/.local/state/net-proxy-tool/`, as its original content and mode or as a marker that it was absent.
- Switching off restores content, permissions and absence exactly, then removes only the state the tool created.
- Verify the result in a new login shell (`web/node_baseline.py`), not in the session that made the change. A restored node may still use a proxy that the user had before; report that as it is.
- Refuse symlinks in the state path, use a lock directory, and never change `/etc` files.
- Never send a password on a command line or in a script body. SSH passwords reach `ssh` through the askpass helper's environment only.

Field nodes:

- Real nodes are tested read-only unless the maintainer says otherwise. Never switch, provision or restore a real node on your own initiative.
- Field results (addresses, host names, account names) are written to `scratch/` only.
