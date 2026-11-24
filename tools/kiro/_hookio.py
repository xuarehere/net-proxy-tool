"""Shared helpers for the Kiro hook scripts in this directory.

The scripts run with whatever Python the hook command finds, so they use the
standard library only and never fail loudly on malformed hook events.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENT_LOG = ROOT / "scratch" / "kiroween" / "hook-events.jsonl"

# Keys that carry file paths in Kiro file events and in tool inputs.
PATH_KEYS = frozenset((
    "path", "file_path", "filePath", "file", "files", "paths", "file_paths", "filePaths",
    "target_file", "targetFile", "targetFiles", "sourcePath", "destinationPath",
))


def read_event(stream=None):
    """Return the hook event object, or {} when STDIN is empty, a terminal or not a JSON object.

    Bytes are decoded as UTF-8 whatever the console code page is, and a leading
    byte order mark is dropped: Windows PowerShell 5.1 adds one when it pipes text
    into a program.
    """
    stream = sys.stdin if stream is None else stream
    try:
        if stream is None or stream.isatty():
            return {}
        raw = stream.buffer.read() if hasattr(stream, "buffer") else stream.read()
    except (OSError, ValueError):
        return {}
    text = raw.decode("utf-8-sig", errors="replace") if isinstance(raw, bytes) else raw.lstrip("\ufeff")
    if not text.strip():
        return {}
    try:
        value = json.loads(text)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def event_paths(event):
    """Collect the file paths named anywhere in a hook event, in order and without duplicates."""
    found = []

    def visit(value, key, depth):
        if depth > 8:
            return
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, child_key, depth + 1)
        elif isinstance(value, list):
            for child in value:
                visit(child, key, depth + 1)
        elif isinstance(value, str) and key in PATH_KEYS and value.strip():
            found.append(value.strip())

    visit(event, None, 0)
    return list(dict.fromkeys(found))


def repo_relative(path, cwd=None):
    """Return the POSIX path of `path` relative to the repository root, or None if it lies outside."""
    if not path:
        return None
    base = cwd or str(ROOT)
    absolute = os.path.abspath(os.path.join(base, os.path.expanduser(str(path))))
    root = os.path.normcase(os.path.abspath(str(ROOT)))
    candidate = os.path.normcase(absolute)
    if candidate == root:
        return ""
    if not candidate.startswith(root + os.sep):
        return None
    return absolute[len(root) + 1:].replace("\\", "/")


def record(hook, decision, rule, detail=""):
    """Append one hook decision to the local, git-ignored event log. Never raises.

    NPT_HOOK_EVENT_LOG overrides the log path; an empty value disables logging (used by tests).
    """
    target = os.environ.get("NPT_HOOK_EVENT_LOG", str(EVENT_LOG))
    if not target:
        return
    try:
        log = Path(target)
        log.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "hook": hook,
            "decision": decision,
            "rule": rule,
            "detail": str(detail)[:200],
        }
        with log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass
