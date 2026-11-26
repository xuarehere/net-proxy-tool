# Requirements Document: mcp-server

## Introduction

A coding agent cannot use a Web console that only speaks to a browser. This feature adds an MCP server so that an agent can ask the same diagnostic questions an operator asks, and get the same answers.

The server is read-only. It reports gateways, probes a gateway through it, checks the configured targets, lists the nodes and runs the same node request the console runs. It never writes the configuration, never switches a node and never changes a gateway.

## Glossary

- **MCP**: the Model Context Protocol that a coding agent uses to call tools.
- **Protocol version**: the version string the client and the server agree on.
- **Meta**: the `_meta` object of a request, which carries the protocol version and the client capabilities.
- **Legacy client**: a client that speaks a protocol version up to `2025-11-25` and handshakes with `initialize`.
- **Tool**: one callable operation of the server.
- **Structured content**: the machine-readable payload of a tool result, beside its human-readable text.

## Requirements

### Requirement 1: A standard-library MCP server

**User Story:** As an operator, I want an agent to reach the console's diagnostics, so that the agent can answer a network question with the same evidence I would see.

#### Acceptance Criteria

1. THE repository SHALL provide `net_proxy_mcp.py`, runnable as `python -X utf8 net_proxy_mcp.py` and installed as the console script `net-proxy-tool-mcp`.
2. THE server SHALL accept `--config PATH` and use that file as the console configuration for the whole session.
3. THE server SHALL read the configuration and SHALL NOT write it, and SHALL NOT switch, provision or restore a node.
4. THE runtime SHALL stay on the Python standard library and Python 3.8.

### Requirement 2: The protocol stream

**User Story:** As an agent, I want a clean protocol stream, so that my messages are not corrupted by a stray print.

#### Acceptance Criteria

1. THE server SHALL read newline-delimited JSON from standard input and write newline-delimited JSON to standard output.
2. Standard output SHALL carry protocol messages only; THE server SHALL redirect ordinary `sys.stdout` writes to standard error after startup.
3. THE server SHALL write every log, warning and traceback to standard error.
4. WHEN standard input reaches its end, THE server SHALL stop and exit.
5. THE server SHALL answer a request with exactly one response that carries the same identifier, and SHALL NOT answer a notification.

### Requirement 3: Version negotiation

**User Story:** As an agent, I want the server to tell me which protocol it speaks, so that a version mismatch is a clear error and not a silent failure.

#### Acceptance Criteria

1. THE server SHALL speak the protocol version `2026-07-28` and accept the legacy versions `2025-11-25`, `2025-06-18`, `2025-03-26` and `2024-11-05`.
2. WHEN a request declares a version that the server does not support, THE server SHALL answer with the error code `-32022` whose data names the supported versions and the requested one.
3. WHEN a request in the current protocol lacks `params._meta["io.modelcontextprotocol/protocolVersion"]` or `params._meta["io.modelcontextprotocol/clientCapabilities"]`, THE server SHALL answer with the error code `-32602`.
4. `params._meta["io.modelcontextprotocol/clientInfo"]` SHALL be optional.
5. WHEN a client asks for `server/discover`, THE server SHALL answer with `resultType` set to `complete`, the supported versions, the server capabilities, the server information under `_meta["io.modelcontextprotocol/serverInfo"]` and the instructions for the agent.
6. WHEN a legacy client asks for `initialize`, THE server SHALL answer with the negotiated version, the server capabilities and the server information.
7. A request that declares no version and is not a handshake SHALL be answered as usual.

### Requirement 4: Tool calls

**User Story:** As an agent, I want a tool answer that carries both text and data, so that I can show the operator a sentence and check the fields myself.

#### Acceptance Criteria

1. `tools/list` SHALL describe every tool with its name, its purpose and its input schema.
2. `tools/call` SHALL answer with `content`, `structuredContent` and `isError`.
3. WHEN a tool reports a failure, THE server SHALL answer with `isError` set to true and SHALL NOT raise.
4. WHEN a tool is not known, THE server SHALL answer with the error code `-32602`.
5. WHEN the arguments do not match the schema, THE server SHALL answer with the error code `-32602`.

### Requirement 5: The diagnostic tools

**User Story:** As an operator, I want the agent to see the same facts as the console, so that its advice matches what I would read.

#### Acceptance Criteria

1. `list_gateways` SHALL return the configured gateways without a password, a token or a credential.
2. `check_gateway` SHALL probe a gateway, given its identifier or its `host:port` address, through the default target `https://www.google.com/`, and SHALL accept a timeout of at most 60 seconds.
3. `check_gateway_targets` SHALL probe the configured diagnostic targets through a gateway and SHALL return one result per target.
4. `list_nodes` SHALL return the node summaries with the effective proxy and the warnings of the shared diagnostics, without a credential.
5. `test_node` SHALL run the same request as the console against one node and SHALL return the ordinary request and the explicit proxy request beside each other.
6. `test_node` SHALL refuse a node that is not registered.
7. NONE of the tools SHALL write the configuration or change a node.

### Requirement 6: Cancellation

**User Story:** As an agent, I want to cancel a running request, so that a slow probe does not block my session.

#### Acceptance Criteria

1. WHEN a `notifications/cancelled` notification names a request, THE server SHALL stop that request if it has not started and SHALL answer it with the error code `-32800` instead of its result.
2. THE server SHALL answer the cancellation notification itself with nothing.
3. A cancelled request SHALL still receive exactly one response.

### Requirement 7: Tests

**User Story:** As a maintainer, I want generated protocol traffic, so that a malformed message cannot slip through.

#### Acceptance Criteria

1. THE test suite SHALL implement P8: every answer line is valid JSON-RPC, every request identifier receives exactly one answer and a notification receives none.
2. THE test suite SHALL cover the version negotiation, the five tools and the cancellation.
3. Tests SHALL use a temporary `NET_PROXY_CONFIG` and SHALL NOT contact a real target, a real proxy or a field node.
