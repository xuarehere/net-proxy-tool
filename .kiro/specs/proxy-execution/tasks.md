# Implementation Plan: proxy-execution

- [x] 1. Add the execution regressions
  - The argument, directory, timeout and output limits are refused
  - A program that is not on the path is refused, and a Windows batch program is refused
  - The child sees the proxy variables and the parent environment is unchanged
  - A timeout stops the process tree and reports it
  - The output is cut at the limit and the truncation is reported
  - The audit record holds the program, the count, the hash and the exit code, and no argument
  - P9: the child receives the proxy variables and the parent environment stays the same
  - _Requirements: 1.1–1.5, 2.1–2.4, 3.1–3.3, 4.1–4.5, 5.1–5.3, 6.1–6.3_

- [x] 2. Implement `run_with_proxy`
  - Validate the arguments, resolve the program and the working directory
  - Build the child environment and start the process without a shell
  - Read the output up to the limit and stop the process tree on a timeout or a cancellation
  - Write the audit record and answer
  - _Requirements: 1.1–1.5, 2.1–2.4, 3.1–3.3, 4.1–4.5, 5.1–5.3_

- [x] 3. Register the tool
  - Describe `run_with_proxy` in `tools/list` with its input schema
  - Keep it out of the automatic approval list
  - _Requirements: 1.1–1.2_

- [ ] 4. Validate and commit Task 7
  - [x] 4.1 Run the focused tests (11 execution tests, P9 property)
  - [x] 4.2 Run the full suite with a temporary `NET_PROXY_CONFIG` (244 tests, 1 optional SSH-image skip)
  - [x] 4.3 Run the Python 3.8 check, the stdlib check and the secret scans (`findings=0`)
  - [ ] 4.4 Review the complete Task 7 diff and create one local commit; do not push
  - _Requirements: 6.1–6.3_
