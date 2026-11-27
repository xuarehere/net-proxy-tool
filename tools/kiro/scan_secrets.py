"""Find credentials and private identifiers in text, files and git diffs.

The shell-guard hook calls this module before `git commit` and `git push`. It can
also run on its own:

    python -X utf8 tools/kiro/scan_secrets.py --staged
    python -X utf8 tools/kiro/scan_secrets.py --unpushed
    python -X utf8 tools/kiro/scan_secrets.py FILE [FILE ...]

Findings name the kind, location and a masked preview. They never contain the
matched value. A line that carries `pragma: allowlist secret` is skipped, which
is how deliberate test fixtures opt out.
"""
import argparse
import re
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DENYLIST = ROOT / "scratch" / "private-denylist.txt"
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_GIT_OUTPUT = 32 * 1024 * 1024
ALLOW_MARKER = re.compile(r"pragma:\s*allowlist\s+secret", re.IGNORECASE)

PATTERNS = (
    ("github-token", re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,251}")),
    ("github-fine-grained-token", re.compile(r"github_pat_[A-Za-z0-9_]{22,240}")),
    ("aws-access-key-id", re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}")),
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")),
    ("ssh-password", re.compile(r"\"ssh_pass\"\s*:\s*\"(?:[^\"\\]|\\.)+\"")),
    ("url-credentials", re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s/:@'\"<>]+:[^\s/@'\"<>]+@[^\s/'\"<>]")),
)

Finding = namedtuple("Finding", "kind source line preview")


def mask(value):
    """Describe a matched value without revealing it."""
    shown = value[:4] if len(value) > 8 else value[:1]
    return "{}... ({} chars)".format(shown, len(value))


def load_denylist(path=DENYLIST):
    """Return the private literals to block, lower-cased. A missing file means no extra literals."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    entries = (line.strip() for line in lines)
    return tuple(entry.lower() for entry in entries if entry and not entry.startswith("#"))


def scan_line(text, source, line, denylist=()):
    """Return the findings in one line of text."""
    if ALLOW_MARKER.search(text):
        return []
    findings = []
    for kind, pattern in PATTERNS:
        for match in pattern.finditer(text):
            findings.append(Finding(kind, source, line, mask(match.group(0))))
    for entry in denylist:
        # Case-insensitive search on the original text keeps match positions exact;
        # str.lower() can change the length of non-ASCII text before the match.
        matched = re.search(re.escape(entry), text, re.IGNORECASE)
        if matched:
            findings.append(Finding("private-denylist", source, line, mask(matched.group(0))))
    return findings


def scan_text(text, source="<text>", denylist=()):
    """Return the findings in a block of text, with 1-based line numbers."""
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        findings.extend(scan_line(line, source, number, denylist))
    return findings


def scan_diff(diff_text, denylist=(), label=""):
    """Scan only the added lines of a unified diff or `git log -p` output.

    Lines that start with `commit:<sha>` (as produced by `--format=commit:%H`) switch
    the reported source to that commit.
    """
    findings = []
    path = None
    commit = label
    new_line = 0
    old_left = new_left = 0  # Lines still expected in the current hunk.
    hunk = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    for raw in diff_text.splitlines():
        if old_left > 0 or new_left > 0:
            if raw.startswith("+"):
                if path is not None:
                    source = "{}@{}".format(path, commit) if commit else path
                    findings.extend(scan_line(raw[1:], source, new_line, denylist))
                new_line += 1
                new_left -= 1
            elif raw.startswith("-"):
                old_left -= 1
            elif raw.startswith("\\"):
                pass  # "\ No newline at end of file"
            else:
                new_line += 1
                old_left -= 1
                new_left -= 1
            continue
        if raw.startswith("commit:"):
            commit = raw[len("commit:"):].strip()[:12]
            path = None
        elif raw.startswith("diff --git "):
            path = None
        elif raw.startswith("+++ "):
            target = raw[4:].strip()
            path = None if target == "/dev/null" else (target[2:] if target.startswith("b/") else target)
        elif raw.startswith("@@"):
            matched = hunk.match(raw)
            if matched:
                old_left = int(matched.group(1) if matched.group(1) is not None else 1)
                new_line = int(matched.group(2))
                new_left = int(matched.group(3) if matched.group(3) is not None else 1)
    return findings


def scan_file(path, source=None, denylist=()):
    """Scan a text file. Binary or oversized files are skipped."""
    path = Path(path)
    try:
        if path.is_symlink() or path.stat().st_size > MAX_FILE_BYTES:
            return []
        data = path.read_bytes()
    except OSError:
        return []
    if b"\x00" in data[:8192]:
        return []
    return scan_text(data.decode("utf-8", errors="replace"), source or str(path), denylist)


def git(args, cwd=ROOT, timeout=60):
    """Run git and return its decoded stdout. Raises RuntimeError when git fails."""
    command = ["git", "-c", "core.quotepath=false", "--no-pager"] + list(args)
    try:
        completed = subprocess.run(command, cwd=str(cwd), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("git {} failed: {}".format(" ".join(args[:2]), exc)) from exc
    if completed.returncode != 0:
        reason = completed.stderr.decode("utf-8", errors="replace").strip()[:300]
        raise RuntimeError("git {} failed: {}".format(" ".join(args[:2]), reason))
    return completed.stdout[:MAX_GIT_OUTPUT].decode("utf-8", errors="replace")


def scan_staged(cwd=ROOT, denylist=()):
    return scan_diff(git(["diff", "--cached", "--no-color", "--no-ext-diff", "--unified=0"], cwd), denylist)


def scan_worktree(cwd=ROOT, denylist=()):
    return scan_diff(git(["diff", "--no-color", "--no-ext-diff", "--unified=0"], cwd), denylist)


def untracked_files(cwd=ROOT):
    output = git(["ls-files", "--others", "--exclude-standard", "-z"], cwd)
    return [name for name in output.split("\0") if name]


def scan_untracked(paths, cwd=ROOT, denylist=()):
    findings = []
    for name in paths:
        findings.extend(scan_file(Path(cwd) / name, name, denylist))
    return findings


def scan_unpushed(cwd=ROOT, denylist=()):
    """Scan commit messages and added lines of local commits that no remote-tracking branch contains."""
    selection = ["HEAD", "--branches", "--tags", "--not", "--remotes"]
    findings = scan_diff(git(["log", "-p", "--no-color", "--no-ext-diff", "--unified=0",
                              "--format=commit:%H"] + selection, cwd), denylist)
    messages = git(["log", "--format=%H%x00%B%x00"] + selection, cwd).split("\0")
    for sha, body in zip(messages[0::2], messages[1::2]):
        findings.extend(scan_text(body, "commit {} message".format(sha.strip()[:12]), denylist))
    return findings


def format_findings(findings, limit=20):
    lines = ["  {}:{}  {}  {}".format(f.source, f.line, f.kind, f.preview) for f in findings[:limit]]
    if len(findings) > limit:
        lines.append("  ... and {} more".format(len(findings) - limit))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find credentials and private identifiers before they are committed.")
    parser.add_argument("files", nargs="*", help="files to scan")
    parser.add_argument("--staged", action="store_true", help="scan added lines in the git index")
    parser.add_argument("--unpushed", action="store_true", help="scan local commits that are on no remote")
    args = parser.parse_args(argv)
    denylist = load_denylist()
    findings = []
    try:
        if args.staged:
            findings.extend(scan_staged(denylist=denylist))
        if args.unpushed:
            findings.extend(scan_unpushed(denylist=denylist))
    except RuntimeError as exc:
        print("scan_secrets: {}".format(exc), file=sys.stderr)
        return 2
    for name in args.files:
        findings.extend(scan_file(name, denylist=denylist))
    if findings:
        print("scan_secrets: {} finding(s)\n{}".format(len(findings), format_findings(findings)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
