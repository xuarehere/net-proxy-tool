# Implementation Plan: console-access

- [x] 1. Add access-control regressions
  - Non-loopback client without a token is refused with 401
  - A correct `token` query on the console root returns 302 and the `npt_access` cookie
  - A wrong token returns 401 and sets no cookie
  - A correct cookie is accepted; a loopback client never needs a token
  - An IPv4-mapped loopback client counts as loopback
  - The token never appears in a response body, an audit record or a request log line
  - The Host gate accepts a local name only when access control is active
  - The same flow over a real socket on a non-loopback address
  - _Requirements: 1.1–1.8, 2.1–2.4_

- [x] 2. Add audit, rotation, permission, write and identity regressions
  - The audit record carries an ISO timestamp and the client address
  - `audit.log` rotates at 5 MiB and keeps three generations
  - A configuration file warning names the file and the mode and no content
  - A locked configuration file is retried, and the original error survives
  - The recorded account name has no trailing newline byte
  - _Requirements: 3.1–3.3, 4.1–4.3, 5.1–5.3, 6.1–6.3, 7.1–7.2_

- [x] 3. Implement the access token
  - Resolve the token from `NET_PROXY_ACCESS_TOKEN` or generate one for a published console
  - Classify loopback clients, including IPv4-mapped addresses
  - Cookie and query handling, 302 and 401 responses
  - Redact the token in the request log
  - _Requirements: 1.1–1.8_

- [x] 4. Extend the Host gate for a published console
  - Discover the machine's own names and addresses without a public DNS lookup
  - Extend the allowed list only while access control is active
  - _Requirements: 2.1–2.4_

- [x] 5. Extend the audit record and rotate the logs
  - ISO timestamp and client address
  - `audit.log` rotation at 5 MiB with three generations
  - `console.log` rotation at 10 MiB in the launcher
  - _Requirements: 3.1–3.3, 4.1–4.3_

- [x] 6. Warn about loose configuration permissions
  - Report the file and its mode at startup, without content
  - _Requirements: 5.1–5.3_

- [x] 7. Make configuration writes reliable on Windows
  - Bounded retry for permission errors with a growing delay
  - _Requirements: 6.1–6.3_

- [x] 8. Record the exact node account name
  - Drop the newline byte before hashing the account name
  - _Requirements: 7.1–7.2_

- [x] 9. Update the container image, the operations guide and the changelog
  - Document the access link and the token in the container logs
  - Update the English and Chinese operations guides together
  - Add the v1.5.0 changelog entries
  - _Requirements: 1.3–1.4_

- [x] 10. Validate and commit Task 4 (commit `ca400e3`)
  - [x] 10.1 Run focused tests (15 access, 7 reliability, 8 property)
  - [x] 10.2 Run the full suite with a temporary `NET_PROXY_CONFIG` (200 tests, 1 optional SSH-image skip)
  - [x] 10.3 Run the Python 3.8 check, the stdlib check and the secret scans (`findings=0`)
  - [x] 10.4 Review the complete Task 4 diff and create one local commit; do not push
  - _Requirements: 8.1–8.3_
