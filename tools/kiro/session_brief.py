"""Print a short project brief for a new or freshly compacted Kiro session.

Kiro adds this script's stdout to the agent's context (SessionStart and
PostCompact hooks). It reports the branch, uncommitted work and version
consistency, then restates the rules that matter most. It never prints remote
URLs or configuration contents.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _hookio import ROOT, read_event  # noqa: E402

RULES = (
    "Runtime code uses the Python standard library only (Python >= 3.8); Hypothesis and Playwright are test-only.",
    "Proxy variables go to child processes only; node changes are snapshotted, restored and verified "
    "in a fresh login session (.kiro/steering/zero-pollution.md).",
    "Never print git remote URLs or config.json; use `git remote` and tools/kiro/redacted_config.py.",
    "Tests and manual checks use a temporary NET_PROXY_CONFIG and a port other than 8899.",
    "Field data (real IPs, host names, accounts, token usage) stays in scratch/, never in commits.",
    "Ask before deleting files, pushing, tagging, releasing or switching a real node.",
)


def git(*args):
    try:
        completed = subprocess.run(["git", "--no-pager"] + list(args), cwd=str(ROOT), stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.decode("utf-8", errors="replace").strip() if completed.returncode == 0 else ""


def read(path):
    try:
        return (ROOT / path).read_text(encoding="utf-8")
    except OSError:
        return ""


def versions():
    found = {}
    for label, path, pattern in (("sdk/config.py", "sdk/config.py", r'^VERSION\s*=\s*"([^"]+)"'),
                                 ("pyproject.toml", "pyproject.toml", r'^version\s*=\s*"([^"]+)"')):
        matched = re.search(pattern, read(path), re.MULTILINE)
        found[label] = matched.group(1) if matched else "?"
    return found


def brief():
    lines = ["net-proxy-tool session brief"]
    branch = git("branch", "--show-current") or "(detached)"
    head = git("rev-parse", "--short", "HEAD")
    lines.append("- Branch: {}  HEAD: {}".format(branch, head or "?"))
    status = [line for line in git("status", "--porcelain").splitlines() if line.strip()]
    if status:
        modified = sum(1 for line in status if not line.startswith("??"))
        untracked = len(status) - modified
        lines.append("- Uncommitted: {} changed, {} untracked".format(modified, untracked))
    else:
        lines.append("- Working tree clean")
    found = versions()
    values = set(found.values())
    lines.append("- Version: " + ", ".join("{} {}".format(k, v) for k, v in found.items()) +
                 ("" if len(values) == 1 else "  <- mismatch, run tools/kiro/check_release_consistency.py"))
    if not (ROOT / ".kiro" / "settings" / "mcp.json").is_file():
        lines.append("- MCP: .kiro/settings/mcp.json is missing; ask the maintainer to paste docs/kiro/mcp.json.")
    if importlib.util.find_spec("hypothesis") is None:
        lines.append("- Property tests are skipped: run `python -m pip install -r requirements-dev.txt`.")
    lines.append("Rules:")
    lines.extend("- " + rule for rule in RULES)
    return "\n".join(lines)


def main():
    read_event()  # Drain the event so the hook runner never blocks on a full pipe.
    print(brief())
    return 0


if __name__ == "__main__":
    sys.exit(main())
