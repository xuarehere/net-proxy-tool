# AGENTS.md

Operating rules for any coding agent that works on net-proxy-tool. They are short on purpose;
the detail lives in the files they point at.

## What this project is

net-proxy-tool routes one command, one Python task or one remote node through an HTTP proxy the
operator already runs, and then reports exactly what happened: the final HTTP status, the hop that
failed, the peer that answered and the account environment on the target.

The runtime is **Python 3.8 or newer with the standard library only**. The release archives bundle
Python, so a machine without one can still run the tool.

## The four rules that never change

1. **The runtime imports nothing outside the standard library.** `pyproject.toml` keeps
   `dependencies` empty, and `tools/kiro/check_stdlib.py` fails the build when a runtime file
   imports a third-party package. A new runtime file must be added to the allowlist in
   `packaging/build_portable.py`.
2. **The proxy reaches exactly one thing.** A child process, a `with ProxySession():` block, or the
   selected account or container of a node. The parent environment, the shell profiles and the
   system proxy settings stay untouched. A node that is switched off restores the content, the mode
   and the absence of every file it manages, and the restoration is verified in a fresh login shell.
3. **An agent reads, it does not write.** The MCP server and the agent in `.kiro/agents/` never
   write the configuration and never switch a node. The console is the only place where a change
   happens.
4. **The secrets stay out of everything.** The console configuration holds SSH passwords. It is
   never printed, never returned by the API and never written to a log. The remote URLs of this
   repository once embedded an access token.

## How a change is made

Every feature gets its own directory under `.kiro/specs/<feature>/` with `requirements.md`,
`design.md` and `tasks.md`. The requirements are written in EARS form, the design names the
interfaces and the correctness properties, and the task list tracks the work.

The order never changes:

1. Write the specification.
2. Write a test that fails.
3. Implement.
4. Run the whole suite with a temporary configuration.
5. Make exactly one commit that names the feature and the task.

The property-based tests in `test/test_prop_*.py` carry the number of their property and the
requirement it validates in the docstring, so a reader can walk from a requirement to the test that
proves it. A bug found by a property is pinned with an `@example`.

## Where things live

| Path | Contents |
| --- | --- |
| `.kiro/specs/<feature>/` | The requirements, the design and the task list of one feature |
| `.kiro/steering/` | The standing rules: product, tech, structure, zero pollution, security, testing, i18n, docs, release, field validation |
| `.kiro/hooks/` | The event hooks that guard and check the work |
| `.kiro/agents/` | The custom agent for egress questions |
| `kiro-power/` | The commands an agent needs here |
| `tools/kiro/` | The scripts the hooks, the power and the release procedure run |
| `web/` | The console: `server.py`, `diagnostics.py`, `local_gateway.py`, `messages.py`, `node_probe.py`, `node_baseline.py`, `static/` |
| `sdk/` | `config.py` (paths, proxy environment, atomic writes, log rotation) and `proxy_session.py` |
| `net_proxy_mcp.py` | The MCP server for coding agents |
| `test/` | The unittest suite; `test_prop_*.py` hold the properties |
| `packaging/` | The portable build, the smoke checks and the browser checks |
| `scratch/` | Git-ignored notes, logs, field data and the submission drafts |

## The commands

```console
python -X utf8 tools/kiro/check_stdlib.py --all
python -X utf8 tools/kiro/scan_secrets.py --staged
python -X utf8 tools/kiro/check_release_consistency.py
python -X utf8 -m unittest discover -s test
python -X utf8 tools/demo.py
```

The test suite needs a temporary configuration and a free port. It never uses port 8899 and never
contacts a real destination.

## What needs the maintainer

A push, a pull request, a merge, a tag, a release, a deployment, a change of a remote node and the
submission to Devpost are the maintainer's decisions. Ask in the current conversation; do not act
on your own. The same applies to deleting a file and to changing a git remote.

Never print a remote URL, a token or the console configuration. Use `git remote` for the names and
`python -X utf8 tools/kiro/redacted_config.py` for a redacted view of the configuration.
