# Implementation Plan: mcp-inspect

- [x] 1. Add the inspect regressions
  - The command still leaves through the selected gateway
  - The contacted hosts are reported and hold no path or body
  - No observation gateway survives the call
  - Without `inspect`, no gateway is started
  - _Requirements: 1.1–1.4, 2.1–2.5, 3.1–3.4, 4.1–4.2_

- [x] 2. Implement the inspect mode
  - Start the observation gateway with the selected gateway as its upstream
  - Point the child's proxy variables at the observation gateway
  - Read the records into `contacted_hosts` and stop the gateway in every path
  - _Requirements: 1.1–1.4, 2.1–2.5, 3.1–3.4_

- [x] 3. Describe the new argument
  - Add `inspect` to the input schema of `run_with_proxy`
  - _Requirements: 1.1–1.2_

- [ ] 4. Validate and commit Task 9
  - [x] 4.1 Run the focused tests (4 inspect tests, 11 gateway tests)
  - [x] 4.2 Run the full suite with a temporary `NET_PROXY_CONFIG` (261 tests, 1 optional SSH-image skip)
  - [x] 4.3 Run the Python 3.8 check, the stdlib check and the secret scans (`findings=0`)
  - [ ] 4.4 Review the complete Task 9 diff and create one local commit; do not push
  - _Requirements: 4.1–4.2_

## Note

This task also fixed the upstream chaining of the observation gateway, which Task 8 had left
unfinished: an upstream proxy needs the original absolute request and the original CONNECT request,
not the origin form. The gateway now forwards the request it received and passes the upstream's own
answer to the client.
