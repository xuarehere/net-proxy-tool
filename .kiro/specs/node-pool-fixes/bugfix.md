# Bugfix: node-pool-fixes

## Introduction

The worker node pool has four defects that an operator notices while using it: two nodes tested at the same time lose one of their results, the action menu of a node is cut off by the table, some text is too dim to read, and a remote node can be bound to a gateway on the control machine's loopback interface without any warning.

## Requirements

### Requirement 1: Every node keeps its own result

**User Story:** As an operator, I want to test two nodes at the same time and read both results, so that I can compare them.

#### Acceptance Criteria

1. WHEN two nodes are tested at the same time, THE Console SHALL show the result of each node in its own row.
2. WHEN a node is tested again, THE Console SHALL replace the result of that node only.
3. A late answer for an older test of the same node SHALL NOT replace a newer one.
4. THE Console SHALL remember the last result of each node, so that a redraw does not lose it.

### Requirement 2: The action menu is never cut off

**User Story:** As an operator, I want the action menu of a node to open completely, so that I can reach every action.

#### Acceptance Criteria

1. THE action menu SHALL be positioned relative to the viewport, so that no container can clip it.
2. THE action menu SHALL open below its button and stay inside the viewport.
3. WHEN the page is scrolled or resized, THE action menu SHALL follow its button.

### Requirement 3: Readable text

**User Story:** As an operator, I want to read the dim text, so that I do not miss a state.

#### Acceptance Criteria

1. THE dim text colour SHALL reach a contrast ratio of at least 4.5 to 1 against the card background in the dark theme.
2. THE light theme SHALL keep its own readable value.

### Requirement 4: A remote node is warned about a loopback gateway

**User Story:** As an operator, I want to be told that a remote node cannot reach a loopback gateway, so that I do not enable a proxy that cannot work.

#### Acceptance Criteria

1. WHEN a remote node is switched on and its bound gateway listens on the loopback interface of the control machine, THE Console SHALL ask for a confirmation first.
2. THE confirmation SHALL name the gateway address and say that the node cannot reach it.
3. WHEN the operator confirms, THE Console SHALL continue with the switch.
4. WHEN the operator declines, THE Console SHALL not switch the node.
5. A local node SHALL NOT be asked, because a local node runs on the control machine.

### Requirement 5: The console reports its own addresses

**User Story:** As an operator, I want to see which address the console is reachable at, so that I can give a reachable gateway address to a remote node.

#### Acceptance Criteria

1. THE Console SHALL answer `GET /api/host-addresses` with the names and addresses of this machine.
2. THE answer SHALL mark which addresses are on the loopback interface.
3. THE answer SHALL hold no configuration content and no credential.

## Testing strategy

`test/test_node_pool_fixes.py` covers the new endpoint, the address classification, the presence of
the front-end fixes and the contrast ratio of the dim text.

`packaging/test_browser_nodes.py` drives the console in Chromium: two nodes tested at the same time keep both results, the action menu opens complete, and a remote node bound to a loopback gateway asks for a confirmation. The browser check runs in CI, where Chromium is installed.

## Note

The gateway writes its connection record after it answers the client, so a test that reads the
records straight after the answer can miss them. The two gateway tests wait for the record instead
of assuming that it is already there; the behaviour of the gateway did not change.
