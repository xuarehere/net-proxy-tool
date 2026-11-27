# Implementation Plan: console-i18n

- [x] 1. Add the language regressions
  - Every key exists in both languages
  - Every `data-i18n` key of the page and every translated call of the script is known
  - The API localizes its answers and keeps an unknown message unchanged
  - The catalogue is served as a script
  - _Requirements: 1.1–1.4, 4.1–4.4, 5.1–5.3_

- [x] 2. Build the catalogue
  - The sources in `tools/i18n/` and `tools/i18n_build_messages.py`
  - `web/messages.py` with every message in both languages
  - _Requirements: 1.1–1.3_

- [x] 3. Implement the browser side
  - `web/static/i18n.js` with the detection, `t()`, the translation of the page and the toggle
  - The `X-NPT-Language` header on the API requests
  - _Requirements: 2.1–2.5, 3.1–3.3_

- [x] 4. Mark the page and the script
  - A `data-i18n` key for every static text of the page
  - `t()` for every dynamic string of the script
  - _Requirements: 3.1–3.3_

- [x] 5. Localize the API answers
  - The `error` and `message` fields follow the language of the request
  - _Requirements: 4.1–4.4_

- [x] 6. Update the packaging and the browser checks
  - `web/messages.py` and `web/static/i18n.js` in the packaging allowlist
  - The browser checks that assert Chinese text pin the Chinese language
  - `packaging/test_browser_i18n.py` and the CI step
  - _Requirements: 5.2–5.3_

- [x] 7. Validate and commit Task 11 (commit `f09af3b`)
  - [x] 7.1 Run the focused tests (9 language tests)
  - [x] 7.2 Run the full suite with a temporary `NET_PROXY_CONFIG` (282 tests, 1 optional SSH-image skip)
  - [x] 7.3 Run the Python 3.8 check, the stdlib check and the secret scans
  - [x] 7.4 Review the complete Task 11 diff and create one local commit; do not push
  - _Requirements: 5.1–5.3_
