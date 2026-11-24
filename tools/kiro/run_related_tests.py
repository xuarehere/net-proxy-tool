"""Run the unit tests related to changed files, or the whole suite.

Each changed Python file maps to at most MAX_MODULES test modules (a test module
maps to itself; a source module maps to the test files that name it, most
references first). Tests run with a disposable NET_PROXY_CONFIG so the
maintainer's configuration is never touched.

    python -X utf8 tools/kiro/run_related_tests.py --changed      # Stop hook
    python -X utf8 tools/kiro/run_related_tests.py                # files named in a hook event on STDIN
    python -X utf8 tools/kiro/run_related_tests.py web/server.py  # named files
    python -X utf8 tools/kiro/run_related_tests.py --all          # full suite (PostTaskExec)

`--changed` looks at files that differ from HEAD (untracked files included) and
skips the run when their contents are the same as at the previous run, so an
agent turn that changed nothing costs nothing and a failure is reported once.

Exit codes: 0 passed or nothing to run, 2 failures or timeout (details on stderr).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _hookio import ROOT, event_paths, read_event, record, repo_relative  # noqa: E402

TEST_DIR = ROOT / "test"
STATE_FILE = ROOT / "scratch" / "kiroween" / "related-tests-state.json"
MAX_MODULES = 4
FILE_BUDGET_S = 100
SUITE_BUDGET_S = 560
IGNORED_DIRS = ("build/", "dist/", "scratch/", "packaging/", "docs/", ".kiro/", ".git/")


def git_paths(*args):
    """Return the NUL-separated paths printed by a git command, or [] when git fails."""
    try:
        completed = subprocess.run(["git", "-c", "core.quotepath=false", "--no-pager"] + list(args) + ["-z"],
                                   cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []
    return [name for name in completed.stdout.decode("utf-8", errors="replace").split("\0") if name]


def changed_files():
    """Repository-relative paths that differ from HEAD, untracked files included."""
    names = git_paths("diff", "--name-only", "HEAD") + git_paths("ls-files", "--others", "--exclude-standard")
    return sorted(set(names))


def fingerprint(rels):
    """Hash the names and current contents of the given files."""
    digest = hashlib.sha256()
    for rel in sorted(rels):
        try:
            content = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        except OSError:
            content = "missing"
        digest.update("{}\0{}\n".format(rel, content).encode("utf-8"))
    return digest.hexdigest()


def load_state(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def save_state(path, state):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def related_modules(rels, test_dir=TEST_DIR, limit=MAX_MODULES):
    """Map repository-relative paths to test module file names."""
    chosen = []
    for rel in rels:
        if not rel or not rel.endswith(".py") or rel.startswith(IGNORED_DIRS):
            continue
        path = Path(rel)
        if rel.startswith("test/"):
            if path.name.startswith("test_") and (test_dir / path.name).is_file():
                chosen.append(path.name)
            continue
        stem = path.parent.name if path.stem == "__init__" else path.stem
        pattern = re.compile(r"\b{}\b".format(re.escape(stem)))
        scored = []
        for test in sorted(test_dir.glob("test_*.py")):
            count = len(pattern.findall(test.read_text(encoding="utf-8", errors="replace")))
            if test.stem.startswith(("test_" + stem, "test_prop_" + stem)):
                count += 1000
            if count:
                scored.append((-count, test.name))
        chosen.extend(name for _, name in sorted(scored))
    return list(dict.fromkeys(chosen))[:limit]


def test_environment(scratch):
    """Return the environment for test runs, with the configuration redirected into `scratch`."""
    environment = dict(os.environ)
    environment.update(NET_PROXY_CONFIG=os.path.join(scratch, "config.json"), PYTHONUTF8="1",
                       PYTHONDONTWRITEBYTECODE="1")
    environment.pop("NET_PROXY_ACCESS_TOKEN", None)
    return environment


def run(args, budget, environment):
    """Run a unittest command line and return (returncode, combined output)."""
    command = [sys.executable, "-X", "utf8", "-m", "unittest"] + args
    try:
        completed = subprocess.run(command, cwd=str(ROOT), env=environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=max(budget, 1))
    except subprocess.TimeoutExpired as exc:
        output = (exc.output or b"").decode("utf-8", errors="replace")
        return None, output
    return completed.returncode, completed.stdout.decode("utf-8", errors="replace")


def tail(text, lines=40):
    return "\n".join(text.strip().splitlines()[-lines:])


def summary(text):
    matched = re.findall(r"^(Ran \d+ tests? in [\d.]+s)\s*$\s*^((?:OK|FAILED).*)$", text, re.MULTILINE)
    return "; ".join(" ".join(item) for item in matched) or "no unittest summary"


def run_modules(modules, budget=FILE_BUDGET_S):
    deadline = time.monotonic() + budget
    failures = []
    with tempfile.TemporaryDirectory(prefix="npt-hook-tests-") as scratch:
        environment = test_environment(scratch)
        for module in modules:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failures.append("{}: not run, the {} s budget for related tests ran out".format(module, budget))
                break
            code, output = run(["discover", "-s", "test", "-p", module], remaining, environment)
            if code is None:
                failures.append("{}: timed out\n{}".format(module, tail(output)))
                break
            if code != 0:
                failures.append("{}: {}\n{}".format(module, summary(output), tail(output)))
    return failures


def run_suite(budget=SUITE_BUDGET_S):
    with tempfile.TemporaryDirectory(prefix="npt-hook-suite-") as scratch:
        code, output = run(["discover", "-s", "test"], budget, test_environment(scratch))
    if code is None:
        return ["full suite timed out after {} s\n{}".format(budget, tail(output, 60))]
    if code != 0:
        return ["full suite: {}\n{}".format(summary(output), tail(output, 60))]
    return []


def run_changed(state_path=STATE_FILE):
    """Run the tests related to files changed since HEAD. Returns (label, failures), or None to skip."""
    rels = [rel for rel in changed_files() if rel.endswith(".py")]
    modules = related_modules(rels)
    if not modules:
        return None
    stamp = fingerprint(set(rels) | {"test/" + module for module in modules})
    if load_state(state_path).get("fingerprint") == stamp:
        return None
    failures = run_modules(modules)
    save_state(state_path, {"fingerprint": stamp, "modules": modules, "passed": not failures,
                            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    return ", ".join(modules), failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run tests related to changed files, or the whole suite.")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--all", action="store_true", help="run the full suite")
    parser.add_argument("--changed", action="store_true",
                        help="run tests for files changed since HEAD, unless unchanged since the last run")
    args = parser.parse_args(argv)
    if args.all:
        failures = run_suite()
        label = "full suite"
    elif args.changed:
        outcome = run_changed()
        if outcome is None:
            return 0
        label, failures = outcome
    else:
        if args.paths:
            rels = [repo_relative(path) for path in args.paths]
        else:
            event = read_event()
            rels = [repo_relative(path, event.get("cwd")) for path in event_paths(event)]
        modules = related_modules(rels)
        if not modules:
            return 0
        failures = run_modules(modules)
        label = ", ".join(modules)
    record("related-tests", "fail" if failures else "pass", "tests", label)
    if failures:
        print("related-tests: failures in {}\n\n{}".format(label, "\n\n".join(failures)), file=sys.stderr)
        return 2
    print("related-tests: passed ({})".format(label))
    return 0


if __name__ == "__main__":
    sys.exit(main())
