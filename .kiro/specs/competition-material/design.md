# Design Document: competition-material

## Overview

`tools/demo.py` runs the whole flow of the tool in one process and narrates it. The documents in `scratch/kiroween/` describe the project for a reviewer and for the maintainer's own submission.

## The demo

```console
python -X utf8 tools/demo.py
```

The demo:

1. creates a temporary configuration and points the console at it;
2. starts the local observation gateway and saves it as a gateway;
3. sends one request through that gateway to `https://example.com/`, or to a local origin when the network is unavailable;
4. prints the final HTTP status, the proxy that carried the request and the hosts the gateway saw;
5. stops the gateway and removes the temporary configuration.

Every step prints a line that begins with a step number and a sentence, so that a recording can follow the output without an extra narration script.

The demo never touches the configuration of the operator: it sets `NET_PROXY_CONFIG` to a file in a temporary directory for the whole run and restores it afterwards.

### The fallback origin

When `https://example.com/` cannot be reached, the demo starts a local HTTP server on port 0 and uses that as the target. The console then shows the same facts, and the demo says plainly that it used the local origin because the network was unavailable.

## The documents

| File | Purpose |
| --- | --- |
| `devpost.md` | The Devpost entry: the description, the story, the links and the checklist for the submission |
| `video-script.md` | The screen-by-screen recording script |
| `social-post.md` | The announcement post |
| `blog-draft.md` | The technical article draft |
| `checklist.md` | What is ready and what the maintainer still has to do |

All of them live under `scratch/`, which is git-ignored: they are working material for the submission, not part of the published repository.

## The honest timeline

The entry describes four stages, because that is how the work happened:

| Stage | What it produced |
| --- | --- |
| Antigravity | The base versions: the console, the CLI, the SDK and the node lifecycle |
| Codex | v1.4.0 to v1.4.3: the diagnostics, the node revisions and the guides |
| Kiro | The specifications, the steering files, the hooks and the property tests |
| Claude Code | v1.5.0: the request hardening, the access token, the MCP server, the local gateway and the release |

No document claims that one of them did the work of the others.

## The measurable facts

The documents quote only what the repository proves:

- the test suite and the platforms the release checks cover;
- zero runtime dependencies, with the standard library only;
- the proxy isolation: the variables reach the child, the account or the container, and nothing else;
- the read-only MCP server and the local observation gateway that needs no proxy.

## Testing strategy

Running `tools/demo.py` is the test: it must report a result, show the contacted host and leave no listener behind. The documents are reviewed against the checklist.
