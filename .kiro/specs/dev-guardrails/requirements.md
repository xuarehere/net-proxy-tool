# Requirements Document: dev-guardrails

## Introduction

net-proxy-tool v1.5.0 is built with a coding agent that runs shell commands, reads and writes files, commits and pushes. This repository has specific risks: its git remotes have carried URLs with embedded access tokens, the maintainer's `config.json` stores SSH passwords, field work produces real addresses that must not be published, and the runtime must stay on the Python standard library. This feature adds Kiro hooks, steering and test infrastructure that stop those mistakes before they happen and run the right tests without being asked.

## Glossary

- **Agent**: the Kiro agent working in this repository.
- **Shell guard**: `tools/kiro/guard_shell.py` registered as a PreToolUse hook for shell tools and for MCP tools that run commands.
- **File guard**: the same script registered as a PreToolUse hook for file read, write, append, replace, delete and move tools.
- **Scanner**: `tools/kiro/scan_secrets.py`.
- **Runtime file**: a Python file at the repository root or under `sdk/`, `web/`, `bin/` or `tools/`.
- **Console configuration**: `config.json` at the repository root.
- **Denylist**: `scratch/private-denylist.txt`, one private literal (address, host or account name) per line. Git-ignored.
- **Block**: the hook exits with code 2 and writes the reason to stderr, so Kiro does not run the tool and shows the reason to the agent.

## Requirements

### Requirement 1: Commands that print credentials

**User Story:** As the maintainer, I want commands that print git remote URLs or stored tokens to be blocked, so that a token in a remote URL never reaches a transcript, log or screenshot.

#### Acceptance Criteria

1. WHEN the agent runs a command containing `git remote -v`, `git remote -vv` or another short-option cluster containing `v`, `git remote --verbose`, `git remote get-url`, `git remote show <name>`, `git config` with `-l`, `--list`, `list`, `--get-regexp` or `--get-urlmatch`, `git config` naming a `remote.*.url`, `remote.*.pushurl` or `url.*` key, `git ls-remote --get-url` or `git credential fill`, THE Shell guard SHALL block it and name a safe alternative.
2. WHEN a command can show or change `.git/config`, THE Shell guard SHALL block it.
3. WHEN a command runs `gh auth token` or `gh auth status` with `--show-token` or `-t`, directly or through a command wrapper, THE Shell guard SHALL block it.
4. THE Shell guard SHALL judge every simple command of a command line separated by `;`, `&&`, `||`, `|`, `&` or a newline outside quotes, every command passed to another shell (`cmd /c`, `powershell -Command`, `pwsh`, `bash -c`, `sh -c`, `wsl`, `Invoke-Expression`), and every `$( )` or backtick substitution.
5. THE Shell guard SHALL allow quoted text that is only an argument, such as a commit message or `echo "git remote -v"`, and SHALL allow `git remote`, `git remote show` without a name, `git remote set-url`, `git fetch`, `git branch -vv` and `gh auth status`.
6. WHEN an MCP tool call carries an `argv` list instead of a command string, THE Shell guard SHALL apply the same rules to that argument list.

### Requirement 2: Force pushes

**User Story:** As the maintainer, I want force and mirror pushes blocked, so that the agent cannot rewrite published history.

#### Acceptance Criteria

1. WHEN the agent runs `git push` with `--force`, `-f` alone or inside a flag cluster, `--force-with-lease` with or without a value, `--force-if-includes`, `--mirror` or a refspec starting with `+`, THE Shell guard SHALL block it.

### Requirement 3: Secret scan before commit and push

**User Story:** As the maintainer, I want commits and pushes checked for credentials and private field data, so that nothing private is published by mistake.

#### Acceptance Criteria

1. WHEN the agent runs `git commit`, THE Shell guard SHALL scan the added lines of the staged diff and the text of the command line, which holds the commit message.
2. WHEN the same command line runs `git add` or the commit uses `-a` or `--all`, THE Shell guard SHALL also scan unstaged changes and the untracked files that `git add` names; for `-A`, `--all`, `.`, `*` or `:/` it SHALL scan all untracked files.
3. WHEN the agent runs `git push`, THE Shell guard SHALL scan the added lines and messages of every local commit reachable from a local branch, tag or the current `HEAD` that no remote-tracking branch contains.
4. THE Scanner SHALL detect GitHub classic tokens, GitHub fine-grained tokens, AWS access key ids, private key headers, non-empty `"ssh_pass"` values, credentials inside URLs and, ignoring case, every Denylist entry.
5. IF the scan finds anything, THEN THE Shell guard SHALL block the command and report each finding as source, line, kind and a preview that shows at most four characters of the match.
6. THE Scanner SHALL skip a line that contains `pragma: allowlist secret`.
7. IF git fails during a scan, THEN THE Shell guard SHALL allow the command and print a warning that the scan was skipped.
8. THE Scanner SHALL run on its own with `--staged`, `--unpushed` or file arguments, and exit with code 1 when it finds anything.
9. WHEN an untracked path is a symbolic link, THE Scanner SHALL NOT follow the link or read its target.

### Requirement 4: Console configuration

**User Story:** As the maintainer, I want the agent kept away from my console configuration, so that SSH passwords are never displayed or overwritten.

#### Acceptance Criteria

1. WHEN a shell command can show or change the Console configuration (a file-reading or file-changing program, an interpreter, a `ReadAll*` or `WriteAll*` call, or an unquoted redirection in the same simple command), THE Shell guard SHALL block it.
2. WHEN a file tool reads, writes, appends to, replaces text in, deletes or moves the Console configuration, THE File guard SHALL block it.
3. THE guards SHALL allow other files named `config.json`, `config.example.json`, and commands that only name the path without reading it, such as setting `NET_PROXY_CONFIG` or `git check-ignore`.
4. THE repository SHALL provide `tools/kiro/redacted_config.py`, which prints the active configuration with the same redaction as the console API: no passwords, tokens or node baselines.

### Requirement 5: Standard library only at runtime

**User Story:** As a user who downloads a portable archive, I want the runtime to need nothing beyond Python's standard library, so that the tool starts on a machine without internet access.

#### Acceptance Criteria

1. WHEN a write tool would leave a Runtime file importing a module that is neither in the standard library nor part of this repository, THE File guard SHALL block the write and name the file, line and module.
2. THE check SHALL allow imports inside a `try` statement with a handler for `ImportError` or `ModuleNotFoundError`, relative imports, and modules of this repository.
3. IF the text that a write would leave does not parse, THEN THE File guard SHALL allow the write, because a multi-step edit can pass through such states.
4. WHEN a Python file or `pyproject.toml` is saved, THE stdlib hook SHALL check the saved Runtime files, or every Runtime file when the event names none, and check that `[project].dependencies` is empty; on a violation it SHALL exit with code 2 and list each violation on stderr.
5. THE check SHALL work on Python 3.8 and later, using a built-in module list where `sys.stdlib_module_names` is missing; modules introduced after Python 3.8 SHALL require an `ImportError` fallback.

### Requirement 6: Tests run without being asked

**User Story:** As the maintainer, I want related tests to run after the agent changes code, so that a regression shows up in the same turn.

#### Acceptance Criteria

1. WHEN an agent turn ends, THE related-tests hook SHALL run the test modules related to the Python files that differ from HEAD, untracked files included: at most four modules within 100 seconds.
2. IF those files have the same content as at the previous run, THEN THE related-tests hook SHALL skip the run.
3. WHEN a spec task completes, THE task hook SHALL run the full suite.
4. THE hooks SHALL run tests with `NET_PROXY_CONFIG` in a new temporary directory and without `NET_PROXY_ACCESS_TOKEN`.
5. IF tests fail or time out, THEN THE hooks SHALL exit with code 2 and write the unittest summary and the end of the output to stderr.

### Requirement 7: Session context

**User Story:** As the maintainer, I want each new or compacted session to start with the project's state and rules, so that the agent does not work from stale assumptions.

#### Acceptance Criteria

1. WHEN a session starts or a conversation has been compacted, THE session-brief hook SHALL print the branch, the short `HEAD` hash without the commit subject, the number of changed and untracked files, whether `sdk/config.py` and `pyproject.toml` versions match, whether `.kiro/settings/mcp.json` or Hypothesis is missing, and the standing rules.
2. THE brief SHALL contain no URL and no configuration content, and SHALL stay under 3000 characters.

### Requirement 8: Documentation pairs

**User Story:** As a reader of either language, I want English and Chinese documents to stay in step.

#### Acceptance Criteria

1. WHEN a file of an English and Chinese documentation pair is saved, THE docs-pair hook SHALL remind the agent to update the other file of the pair in the same change.

### Requirement 9: Guard robustness and evidence

**User Story:** As the maintainer, I want the guards to fail safe for normal work and to leave a record, so that a broken guard never stops all work and I can see what they did.

#### Acceptance Criteria

1. IF a hook event is empty, is not a JSON object, or names no command or path, THEN THE guards SHALL allow the call.
2. IF a guard fails internally, THEN THE guard SHALL allow the call and print a warning on stderr.
3. THE hook scripts SHALL use the Python standard library only.
4. WHEN a guard blocks a call or a check runs, THE hook SHALL append the time, hook, decision, rule and a short detail without secret values to `scratch/kiroween/hook-events.jsonl`, unless `NPT_HOOK_EVENT_LOG` is set to an empty value.

### Requirement 10: Property-based test infrastructure

**User Story:** As a contributor, I want property-based tests that run the same way locally and in CI.

#### Acceptance Criteria

1. THE repository SHALL list test-only tools with exact versions in `requirements-dev.txt`, and CI SHALL install them before the unit suite.
2. WHEN Hypothesis is not installed, THE property test modules SHALL be reported as skipped with an install hint.
3. THE property tests SHALL run 100 examples per property when `CI` is set and 50 otherwise, without a deadline; `HYPOTHESIS_PROFILE` SHALL override the choice.
