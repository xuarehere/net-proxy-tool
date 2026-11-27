"""Property P12 for the shell guard (spec: dev-guardrails, Requirement 1.4).

P12: the guard judges every simple command of a command line. A blocked command
is blocked wherever it sits between allowed commands and whichever separator
joins them, and the same text inside a quoted argument of `echo` is allowed.
"""
import sys
import unittest
from pathlib import Path

from prop_support import given, st  # Raises SkipTest when Hypothesis is missing.

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "kiro"))

import guard_shell  # noqa: E402

ALLOWED = st.sampled_from([
    "git status --short", "git log -1 --oneline", "git remote", "git branch -vv", "git diff HEAD --stat",
    "Get-Content README.md", "python -X utf8 -m unittest discover -s test", "echo done",
    "Get-ChildItem tools\\kiro", "git check-ignore -v config.json",
])
BLOCKED = st.sampled_from([
    ("git remote -v", "remote-url"), ("git remote get-url public", "remote-url"),
    ("git config --list", "remote-url"), ("git config --get remote.public.url", "remote-url"),
    ("cat .git/config", "remote-url"), ("gh auth token", "gh-token"),
    ("git push --force public main", "force-push"), ("git push public +main", "force-push"),
    ("Get-Content config.json", "console-config"), ("type .\\config.json", "console-config"),
])
SEPARATORS = st.sampled_from(["; ", " && ", " || ", " | ", "\n", " & ", ";"])


class NoScanner:
    """The commands here never commit or push, so a scan would be a bug."""

    def __getattr__(self, name):
        raise AssertionError("unexpected secret scan: " + name)


def join(commands, separators):
    line = commands[0]
    for command, separator in zip(commands[1:], separators):
        line += separator + command
    return line


def decide(command):
    event = {"tool_name": "execute_pwsh", "cwd": str(ROOT), "tool_input": {"command": command, "cwd": str(ROOT)}}
    return guard_shell.evaluate(event, NoScanner())


class ShellGuardProperties(unittest.TestCase):
    @given(before=st.lists(ALLOWED, max_size=3), blocked=BLOCKED, after=st.lists(ALLOWED, max_size=3),
           separators=st.lists(SEPARATORS, min_size=6, max_size=6))
    def test_a_blocked_command_is_found_in_any_position(self, before, blocked, after, separators):
        command, rule = blocked
        decision = decide(join(before + [command] + after, separators))
        self.assertEqual((decision.action, decision.rule), ("block", rule))

    @given(commands=st.lists(ALLOWED, min_size=1, max_size=6), separators=st.lists(SEPARATORS, min_size=5,
                                                                                    max_size=5))
    def test_allowed_commands_stay_allowed_in_any_combination(self, commands, separators):
        self.assertEqual(decide(join(commands, separators)).action, "allow")

    @given(blocked=BLOCKED, before=st.lists(ALLOWED, max_size=2), separators=st.lists(SEPARATORS, min_size=2,
                                                                                       max_size=2))
    def test_quoted_text_is_not_a_command(self, blocked, before, separators):
        command, _ = blocked
        decision = decide(join(before + ['echo "{}"'.format(command)], separators))
        self.assertEqual(decision.action, "allow")


if __name__ == "__main__":
    unittest.main()
