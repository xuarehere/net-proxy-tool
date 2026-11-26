# Requirements Document: local-gateway

## Introduction

net-proxy-tool needs an HTTP proxy to demonstrate what it does. A reviewer who does not have a proxy cannot try the tool at all. The local observation gateway is a small proxy that ships with the tool: it listens on the loopback interface, forwards the request and records which hosts it saw.

## Glossary

- **Observation gateway**: the local proxy that the tool ships with.
- **Tunnel**: one forwarded connection.
- **Upstream**: another proxy the observation gateway forwards to, instead of connecting to the origin itself.
- **Destination port**: the port of the origin the request goes to.
- **Record**: one line of the gateway's memory that names a connection it handled.

## Requirements

### Requirement 1: A loopback-only proxy

**User Story:** As an operator, I want the shipped gateway to be reachable only from this machine, so that it cannot become an open proxy.

#### Acceptance Criteria

1. THE gateway SHALL listen on `127.0.0.1` only.
2. WHEN the gateway starts, THE gateway SHALL report the port it listens on.
3. THE gateway SHALL be reachable over HTTP and over a CONNECT tunnel.

### Requirement 2: A bounded destination set

**User Story:** As an operator, I want the gateway to reach only the ports I allow, so that it cannot be used to reach an internal service.

#### Acceptance Criteria

1. THE gateway SHALL allow the destination ports 80 and 443, and SHALL accept further ports only when the operator names them.
2. WHEN a request names a destination port that is not allowed, THE gateway SHALL answer HTTP 403 and SHALL NOT open a connection.
3. THE gateway SHALL refuse a destination host that is empty, malformed or too long.

### Requirement 3: Bounded resources

**User Story:** As an operator, I want the gateway to stop using resources when it is misused, so that it cannot fill the machine.

#### Acceptance Criteria

1. THE gateway SHALL hold at most 64 tunnels at the same time and SHALL answer HTTP 503 when it holds that many.
2. THE gateway SHALL read at most 16 KiB of request head and SHALL answer HTTP 431 when the head is larger.
3. THE gateway SHALL give up on a connection that takes longer than 10 seconds to establish.
4. THE gateway SHALL close a connection that carries no traffic for 60 seconds.
5. THE gateway SHALL release its tunnel slot when a connection ends.

### Requirement 4: An optional upstream

**User Story:** As an operator, I want the gateway to forward to my own proxy when I have one, so that the tool can be used behind an existing setup.

#### Acceptance Criteria

1. THE gateway SHALL accept an upstream address of the form `host:port`.
2. WHEN an upstream is configured, THE gateway SHALL forward the CONNECT or the absolute request to that upstream.
3. WHEN the upstream cannot be reached, THE gateway SHALL answer HTTP 502 and SHALL record the failure.

### Requirement 5: What the gateway saw

**User Story:** As an operator, I want to see which hosts a request went to, so that I can explain the behaviour of the tool.

#### Acceptance Criteria

1. THE gateway SHALL keep the last 200 connections in memory.
2. A record SHALL name the method, the destination host, the destination port, the outcome and the byte counts, and SHALL NOT keep the request or the response body.
3. WHEN the gateway starts, THE earlier records are gone.
4. THE gateway SHALL provide a configuration record with the identifier `local-gateway`, the kind `local` and its port, so that the console can offer it as a gateway.

### Requirement 6: A command line

**User Story:** As an operator, I want to run the gateway on its own, so that I can point another tool at it.

#### Acceptance Criteria

1. THE repository SHALL provide `python -m web.local_gateway` with the options `--port`, `--upstream` and `--allow-port`.
2. THE command line SHALL print the address it listens on.
3. THE command line SHALL stop on an interrupt.

### Requirement 7: Tests

**User Story:** As a maintainer, I want generated requests, so that an unusual request cannot slip through.

#### Acceptance Criteria

1. THE test suite SHALL implement P10: the gateway answers any request without failing, and refuses a request that is not a proxy request or that names a forbidden port.
2. THE test suite SHALL cover the tunnel, the absolute request, the port allowlist, the record list and the configuration record.
3. Tests SHALL use local sockets on port 0 and SHALL NOT reach the internet.
