# Kiro and agent guide

This project is developed with an AI coding agent, and the agent's workflow is part of the
repository rather than a private habit. The pages below explain what lives where, so that a
reviewer can follow the work and a contributor can continue it.

[简体中文](kiro.md) · [Quick start](../QUICKSTART_EN.md) · [Operations](operations_en.md)

## What the repository holds

| Path | Contents |
| --- | --- |
| `.kiro/specs/<feature>/` | The requirements, the design and the task list of one feature |
| `.kiro/steering/` | The standing rules that apply to every change |
| `.kiro/hooks/` | The event hooks that guard and check the work |
| `.kiro/agents/` | The custom agent for egress questions |
| `kiro-power/` | The power: the checks and commands an agent needs here |
| `tools/kiro/` | The scripts the hooks, the power and the release procedure run |
| `test/test_prop_*.py` | The property-based tests that each specification names |
| `docs/kiro/mcp.json` | The MCP server registration for the agent |

## The specifications

Every feature gets its own directory with three files:

- `requirements.md` states the requirements in EARS form ("WHEN … THE Console SHALL …").
- `design.md` describes the interfaces, the error handling, the decisions and the correctness
  properties.
- `tasks.md` lists the work and marks what is done.

A change follows the same order every time: the specification, a failing test, the
implementation, the full test suite, and one commit. The property tests carry the number of the
property and the requirement it validates in their docstring, so a reader can walk from a
requirement to the test that proves it.

## The steering files

The steering files hold the rules that do not belong to one feature:

| File | Applies to | Rule |
| --- | --- | --- |
| `product.md` | always | What the tool promises and what it does not do |
| `tech.md` | always | Python 3.8, standard library only, the packaging allowlist |
| `structure.md` | always | Where each kind of file lives |
| `zero-pollution.md` | always | The proxy reaches the child, the account or the container, and only that |
| `security.md` | runtime code | Input validation, redaction, timeouts, process trees |
| `testing.md` | tests | Temporary configuration, free ports, credential-free fixtures |
| `i18n.md` | the console | The language keys and the fallbacks |
| `docs-style.md` | documents | The English and Chinese pairs stay in step |
| `release.md` | releases | The release procedure and the approval steps |
| `field-validation.md` | field checks | Read-only by default, real data stays in `scratch/` |

## The hooks

The hooks in `.kiro/hooks/` run on agent events. The scripts behind them are in `tools/kiro/`:

| Hook | Trigger | What it does |
| --- | --- | --- |
| `shell-guard` | before a command | Blocks commands that print remote URLs, tokens or the console configuration, and force pushes |
| `file-guard` | before a file change | Blocks a read or a write of the console configuration and a write that would add a third-party import to the runtime |
| `stdlib-only` | after a save | Reports any runtime import outside the standard library |
| `related-tests` | end of a turn | Runs the test modules related to the files that changed |
| `task-verify` | after a task | Runs the full suite |
| `session-brief` | session start | Restates the branch, the uncommitted work and the standing rules |
| `docs-pair` | after a document | Reminds the agent to update the other language of a pair |

## The MCP server

`net_proxy_mcp.py` serves the console's diagnostics over the Model Context Protocol, so a
coding agent can read the same state an operator reads:

| Tool | What it does | Automatic approval |
| --- | --- | --- |
| `list_gateways` | Lists the configured gateways | yes |
| `check_gateway` | Sends one request through a gateway | yes |
| `check_gateway_targets` | Probes the configured diagnostic sites | yes |
| `list_nodes` | Lists the nodes with their effective proxy | yes |
| `test_node` | Runs the console's two-path request against one node | no |
| `run_with_proxy` | Runs one command with the proxy variables | no |

The server never writes the configuration and never switches a node. `run_with_proxy` starts
one program without a shell, keeps the proxy variables inside the child process only, bounds
the time and the output, and stops the whole process tree when it is cancelled or times out.
With `inspect` it routes the command through the local observation gateway and reports the
hosts the command reached.

Register it with the agent by copying `docs/kiro/mcp.json` into the agent's own settings
directory; the repository does not carry that file, because the location belongs to the machine.

## The power and the agent

`kiro-power/` holds the commands an agent needs here: the session brief, the standard library
check, the secret scan, the release consistency check, the related tests and the demo. All of them
are read-only.

`.kiro/agents/egress-diagnostician.md` is the custom agent for the question the power answers:
why does a request not leave through the proxy. It names the stage where the request stops and
says what it did not verify.

## The checks

```console
python -X utf8 tools/kiro/check_stdlib.py --all
python -X utf8 tools/kiro/scan_secrets.py --staged
python -X utf8 tools/kiro/check_release_consistency.py
python -X utf8 -m unittest discover -s test
```

The first three run without a network. The test suite needs a temporary configuration and a
free port; it never uses port 8899 and never contacts a real destination.
