# Requirements Document: mcp-inspect

## Introduction

An agent that runs a command through the proxy usually wants to know which hosts the command actually reached. The `inspect` mode of `run_with_proxy` answers that: the command goes through a temporary local observation gateway, and the answer names the hosts it saw.

The traffic still leaves through the selected gateway, so the observation does not change what the command does.

## Glossary

- **Inspect mode**: the `inspect` option of `run_with_proxy`.
- **Observation gateway**: the temporary local gateway that the inspect mode starts.
- **Contacted host**: a destination host that the observation gateway saw in a request.

## Requirements

### Requirement 1: The command is observed, not redirected

**User Story:** As an operator, I want to see which hosts a command reaches, so that I can explain what the command did over my proxy.

#### Acceptance Criteria

1. WHEN `run_with_proxy` is called with `inspect` set to true, THE tool SHALL start a temporary observation gateway and SHALL point the child's proxy variables at it.
2. THE observation gateway SHALL forward to the selected gateway, so that the command still leaves through the gateway the operator chose.
3. THE tool SHALL stop the observation gateway when the command ends, whatever the outcome.
4. WHEN `inspect` is not set or is false, THE tool SHALL behave exactly as before, and SHALL NOT start a gateway.

### Requirement 2: The contacted hosts

**User Story:** As an agent, I want the names of the contacted hosts, so that I can report them.

#### Acceptance Criteria

1. THE answer SHALL carry a `contacted_hosts` list when the inspect mode ran.
2. Every entry SHALL name a host and a port.
3. A host that appears more than once SHALL appear once in the list.
4. THE list SHALL hold no path, no header and no body.
5. THE list SHALL be empty when the command reached no host.

### Requirement 3: The observation is bounded

**User Story:** As an operator, I want the observation to be short-lived and local, so that it cannot become a service of its own.

#### Acceptance Criteria

1. THE observation gateway SHALL listen on the loopback interface only.
2. THE observation gateway SHALL reach only the destination ports 80 and 443.
3. THE observation gateway SHALL hold at most 64 tunnels and SHALL give up on a connection that stays idle for 60 seconds.
4. WHEN the command is stopped by a timeout or a cancellation, THE observation gateway SHALL be stopped as well.

### Requirement 4: Tests

**User Story:** As a maintainer, I want the inspect mode covered, so that the observation cannot change the command's behaviour.

#### Acceptance Criteria

1. THE test suite SHALL cover that the command still leaves through the selected gateway, that the contacted hosts are reported and that no gateway survives the call.
2. Tests SHALL use a local proxy on port 0 and SHALL NOT reach the internet.
