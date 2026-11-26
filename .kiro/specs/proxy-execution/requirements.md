# Requirements Document: proxy-execution

## Introduction

An agent that can see the proxy state often wants to try one command through the proxy. The `run_with_proxy` tool runs exactly one command with the proxy variables of a gateway, the way the `with-proxy` command line does. The change must stay inside the tool's own promise: the proxy variables reach the child process only, the parent environment is untouched, and the audit trail records what happened without recording the arguments.

## Glossary

- **Child process**: the one command the tool starts.
- **Process tree**: the child together with every process it starts.
- **Argument hash**: a digest over the full argument list, so that two runs can be compared without storing the arguments.

## Requirements

### Requirement 1: One command, no shell

**User Story:** As an operator, I want the agent to run one command through my proxy, so that it can reproduce a problem without asking me to type it.

#### Acceptance Criteria

1. `run_with_proxy` SHALL accept an `argv` list of one to sixty-four strings and SHALL reject every other shape.
2. THE tool SHALL start the program directly, without a shell and without a command line, so that no argument can be interpreted by a shell.
3. THE tool SHALL resolve the program with `shutil.which` and SHALL refuse a program that is not on the search path.
4. ON Windows, THE tool SHALL refuse a `.bat` or `.cmd` program, because those need a command interpreter.
5. THE tool SHALL refuse an argument that is empty, that contains a NUL, or that exceeds 4096 characters.

### Requirement 2: The proxy reaches the child only

**User Story:** As an operator, I want my own environment untouched, so that the tool cannot change how my shell or my other programs behave.

#### Acceptance Criteria

1. THE tool SHALL pass the proxy variables of the selected gateway to the child process.
2. THE tool SHALL NOT change the environment of the server process, and a test SHALL prove that the environment before and after a run is identical.
3. THE tool SHALL set the same proxy variables as `with-proxy`, in both cases.
4. WHEN no gateway can be selected, THE tool SHALL refuse the run.

### Requirement 3: The working directory stays inside

**User Story:** As an operator, I want the agent to run commands only where I pointed it, so that it cannot wander through my disk.

#### Acceptance Criteria

1. THE tool SHALL accept a `cwd` that lies inside the directory the server was started in.
2. THE tool SHALL refuse a `cwd` outside that directory, including one that reaches outside through `..`.
3. WHEN no `cwd` is given, THE tool SHALL use the directory the server was started in.

### Requirement 4: Bounded time and output

**User Story:** As an operator, I want a command that cannot run forever and cannot fill my disk, so that the agent stays usable.

#### Acceptance Criteria

1. THE tool SHALL accept a timeout of at most 600 seconds and SHALL default to 120 seconds.
2. THE tool SHALL accept an output limit of at most 256 KiB and SHALL default to 64 KiB.
3. WHEN the command exceeds the timeout, THE tool SHALL stop the whole process tree and SHALL report the timeout.
4. WHEN the command writes more than the limit, THE tool SHALL keep the first bytes and SHALL report that it truncated the output.
5. WHEN the command is cancelled, THE tool SHALL stop the whole process tree.

### Requirement 5: The audit trail stays small

**User Story:** As a maintainer, I want to know that a command ran without storing its arguments, so that the audit log cannot become a secret store.

#### Acceptance Criteria

1. WHEN a run finishes, THE tool SHALL write an audit record that holds the program name, the number of arguments, the argument hash and the exit code.
2. THE audit record SHALL NOT hold an argument, a proxy variable or the output of the command.
3. WHEN the run fails before it starts, THE tool SHALL write the same kind of record.

### Requirement 6: Tests

**User Story:** As a maintainer, I want generated arguments, so that an unusual argument cannot slip past the validation.

#### Acceptance Criteria

1. THE test suite SHALL implement P9: the child receives the proxy variables and the parent environment stays the same.
2. THE test suite SHALL cover the argument, directory, timeout and output limits, the refusal of a shell program and the audit record.
3. Tests SHALL NOT run a command that reaches the network or writes outside a temporary directory.
