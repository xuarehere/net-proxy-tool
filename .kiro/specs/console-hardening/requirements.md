# Requirements Document: console-hardening

## Introduction

The Web console accepts configuration and diagnostic requests from a browser. A malformed JSON value must not reach string, integer, socket or subprocess operations with the wrong type. The console must reject unsupported request formats, keep internal exception details out of HTTP responses and preserve the project's existing zero-dependency and zero-pollution behavior.

## Glossary

- **API endpoint**: a registered `/api/*` route handled by `ProxyConsoleHandler`.
- **JSON endpoint**: a POST API endpoint whose request body is a JSON object.
- **Validation error**: an invalid type, size, range, enum, host, URL or nested selection supplied by a client.
- **Internal error**: an exception that is not an expected validation or binding conflict.
- **Error ID**: a random, non-secret identifier that links a generic HTTP 500 response to one server-side traceback.
- **Sensitive key**: `ssh_pass`, `password`, `token`, `api_key`, `private_key`, `_node_baseline` or `_node_restored_baseline`, ignoring case.

## Requirements

### Requirement 1: Typed request validation

**User Story:** As an operator, I want malformed API input rejected before execution, so that a bad browser or scripted request cannot crash a handler or reach a transport with ambiguous values.

#### Acceptance Criteria

1. WHEN a registered JSON endpoint receives a body, THE Console SHALL require a JSON object and validate every recognized string, integer, Boolean, list and nested node-selection field before invoking its handler.
2. WHEN a recognized field has the wrong JSON type, exceeds its length limit or falls outside its numeric range, THE Console SHALL return HTTP 400 with a JSON error and SHALL NOT invoke a socket, subprocess or remote-node operation.
3. WHEN a recognized string contains an unpaired Unicode surrogate or a NUL, THE Console SHALL return HTTP 400 and SHALL NOT persist the value.
4. WHEN a numeric field is a decimal string, THE Console MAY normalize it to an integer; Boolean values SHALL NOT be accepted as integers.
5. WHEN `nodes` is present, THE Console SHALL require a non-empty bounded array of objects whose `node_id`, revision and gateway fields have valid primitive types.
6. THE typed validator SHALL return only normalized values or raise `ValueError` for every input; it SHALL NOT raise `AttributeError`, `TypeError`, `OverflowError` or another implementation exception for client-controlled values.

### Requirement 2: JSON media type and body limits

**User Story:** As an operator, I want the API to accept one unambiguous request format, so that browsers, proxies and scripts cannot make the server interpret a body differently.

#### Acceptance Criteria

1. WHEN a registered POST endpoint receives a request whose media type is not `application/json`, including a missing Content-Type, THE Console SHALL return HTTP 415 with a JSON response.
2. WHEN `application/json` includes parameters such as `charset=utf-8`, THE Console SHALL accept it.
3. WHEN Content-Length is missing, malformed, negative, duplicated or greater than 1 MiB, THE Console SHALL return HTTP 400 or 413 as appropriate and close the connection when unread bytes could remain.
4. WHEN UTF-8 decoding or JSON parsing fails, including JSON nested deeper than the parser allows, THE Console SHALL return HTTP 400 with a JSON response.
5. WHEN a request carries `Transfer-Encoding` or more than one `Content-Type` header, THE Console SHALL return HTTP 400 with a JSON response and close the connection.

### Requirement 3: Safe internal errors

**User Story:** As a maintainer, I want unexpected failures diagnosable without exposing internals, so that clients receive a stable response and secrets do not leak.

#### Acceptance Criteria

1. WHEN a handler raises a validation error, THE Console SHALL return HTTP 400; a node binding conflict SHALL return HTTP 409.
2. WHEN a handler raises any other exception, THE Console SHALL return HTTP 500 containing `success: false`, a generic error string and an `error_id`; it SHALL NOT include the exception message, traceback, path or request value.
3. WHEN an Internal error occurs, THE Console SHALL write the Error ID, exception type and traceback frames to stderr, without printing the exception message or local variables.
4. WHEN a GET API handler raises unexpectedly, THE Console SHALL apply the same Error ID response and stderr logging policy.
5. ALL JSON error responses SHALL pass through `public_data` before transmission.

### Requirement 4: Host and gateway validation

**User Story:** As an operator, I want diagnostics to reject invalid destinations before opening a socket, so that mistakes are safe and predictable.

#### Acceptance Criteria

1. WHEN `/api/test-host` receives a host or port, THE Console SHALL apply the same host and port validation used by gateways before calling `check_tcp_port`.
2. WHEN the host is empty, malformed, too long or contains control/shell characters, or the port is outside 1–65535, THE Console SHALL return HTTP 400 and SHALL NOT call `check_tcp_port`.
3. WHEN a gateway protocol is read from an API request, THE Console SHALL trim it, normalize it to lower case and accept only the supported HTTP protocol.
4. WHEN a gateway is updated, THE normalized protocol SHALL be persisted and endpoint-change detection SHALL compare normalized values.

### Requirement 5: Bounded request reads

**User Story:** As an operator, I want idle clients bounded, so that one incomplete request cannot occupy a worker forever.

#### Acceptance Criteria

1. WHEN a request connection is set up, THE Console SHALL set its socket timeout to 60 seconds before reading headers or a body.
2. WHEN a socket read times out, THE Console SHALL close that connection without changing configuration or node state.

### Requirement 6: Audit warning channel

**User Story:** As a user of the stdio MCP server and console logs, I want diagnostics separated from protocol output, so that a logging failure cannot corrupt machine-readable stdout.

#### Acceptance Criteria

1. WHEN `write_audit_log` cannot append an entry, THE Console SHALL write the warning to stderr, not stdout.
2. THE warning SHALL NOT contain audit details, request bodies or credentials.

### Requirement 7: Regression properties

**User Story:** As a maintainer, I want broad generated-input coverage, so that boundary cases remain fixed across platforms.

#### Acceptance Criteria

1. THE test suite SHALL implement P1 through P6 from the design with Hypothesis and the shared CI/dev profiles.
2. Tests SHALL use a temporary `NET_PROXY_CONFIG`, local sockets on port 0 and mocked transports; they SHALL NOT use port 8899, a real proxy, the internet or a field node.
3. Runtime changes SHALL remain Python 3.8-compatible and use only the standard library.
