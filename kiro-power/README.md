# net-proxy-tool power for Kiro

This folder holds the Kiro power that belongs to net-proxy-tool: the small set of checks and
commands that an agent needs while it works on this repository.

## What the power does

The power gives an agent three things:

1. **The state of the repository** — the branch, the uncommitted work, the version agreement and
   the standing rules. The script is `tools/kiro/session_brief.py`.
2. **The checks that must pass** — the standard library rule, the secret scan and the release
   version agreement. The scripts are `tools/kiro/check_stdlib.py`,
   `tools/kiro/scan_secrets.py` and `tools/kiro/check_release_consistency.py`.
3. **The related tests** — the test modules that belong to the files an agent changed. The script
   is `tools/kiro/run_related_tests.py`.

Every one of them runs with a temporary configuration and without touching the configuration of the
operator.

## Installing it

The power uses the scripts in `tools/kiro/` of this repository, so it is installed together with
the repository rather than copied into the IDE:

1. Copy this folder into the powers directory of your Kiro installation, or keep it in the
   repository and point the power at `tools/kiro/`.
2. Make sure `python` on the path is Python 3.8 or newer.
3. Ask the agent for the power by name, or enable it in the agent that should use it.

## The commands

| Command | What it answers |
| --- | --- |
| `python -X utf8 tools/kiro/session_brief.py` | What is the branch, what is uncommitted, do the versions agree |
| `python -X utf8 tools/kiro/check_stdlib.py --all` | Does the runtime still import only the standard library |
| `python -X utf8 tools/kiro/scan_secrets.py --staged` | Does the staged change carry a credential |
| `python -X utf8 tools/kiro/check_release_consistency.py` | Do all the version placeholders agree |
| `python -X utf8 tools/kiro/run_related_tests.py --changed` | Do the tests of the changed files pass |
| `python -X utf8 tools/demo.py` | What does the whole flow look like, without a proxy |

## The rules the power enforces

The power is deliberately read-only. It never writes the configuration, never switches a node and
never publishes anything. The commands that reach outside the machine — a push, a release, a
deployment — need the maintainer's approval in the current conversation.

The sensitive parts of this repository are guarded by the hooks in `.kiro/hooks/`, not by the power:
the shell guard blocks the commands that would print a remote URL or a token, and the file guard
blocks a read of the console configuration.

## The agent that uses it

`.kiro/agents/egress-diagnostician.md` is the custom agent for the questions this power answers:
why does a request not leave through the proxy. It is read-only by design and names the stage
where a request stops instead of guessing.
