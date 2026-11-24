# Implementation Plan: dev-guardrails

- [x] 1. Shared hook input and evidence log
  - `tools/kiro/_hookio.py`: `read_event`, `event_paths`, `repo_relative`, `record`
  - Unit tests for malformed input, nested paths and repository-relative paths
  - _Requirements: 9.1, 9.3, 9.4_

- [x] 2. Secret scanner
  - [x] 2.1 Patterns, allow marker, Denylist, masked previews and the diff parser in `tools/kiro/scan_secrets.py`
    - _Requirements: 3.4, 3.5, 3.6, 3.8_
  - [x] 2.2 Staged, worktree, untracked and unpushed scans with git failures reported as `RuntimeError`
    - _Requirements: 3.1, 3.2, 3.3, 3.7_
  - [x] 2.3 Property test for embedded credentials and diff scanning
    - **Property P11: Embedded credentials are found and never shown**
    - **Validates: Requirements 3.4, 3.5, 3.1**
    - Writing P11 exposed a preview misalignment: positions found in `text.lower()` drifted for characters such as U+0130. Fixed with a case-insensitive search on the original text and pinned with `@example`.

- [x] 3. Shell and file guard
  - [x] 3.1 Remote URL, `.git/config`, `gh` token and force-push rules with segment splitting
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1_
  - [x] 3.2 Nested command lines (`cmd /c`, `powershell -Command`, `bash -c`, `wsl`, `Invoke-Expression`, `$( )`, backticks) and MCP `argv`
    - _Requirements: 1.4, 1.6_
  - [x] 3.3 Commit and push secret scan wiring
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.7_
  - [x] 3.4 Console configuration rule for shell and file tools, and `tools/kiro/redacted_config.py`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 3.5 Pre-write stdlib rule for write, append and replace tools
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 3.6 Property test for command composition
    - **Property P12: Every simple command is judged**
    - **Validates: Requirements 1.4, 1.5**

- [x] 4. Stdlib check on save
  - `tools/kiro/check_stdlib.py` with hook, `--all` and path modes, and the pyproject dependency check
  - _Requirements: 5.2, 5.4, 5.5_

- [x] 5. Related tests and full-suite runs
  - `tools/kiro/run_related_tests.py` with `--changed` (fingerprint skip), path, event and `--all` modes, all with a temporary `NET_PROXY_CONFIG`
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 6. Session brief
  - `tools/kiro/session_brief.py`
  - _Requirements: 7.1, 7.2_

- [x] 7. Property test infrastructure
  - `test/prop_support.py`, `requirements-dev.txt`, CI step that installs it, `.hypothesis/` in `.gitignore`
  - _Requirements: 10.1, 10.2, 10.3_

- [x] 8. Steering
  - Always: `product.md`, `tech.md`, `structure.md`, `zero-pollution.md`
  - File match: `security.md`, `testing.md`, `i18n.md`, `docs-style.md`
  - Manual: `release.md`, `field-validation.md`

- [ ] 9. Register the hooks and complete the available validation
  - [x] 9.1 Create the eight hooks from the design with Kiro's hook tool
  - [x] 9.2 Exercise Shell guard, File guard and stdlib hook stdin payloads without running a sensitive command
  - [ ] 9.3 In a new Kiro session, use only the harmless File-guard probe from the design and confirm the live hook event; never use a remote-URL or configuration-reading command for this check
  - [x] 9.4 Review the full Task 2 diff and add regressions for verbose short flags, wrapped `gh`, wildcard `git add`, detached `HEAD`, symbolic links, Python 3.8 fallbacks and URL-safe session briefs
  - [x] 9.5 Run the current-change secret scan (`findings=0`), focused CI-profile tests (40 unit, P11 3, P12 3), Python 3.8 check, stdlib check and the full suite (159 tests, 1 platform skip)
  - _Requirements: 1.1, 3.2, 3.3, 3.9, 5.4, 5.5, 6.1, 7.1, 8.1_
