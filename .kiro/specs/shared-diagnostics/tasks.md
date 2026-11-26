# Implementation Plan: shared-diagnostics

- [x] 1. Add the report regressions
  - A status report without a gateway, with an unreachable gateway and with an unusable protocol
  - The target order follows the configuration
  - The node summary carries the effective proxy and the three warnings
  - `proxy_url` encloses an IPv6 host exactly once
  - The release checker reports consistent and inconsistent versions
  - _Requirements: 1.1–1.6, 2.1–2.3, 3.1–3.6, 4.1–4.2, 5.1–5.5_

- [x] 2. Provide one proxy URL format
  - `sdk.config.proxy_url(host, port)` and its use in `proxy_environment`
  - `web.server.gateway_url` uses it
  - _Requirements: 4.1–4.2_

- [x] 3. Implement the shared diagnostics
  - `web/diagnostics.py` with `gateway_report`, `targets_report`, `node_summary` and `status_report`
  - The console builds its status answer with `status_report`
  - _Requirements: 1.1–1.6, 2.1–2.3, 3.1–3.6_

- [x] 4. Implement the release consistency check
  - `tools/kiro/check_release_consistency.py`
  - Report the version of every place and every mismatch
  - Compare the example configuration's `no_proxy` with the default
  - _Requirements: 5.1–5.5_

- [x] 5. Update the packaging allowlist
  - Add `web/diagnostics.py` to `packaging/build_portable.py: FILES`
  - _Requirements: 1.1, 4.1_

- [ ] 6. Validate and commit Task 5
  - [x] 6.1 Run focused tests (15 report and release tests)
  - [x] 6.2 Run the full suite with a temporary `NET_PROXY_CONFIG` (216 tests, 1 optional SSH-image skip)
  - [x] 6.3 Run the Python 3.8 check, the stdlib check and the secret scans (`findings=0`)
  - [ ] 6.4 Review the complete Task 5 diff and create one local commit; do not push
  - _Requirements: 6.1–6.3_
