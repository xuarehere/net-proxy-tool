# Requirements Document: console-local-gateway

## Introduction

The tool ships a local observation gateway so that a reviewer without a proxy can still try it. The console has to offer that gateway, start it, stop it and show what it saw. A remote node must never be bound to it, because it listens on the loopback interface of the control machine.

## Requirements

### Requirement 1: The console owns the observation gateway

**User Story:** As an operator, I want the console to start and stop the observation gateway, so that I do not have to run a second program.

#### Acceptance Criteria

1. THE Console SHALL start the observation gateway when the configuration already holds a `local-gateway` record, and SHALL report the port it uses.
2. THE Console SHALL answer `GET /api/local-gateway` with the state of the gateway: whether it runs, its port, its configuration record, its allowed destination ports and its recent connections.
3. WHEN the console is asked to start the gateway, THE Console SHALL start it on the loopback interface and SHALL add or update its configuration record.
4. WHEN the console is asked to stop the gateway, THE Console SHALL stop it and SHALL remove its configuration record.
5. THE Console SHALL never write a gateway record that names another machine.

### Requirement 2: Two obvious ways to start

**User Story:** As a reviewer, I want to see what the tool does without preparing a proxy, so that I can try it in a minute.

#### Acceptance Criteria

1. THE first-run screen SHALL offer a button that starts the observation gateway and saves it as a gateway.
2. THE first-run screen SHALL offer a button that starts the observation gateway and sends one request through it at the same time.
3. THE demo request SHALL use `https://example.com/`, which every network can reach.
4. THE screen SHALL show the address of the gateway and the hosts it saw.

### Requirement 3: A remote node cannot use it

**User Story:** As an operator, I want the console to refuse a remote node that is bound to the local gateway, so that I do not enable a proxy that cannot work.

#### Acceptance Criteria

1. WHEN a node with a remote execution mode is bound to a gateway of the kind `local`, THE Console SHALL refuse the change with a clear message.
2. A local node SHALL be allowed to use the local gateway.
3. THE refusal SHALL name the reason: the gateway listens on the loopback interface.

### Requirement 4: Tests

**User Story:** As a maintainer, I want the console's gateway handling covered, so that the demo path keeps working.

#### Acceptance Criteria

1. THE test suite SHALL cover the start, the stop, the state and the refusal for a remote node.
2. `packaging/test_browser_local_gateway.py` SHALL drive the two entry points in Chromium. The browser check runs in CI, where Chromium is installed.
3. Tests SHALL use a temporary `NET_PROXY_CONFIG` and SHALL NOT reach the internet.
