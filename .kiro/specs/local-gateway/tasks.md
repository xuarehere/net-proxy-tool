# Implementation Plan: local-gateway

- [x] 1. Add the gateway regressions
  - A CONNECT tunnel reaches a local origin
  - An absolute request reaches a local origin and keeps the path
  - A forbidden destination port is refused with 403 and opens no connection
  - A request that is not a proxy request is refused with 400
  - An oversized head is refused with 431
  - The record list names the host and the port and holds no body
  - The configuration record carries the id `local-gateway` and the kind `local`
  - P10: every generated request head is answered and the forbidden ones are refused
  - _Requirements: 1.1–1.3, 2.1–2.3, 3.1–3.5, 4.1–4.3, 5.1–5.4, 7.1–7.3_

- [x] 2. Implement the gateway
  - `LocalGateway` with `start`, `stop`, `records_list` and `config_record`
  - The CONNECT and the absolute request paths, with the upstream variant
  - The tunnel, head, connect and idle limits
  - The connection records
  - _Requirements: 1.1–1.3, 2.1–2.3, 3.1–3.5, 4.1–4.3, 5.1–5.4_

- [x] 3. Provide the command line
  - `python -m web.local_gateway` with `--port`, `--upstream` and `--allow-port`
  - Print the address and stop on an interrupt
  - _Requirements: 6.1–6.3_

- [x] 4. Register the runtime file
  - Add `web/local_gateway.py` to the packaging allowlist
  - _Requirements: 1.1, 6.1_

- [ ] 5. Validate and commit Task 8
  - [x] 5.1 Run the focused tests (9 gateway tests, P10 property)
  - [x] 5.2 Run the full suite with a temporary `NET_PROXY_CONFIG` (255 tests, 1 optional SSH-image skip)
  - [x] 5.3 Run the Python 3.8 check, the stdlib check and the secret scans (`findings=0`)
  - [ ] 5.4 Review the complete Task 8 diff and create one local commit; do not push
  - _Requirements: 7.1–7.3_
