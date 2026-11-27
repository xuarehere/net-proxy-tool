# Implementation Plan: node-off-restoration

- [x] 1. Update specs and `.kiro/steering/zero-pollution.md` scope wording for container-scoped `/etc` and tool-owned residual cleanup.
- [x] 2. Write failing regression tests for wizard contrast (`packaging/test_browser_console.py`), legacy `5036f30f` residual cleanup (`test/test_provision_legacy.py`), residual proxy conflict detection (`test/test_node_baseline.py`, `test/test_node_lifecycle.py`), and Docker full-session on/off isolation (`test/test_docker_proxy_state.py`).
- [x] 3. Implement theme contrast CSS variables in `web/static/style.css`.
- [x] 4. Implement tool-marker baseline sanitation, legacy/Docker `/etc` + `/etc/environment` cleanup in `web/provision.sh`, `bin/docker-proxy-state.sh`, `web/node_baseline.py`, `web/server.py`, and clear residual warning copy in `web/static/app.js` + i18n.
- [x] 5. Verify full test suite (`HYPOTHESIS_PROFILE=ci`), Playwright light/dark contrast screenshots, `check_stdlib.py`, `scan_secrets.py`, and commit cleanly alongside the approved architecture diagrams.
