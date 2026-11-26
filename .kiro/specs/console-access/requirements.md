# Requirements Document: console-access

## Introduction

The console serves loopback by default, but it can be published beyond loopback: the container image binds `0.0.0.0`, and an operator may set `NET_PROXY_BIND` or `--bind`. A console that is reachable from another machine must prove that the visitor is allowed, must record who acted, must keep its own logs from growing without bound, and must warn when the configuration file is readable by other accounts.

## Glossary

- **Access token**: a secret that a non-loopback client must present to use the console.
- **Loopback client**: a client whose address is a loopback address, including an IPv4-mapped IPv6 address such as `::ffff:127.0.0.1`.
- **Console host name**: a name or address that identifies this machine, used for the Host header check.
- **Audit record**: one JSON line in `audit.log`.
- **Generation**: one rotated log file, for example `audit.log.1`.

## Requirements

### Requirement 1: Access token for non-loopback clients

**User Story:** As an operator, I want a console that is reachable from another machine to require a secret, so that anyone who can reach the port cannot read my configuration or switch my nodes.

#### Acceptance Criteria

1. WHEN the console is bound to a non-loopback address, THE Console SHALL require an Access token from every client whose address is not loopback.
2. WHEN the console is bound to a loopback address and no `NET_PROXY_ACCESS_TOKEN` is set, THE Console SHALL NOT require an Access token and SHALL NOT print one.
3. THE Access token SHALL come from `NET_PROXY_ACCESS_TOKEN` when that variable holds a non-empty value; otherwise THE Console SHALL generate a random token at startup.
4. WHEN THE Console generates a token, IT SHALL print one access link that contains the token at startup, and SHALL NOT print it again.
5. WHEN a non-loopback client requests the console root with a correct `token` query parameter, THE Console SHALL reply HTTP 302 to `/` and set a cookie named `npt_access` with the token, marked `HttpOnly`, `SameSite=Strict` and `Path=/`.
6. WHEN a non-loopback client presents a wrong token, THE Console SHALL reply HTTP 401 with an explanation page and SHALL NOT set a cookie.
7. WHEN a non-loopback client presents the correct cookie, THE Console SHALL serve the request normally.
8. THE Access token SHALL NOT appear in an API response body, an audit record, an error message or a request log line.

### Requirement 2: Host header for a published console

**User Story:** As an operator, I want to open the console by its own machine name or address, so that a published console is reachable at the address I publish.

#### Acceptance Criteria

1. WHEN the console requires an Access token, THE Console SHALL accept a Host header that names this machine, including its host name and its non-loopback addresses.
2. WHEN the console does not require an Access token, THE Console SHALL keep its existing strict Host list of `localhost`, `127.0.0.1`, `::1` and the bound address.
3. THE Console SHALL NOT perform a public DNS lookup to decide whether a Host name is local.
4. WHEN a request carries an unknown Host, THE Console SHALL reply HTTP 403 as before.

### Requirement 3: Audit records name the client and the time

**User Story:** As a maintainer, I want to know which client performed an action and when, so that an audit trail can be reviewed.

#### Acceptance Criteria

1. WHEN an audit record is written, THE Console SHALL store an ISO 8601 timestamp.
2. WHEN an audit record is written, THE Console SHALL store the client address of the request that caused it.
3. THE Audit record SHALL NOT contain a password, a token or a full command line.

### Requirement 4: Bounded logs

**User Story:** As an operator, I want log files that cannot fill the disk, so that a long-running console keeps working.

#### Acceptance Criteria

1. WHEN `audit.log` reaches 5 MiB, THE Console SHALL rotate it, keeping at most three generations.
2. WHEN `console.log` reaches 10 MiB, THE launcher SHALL rotate it, keeping at most one previous generation.
3. Rotation SHALL NOT lose the current generation's content in a way that corrupts the newest file.

### Requirement 5: Configuration file permissions

**User Story:** As an operator, I want to be told when my configuration file can be read by other accounts, so that I can tighten it.

#### Acceptance Criteria

1. WHEN the console starts and the configuration file is readable by group or other on a POSIX system, THE Console SHALL print a warning on stderr that names the file and the mode.
2. THE warning SHALL NOT contain any configuration content.
3. WHEN the file is not readable by group or other, or the platform has no POSIX modes, THE Console SHALL print nothing.

### Requirement 6: Reliable configuration writes

**User Story:** As a Windows operator, I want a saved configuration to survive a momentarily locked file, so that a save does not fail because another program opened it.

#### Acceptance Criteria

1. WHEN replacing the configuration file fails because another process holds it open, THE Console SHALL retry a bounded number of times with a growing delay.
2. WHEN the retries are exhausted, THE Console SHALL report the original error.
3. A failed write SHALL NOT leave a temporary file behind and SHALL NOT damage the previous configuration.

### Requirement 7: Exact node identity

**User Story:** As an operator, I want a node's recorded account name to be exactly the account name, so that the console does not think the account changed when it did not.

#### Acceptance Criteria

1. WHEN the read-only baseline records the account name, THE Console SHALL record it without a trailing newline byte.
2. THE recorded account name SHALL equal the account name used by the local identity helper.

## Requirements

### Requirement 8: Tests

**User Story:** As a maintainer, I want regressions for every new behaviour, so that the access rules keep working.

#### Acceptance Criteria

1. THE test suite SHALL cover the token flow, the Host gate, the audit fields, both rotations, the permission warning, the write retry and the account-name fix.
2. Tests SHALL use a temporary `NET_PROXY_CONFIG`, local sockets on port 0 and isolated configuration; they SHALL NOT use port 8899, a real proxy, the internet or a field node.
3. Runtime code SHALL remain Python 3.8-compatible and use only the standard library.
