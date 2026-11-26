# Implementation Plan: mcp-server

- [x] 1. Add the protocol regressions
  - The version negotiation: current protocol, legacy versions, unsupported version, missing meta fields
  - `server/discover` and `initialize` answers
  - The five tools, their answers and their refusals
  - A cancelled request receives one answer and the notification receives none
  - P8: every answer line is valid JSON-RPC and every request is answered once
  - _Requirements: 2.1–2.5, 3.1–3.7, 4.1–4.5, 5.1–5.7, 6.1–6.3, 7.1–7.3_

- [x] 2. Implement the protocol layer
  - Version resolution and validation with `-32022` and `-32602`
  - `initialize`, `server/discover`, `tools/list`, `tools/call`, `ping`, `notifications/cancelled`
  - The message loop with a worker pool of four and a locked writer
  - Standard output carries protocol messages only; ordinary output goes to standard error
  - _Requirements: 1.1–1.4, 2.1–2.5, 3.1–3.7, 4.1–4.5, 6.1–6.3_

- [x] 3. Implement the diagnostic tools
  - `list_gateways`, `check_gateway`, `check_gateway_targets`, `list_nodes`, `test_node`
  - Redact every answer; refuse an unknown node
  - _Requirements: 5.1–5.7_

- [x] 4. Register the entry point and the packaging
  - The console script `net-proxy-tool-mcp` in `pyproject.toml`
  - `net_proxy_mcp.py` in the packaging allowlist
  - `docs/kiro/mcp.json` for the maintainer to copy into `.kiro/settings/mcp.json`
  - _Requirements: 1.1–1.2_

- [ ] 5. Validate and commit Task 6
  - [x] 5.1 Run the focused tests (15 protocol tests, P8 property)
  - [x] 5.2 Run the full suite with a temporary `NET_PROXY_CONFIG` (232 tests, 1 optional SSH-image skip)
  - [x] 5.3 Run the Python 3.8 check, the stdlib check and the secret scans (`findings=0`)
  - [ ] 5.4 Review the complete Task 6 diff and create one local commit; do not push
  - _Requirements: 7.1–7.3_

## Note

P8 found a real defect while it was written: cancelling a request that had not started removed its
future, so the request received no answer at all. The cancellation now answers the request itself
with `-32800`, and the answer count always matches the request count.
