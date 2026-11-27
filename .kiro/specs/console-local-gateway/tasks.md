# Implementation Plan: console-local-gateway

- [x] 1. Add the console gateway regressions
  - The state answers whether the gateway runs and which port it uses
  - Starting the gateway writes its configuration record
  - Stopping the gateway removes the record
  - A remote node is refused a gateway of the kind `local`
  - A local node may use it
  - _Requirements: 1.1–1.5, 3.1–3.3, 4.1–4.3_

- [x] 2. Implement the console side of the gateway
  - The state, the start and the stop
  - The configuration record and its refresh at startup
  - The refusal for a remote node
  - _Requirements: 1.1–1.5, 3.1–3.3_

- [x] 3. Offer the two entry points
  - The panel with the start button, the demo button and the stop button
  - The address and the contacted hosts
  - The demo request through `https://example.com/`
  - _Requirements: 2.1–2.4_

- [x] 4. Validate and commit Task 12 (commit `faef381`)
  - [x] 4.1 Run the focused tests (7 console gateway tests)
  - [x] 4.2 Run the full suite with a temporary `NET_PROXY_CONFIG` (273 tests, 1 optional SSH-image skip)
  - [x] 4.3 Run the Python 3.8 check, the stdlib check and the secret scans (`findings=0`)
  - [x] 4.4 Review the complete Task 12 diff and create one local commit; do not push
  - _Requirements: 4.1–4.3_

## Note

The console now reads and drops an oversized request body, up to 4 MiB, before it answers 413. Without
that, a client that was still sending received a connection reset instead of the answer, which the
hardening test caught as a flaky failure.
