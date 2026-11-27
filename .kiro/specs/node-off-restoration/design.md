# Design Document: node-off-restoration

## Overview
Three focused changes work together across CSS theming, remote POSIX provisioning (`web/provision.sh` + `bin/docker-proxy-state.sh`), baseline probing (`web/node_baseline.py`), and server orchestration (`web/server.py`):

1. **CSS Theme Variables (`web/static/style.css`)**:
   Move `.wizard-header-banner`, `.stepper-pipeline`, `.live-feedback-box`, `.table-toolbar` and `.search-input:focus` backgrounds into CSS variables (`--wizard-banner-bg`, `--pipeline-bg`, `--feedback-bg`, `--toolbar-bg`, `--input-focus-bg`) overridden cleanly inside `@media (prefers-color-scheme: light)`.
2. **Tool-Owned Stripping + Atomic Baseline (`web/provision.sh`, `bin/docker-proxy-state.sh`)**:
   - Helper `strip_tool_blocks()` removes `# --- NET-PROXY-TOOL-START ---` .. `# --- NET-PROXY-TOOL-END ---` ranges (and single-line `[ -r "$HOME/.net-proxy-switch.sh" ]` loaders) from shell profiles.
   - Helper `strip_tool_lines()` removes lines tagged with `# net-proxy-tool` (plus pure tool-written `.curlrc`/`.wgetrc`/`.gitconfig`/`pip.conf`/`99net-proxy` entries when identified).
   - Every tool-written configuration line carries a `# net-proxy-tool` comment tag (while remaining 100% valid syntax in `curl`, `wget`, `pip`, `apt`, `sh` and `/etc/environment`) or `# --- NET-PROXY-TOOL-START/END ---` block, so clean stripping never harms unrelated operator configuration! (For `git config`, track our applied proxy URL / unset exact matching `http.proxy`/`https.proxy` keys.)
   - Container mode (`npt_is_docker=1` when `os_type == "docker"` or `access_mode == "docker_host"` or `/.dockerenv` present) enables snapshotted management of `/etc/profile.d/net-proxy.sh`, `/etc/environment`, `/etc/curlrc`, `/etc/wgetrc` inside the container only; and on `off`, legacy `/etc` & `sudo -n` residuals (`v1.3` / `5036f30f` / `docker-proxy`) are cleaned symmetrically.
3. **Probe & Orchestration (`web/node_baseline.py`, `web/server.py`)**:
   - `node_baseline.py` reports `legacy_residual` booleans (`profile_markers`, `switch_file`, `etc_proxy_sh`, `etc_environment`) without leaking secrets/content.
   - `apply_node_proxy(..., "off", ...)` forces execution of `provision.sh off` whenever `current_state != "disabled"`, `legacy_residual` is true, or `proxy_variables` still match `gateway`; and marks verification failed if `matches_selected_gateway` or `legacy_residual` persists after `off`.
