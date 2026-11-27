---
inclusion: fileMatch
fileMatchPattern: ["test/**", "packaging/test_*.py", "packaging/smoke.py"]
---
# Testing rules

- Framework: `unittest` only in `test/`. Run with `python -X utf8 -m unittest discover -s test`.
- Every test that can write configuration sets `NET_PROXY_CONFIG` to a file in a temporary directory. Never read or change the root `config.json`, and never use port 8899: pick a free port (bind to port 0) instead.
- Write the failing test first, then the code. A bug fix starts with a test that reproduces the bug.
- POSIX-only tests skip on Windows with `unittest.skipIf(os.name == "nt", reason)`, and the reason says what is not available.
- Tests must not need the internet or a real proxy. Use local fixtures such as `test/gateway_tls_fixture.py` or the built-in local gateway with a local upstream.
- Credential-like fixtures are assembled at run time (`"gh" + "p_" + ...`) so the secret scanner never sees a literal.

Property-based tests:

- Files are `test/test_prop_<area>.py` and import their decorators from `prop_support` (`from prop_support import given, st`). That import skips the module when Hypothesis is missing.
- The module docstring names the property (P1 to P11) and the requirement it validates, for example "Property P4 (console-hardening, Requirement 2)".
- Profiles: `ci` runs 100 examples per property and is selected when `CI` is set; `dev` runs 50. `HYPOTHESIS_PROFILE` overrides both.
- Pin each bug that a property found with `@example(...)`, so the case runs on every build.
- Properties state what must always hold: round trips, invariants, "never 500", "never contains a secret". Avoid re-implementing the code under test inside the test.

Browser checks (`packaging/test_browser_*.py`) use Playwright with Chromium, start the console on a free port with a temporary configuration, and run in CI after `pip install -r requirements-dev.txt`.
