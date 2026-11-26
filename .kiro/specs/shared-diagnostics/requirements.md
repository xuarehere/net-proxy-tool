# Requirements Document: shared-diagnostics

## Introduction

The Web console and the MCP server must tell an operator the same thing about a gateway and a node. Today the aggregation lives inside the console's request handler, so a second entry point would have to copy it. This feature moves the aggregation into `web/diagnostics.py` and adds a release consistency check.

## Glossary

- **Status report**: the gateway section, the target results and a timestamp, as the console's `/api/status` returns it.
- **Target**: one configured diagnostic site that is probed through the selected gateway.
- **Effective proxy**: the HTTP proxy URL a node would use with its saved gateway binding.
- **Loopback warning**: the notice that a remote node cannot reach a gateway on the control machine's loopback interface.

## Requirements

### Requirement 1: One aggregation for both entry points

**User Story:** As an operator, I want the console and the agent tools to describe a gateway in the same words, so that a report can be compared without translation.

#### Acceptance Criteria

1. THE repository SHALL provide `web/diagnostics.py` with `gateway_report`, `targets_report`, `node_summary` and `status_report`.
2. WHEN the console answers a status request, THE Console SHALL build its answer with `status_report` instead of its own aggregation.
3. THE status report SHALL keep the existing shape: a `gateway` object with `id`, `name`, `host`, `port`, `online`, `tcp_ok`, `path_verified`, `latency_ms` and `error`, a `targets` list and a `timestamp`.
4. WHEN no gateway is selected, THE status report SHALL contain `gateway: null`, an empty `targets` list and a timestamp, and SHALL NOT raise.
5. WHEN a selected gateway cannot be used, for example because its protocol is not HTTP, THE status report SHALL name the reason in `gateway.error` and SHALL NOT probe any target.
6. THE diagnostics module SHALL read the configuration and SHALL NOT write it.

### Requirement 2: Target probing

**User Story:** As an operator, I want every configured target probed through the selected gateway, so that the report shows the real path.

#### Acceptance Criteria

1. WHEN a gateway is reachable, THE Console SHALL probe every configured diagnostic target through that gateway and return one result per target, in configuration order.
2. THE probing SHALL use a bounded worker pool.
3. WHEN the gateway is not reachable, THE status report SHALL contain an empty target list.

### Requirement 3: Node summary

**User Story:** As an operator, I want to see which proxy a node would use, so that a wrong binding is visible before a switch.

#### Acceptance Criteria

1. `node_summary` SHALL return the node's identity, its execution mode, its saved gateway binding, whether the proxy is enabled, its managed state and its verification state.
2. `node_summary` SHALL return the effective proxy URL of the bound gateway, or null when no gateway is bound.
3. WHEN a remote node is bound to a gateway on the loopback interface of the control machine, `node_summary` SHALL carry a warning that the node cannot reach it.
4. WHEN a node is bound to a gateway that no longer exists, `node_summary` SHALL carry a warning that the binding must be chosen again.
5. WHEN a remote node has no gateway binding, `node_summary` SHALL carry a warning that a binding is required before enabling the proxy.
6. `node_summary` SHALL NOT return a password, a token or a node baseline.

### Requirement 4: One proxy URL format

**User Story:** As a maintainer, I want one place that builds a proxy URL, so that the console, the diagnostics and the CLI cannot disagree.

#### Acceptance Criteria

1. THE repository SHALL provide `sdk.config.proxy_url(host, port)` and SHALL use it for the proxy environment and for the gateway URL.
2. `proxy_url` SHALL enclose an IPv6 host in brackets exactly once.

### Requirement 5: Release consistency

**User Story:** As a maintainer, I want one command that reports every version placeholder, so that a release never points at the wrong download.

#### Acceptance Criteria

1. THE repository SHALL provide `tools/kiro/check_release_consistency.py`.
2. THE tool SHALL compare the version in `sdk/config.py`, `pyproject.toml`, `config.example.json`, the download tables of both README files and the newest heading of `CHANGELOG.md`, and SHALL print the value found in each place.
3. THE tool SHALL report a mismatch as a failure and exit with code 1; it SHALL exit with code 0 when every place agrees.
4. THE tool SHALL compare the `no_proxy` value of `config.example.json` with the default of `sdk.config.NO_PROXY`.
5. THE tool SHALL print no configuration content and no URL.

## Requirement 6: Tests

**User Story:** As a maintainer, I want regressions for the shared reports, so that a second entry point cannot drift.

#### Acceptance Criteria

1. THE test suite SHALL cover the status report with and without a gateway, the target order, the node summary and its warnings, the proxy URL format and the release consistency report.
2. Tests SHALL use a temporary `NET_PROXY_CONFIG` and SHALL NOT probe a real target.
3. Runtime code SHALL remain Python 3.8-compatible and use only the standard library.
