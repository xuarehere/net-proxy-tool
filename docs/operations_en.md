# Configuration, node management and troubleshooting

[简体中文](operations.md) · [Quick start](../QUICKSTART_EN.md) · [Security](../SECURITY.md)

## Locate the active configuration

The Web console, CLI and SDK use the following search order. Set the same absolute path in every entry point when using a custom configuration.

1. The file specified by `NET_PROXY_CONFIG`.
2. An existing `config.json` in the application directory, for older installations.
3. The default per-user configuration file.

| System | Default path |
| --- | --- |
| Windows | `%LOCALAPPDATA%\net-proxy-tool\config.json` |
| macOS | `~/Library/Application Support/net-proxy-tool/config.json` |
| Linux | `$XDG_CONFIG_HOME/net-proxy-tool/config.json`, or `~/.config/net-proxy-tool/config.json` when unset |

Saving the first gateway writes the configuration. The adjacent `data/` directory holds `console.log`, the node audit log and launcher state. Protect `instance.json` because it contains the token used to stop that instance. If a configuration is unreadable, back it up, fix the JSON and restart.

**Upgrade an older installation.** Stop the old console, back up your configuration and extract the new release into a fresh directory. Point `NET_PROXY_CONFIG` at the working configuration file. Existing gateways and nodes load without reapplying switches at startup. For a single CLI invocation, `--gateway HOST:PORT` or `NET_PROXY_GATEWAY` overrides the saved active gateway.

## Choose a node access method

| Method | Use it when |
| --- | --- |
| CLI / `ProxySession` | A local command or Python block needs the proxy. Python threads in the same process share environment variables. |
| Direct SSH | A Linux target runs SSH and one account needs proxy settings for several tools. Verify ordinary SSH login from the control host first. |
| SSH on a mapped port | SSH runs inside a container. Enter the host address, the published SSH port and the container's login user. |
| Docker via its host | A remote host account can access Docker. Supply that host and the exact container name. The container needs a POSIX shell. |

Bind the node to a gateway, run its preflight check and test the switch on that node. Inspect individual results for batch operations. A remote node with a gateway of `127.0.0.1` connects to itself. Supply a gateway address reachable from that node.

Remote switching can change curl, wget, pip, Git and shell configuration for the target account. A root account can also modify target system configuration. Version 1.4 keeps snapshots in the target account's `~/.local/state/net-proxy-tool/`. If a file was edited after activation, compare it with its snapshot and preserve the operator's changes. When legacy settings have no snapshot, the first explicit enable saves the current files and permissions. Disable restores that baseline, which may already contain a proxy. If you disable before capturing a baseline, the tool leaves those settings in place and reports that manual review is required.

## When the console works but the workload fails

1. Save the binding and check the node name and gateway together before switching.
2. Run the explicit proxy request on that node. Use its result to locate an SSH login failure, a missing container, a gateway route problem or a target response. An SSH authentication failure occurs before the target command starts.
3. Compare the ordinary curl request from the same account. Its environment, curl configuration and bypass list can change the route. After enabling the binding, check the gateway log to confirm the request passed through it.
4. Restore the initial switch state. Keep both the snapshot and the current file when an operator edit requires a manual merge.

In v1.3 the first wizard step checked TCP. In v1.4.0 it sent a real request but reported HTTP 302 as offline. Version 1.4.1 follows redirects through the selected gateway and reports proxy authentication, TLS and final HTTP results separately.

### Compare the same URL in a terminal and on the node

The worker pool defaults to `https://www.google.com/` and also offers Claude, ChatGPT, YouTube, Gemini and custom URLs. Examine the account, HOME, curl configuration, first response, final status and socket peer. The ordinary request uses that account’s settings. The explicit request selects the gateway. A matching peer supplies connection evidence. Independent public exit evidence requires a gateway log or a cooperating destination. HTTP 200 confirms access to the returned page.

Both worker probes require curl 7.61 or later on the target account. Check with `curl --version` in the same terminal. [curl option versions](https://curl.se/docs/optionsall.html)

On Windows, password SSH uses the control account’s OpenSSH client. Verify the host key and trust the exact host and port before using the saved identity. A node recorded as off can still inherit proxy settings from another tool or a login script.

## Use Docker Compose

On a host with Docker and Compose, run these commands in the source directory. The console publishes port 8899 on the host's loopback interface and stores configuration in a named volume.

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=80
```

Open `http://127.0.0.1:8899/` on the host. Stop with `docker compose down`. Inside a container, `127.0.0.1` points back to that container. Choose a gateway address reachable from the container and allow connections from its network. To change the published port, set `NET_PROXY_HOST_PORT` before running Compose and adjust the browser URL.

## Diagnose by symptom

If the peer closes a TLS handshake before the GET is sent, the gateway probe reconnects once within the original time budget. The result records the retry. Certificate validation failures are reported immediately.

| Symptom | Check |
| --- | --- |
| Windows reports that `roxy-tool` or `2` is not a command | Extract the entire Windows ZIP for the current release into a new directory and use its root `Start.bat`. The older UTF-8/LF batch file could parse incorrectly under code page 936. |
| No page after double-click | Extract all files and check the architecture. Run the launcher in a terminal to see the error. Open the printed URL if needed. |
| Port 8899 is occupied | Try a free port such as 8900. To stop a running instance for this configuration, use the same launcher with `--stop`. |
| The console opens but the proxy test fails | Verify the listening address and HTTP/mixed port. For a failed TCP connection, check the proxy service, interface and firewall. If TCP works, check protocol, upstream route and target. |
| HTTP 407 | The gateway requires authentication. The setup form accepts host and port. Choose an HTTP proxy entry point you are authorized to use. |
| Certificate error or target HTTP 403 / 429 | Check the target URL, certificate chain, site policy, rate limits and proxy logs. |
| SSH or container preflight fails | Check the SSH host, port, user and key from the control host. For Docker via host, check Docker permissions and the container name. |
| Settings disappear after upgrade | Verify the configuration search order, including the old program directory, account and `NET_PROXY_CONFIG`. |

`GET /api/health` reports the service name, version, PID and status. To check the gateway itself, send a proxied request to a target from the console.
