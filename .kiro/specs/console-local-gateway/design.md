# Design Document: console-local-gateway

## Overview

The console owns one observation gateway. It starts it, stops it, keeps its configuration record in the console configuration and reports what it saw. The gateway itself lives in `web/local_gateway.py`; this feature adds the console side.

## State

```python
LOCAL_GATEWAY = {"instance": None, "record": None}
```

`instance` is the running `LocalGateway`, `record` is its configuration record. The record holds the identifier `local-gateway`, the kind `local` and the port the gateway listens on.

## The endpoints

### `GET /api/local-gateway`

```python
{"running": True, "port": 41234, "address": "127.0.0.1:41234",
 "gateway": {...}, "records": [...], "allowed_ports": [80, 443],
 "reachable": [{"address": "127.0.0.1", "loopback": True}, ...]}
```

The records are the gateway's own connection records. The reachable addresses tell the operator which address a remote node could use for a gateway.

### `POST /api/local-gateway`

The body holds `{"action": "start"}` or `{"action": "stop"}`.

- `start` starts the gateway on the loopback interface with a free port, writes the record into the configuration and answers with the state.
- `stop` stops the gateway, removes the record from the configuration and answers with the state.

An unknown action is refused with 400.

## The configuration record

The record is an ordinary entry of the `gateways` list, with two extra fields:

```json
{"id": "local-gateway", "name": "本机观测网关", "host": "127.0.0.1", "port": 41234,
 "protocol": "http", "kind": "local", "description": "随工具提供的本机观测网关，只监听回环地址。"}
```

Because it is an ordinary record, the wizard, the gateway list and the node binding all work with it. The `kind` marks it as the local one.

The port changes on every start, so the record is rewritten whenever the gateway starts. A console that finds a `local-gateway` record at startup starts the gateway again and refreshes the port.

## The remote node refusal

`validate_client` refuses a node whose execution mode is not `local` and whose bound gateway has the kind `local`:

```python
if gateway.get("kind") == "local" and mode != "local":
    raise ValueError("本机观测网关只监听回环地址，远程节点无法访问；请为远程节点选择可达的网关。")
```

The message names the reason, and the shared diagnostics warn about the same situation for any loopback gateway.

## The two entry points

The first-run screen gains a panel with two buttons:

- **启用本机观测网关** starts the gateway and saves it as a gateway. The panel then shows the address.
- **立即体验** starts the gateway, saves it and sends one request through it to `https://example.com/`, so that the reviewer sees a real result without preparing anything.

The panel shows the address of the gateway and the hosts it saw, and it offers a button that stops the gateway again.

## Error handling

- The gateway cannot bind: the console answers with the error type and keeps the configuration unchanged.
- The configuration cannot be saved: the gateway is stopped again, so the console does not keep a gateway that the configuration does not name.
- An unknown action: 400.

## Testing strategy

`test/test_console_local_gateway.py` covers the state, the start, the stop, the configuration record and the refusal for a remote node.

`packaging/test_browser_local_gateway.py` drives the two entry points in Chromium and checks that the address and the contacted host appear. The browser check runs in CI, where Chromium is installed.
