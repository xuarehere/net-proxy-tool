# Implementation Plan: console-hardening

- [x] 1. Add request-boundary regression tests
  - Content-Type 415, body length/encoding/JSON errors and the 1 MiB cap
  - Duplicate Content-Length, Transfer-Encoding and duplicate Content-Type are rejected
  - Unpaired Unicode surrogate and over-deep JSON are rejected before persistence
  - Safe internal 500 response with Error ID and stderr-only traceback frames
  - 60-second connection timeout
  - `/api/test-host` rejects invalid destinations before transport
  - Gateway protocol normalization and rejected-update preservation
  - _Requirements: 1.1–1.6, 2.1–2.5, 3.1–3.5, 4.1–4.4, 5.1–5.2_

- [x] 2. Implement typed request validation
  - Primitive string, integer and Boolean validators
  - Field limits, tags and nested batch node selections
  - Validate and cache one normalized body before handler dispatch
  - _Requirements: 1.1–1.6_

- [x] 3. Harden body parsing and error handling
  - JSON media type, header ambiguity, Content-Length and decoding checks
  - `RequestError` status handling
  - Generic Error ID responses and stderr traceback-frame logging
  - Apply the policy to GET and POST APIs
  - _Requirements: 2.1–2.5, 3.1–3.5_

- [x] 4. Bound request connections and diagnostics
  - Set the connection socket timeout to 60 seconds
  - Validate `/api/test-host` through `validate_host_port`
  - Send audit failures to stderr without request details
  - _Requirements: 4.1–4.2, 5.1–5.2, 6.1–6.2_

- [x] 5. Normalize gateways without partial mutation
  - Normalize protocol in gateway URL, add, test and update paths
  - Validate a draft before replacing a saved gateway
  - Preserve the prior gateway when validation fails
  - _Requirements: 4.3–4.4_

- [x] 6. Implement the generated-input properties
  - [x] 6.1 P1 proxy URL round trip and IPv6 brackets
  - [x] 6.2 P2 total typed validators
  - [x] 6.3 P3 URL/curl round trip and interpolation rejection
  - [x] 6.4 P4 recursive sensitive-key removal
  - [x] 6.5 P5 config round trip and replacement-failure atomicity
  - [x] 6.6 P6 generated POST bodies against every registered endpoint
  - _Requirements: 7.1–7.3_

- [x] 7. Validate and commit Task 3 (commit `94d13c3`)
  - [x] 7.1 Run focused tests with `HYPOTHESIS_PROFILE=ci` (12 HTTP regressions, P1–P6 property module)
  - [x] 7.2 Run Python 3.8 compatibility and stdlib checks
  - [x] 7.3 Run current-change secret scan (`findings=0`)
  - [x] 7.4 Run the full suite with a temporary `NET_PROXY_CONFIG` (179 tests, 1 optional SSH-image skip)
  - [x] 7.5 Review the complete Task 3 diff and create one local commit; do not push
  - _Requirements: 7.1–7.3_
