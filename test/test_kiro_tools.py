"""Checks for the Kiro hook scripts in tools/kiro (spec: dev-guardrails)."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "kiro"))
QUIET = dict(os.environ, NPT_HOOK_EVENT_LOG="")  # Test runs must not add to the hook evidence log.

import _hookio  # noqa: E402
import check_stdlib  # noqa: E402
import guard_shell  # noqa: E402
import run_related_tests  # noqa: E402
import scan_secrets  # noqa: E402
import session_brief  # noqa: E402

# Fixture secrets are assembled at run time so this file never contains one.
GITHUB_TOKEN = "gh" + "p_" + "A1b2C3d4" * 4 + "Z9y8"
AWS_KEY = "AK" + "IA" + "ABCDEFGHIJ012345"
PRIVATE_KEY = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"
SSH_PASSWORD = '"ssh' + '_pass": "hunter2"'


class FakeScanner:
    """Stands in for scan_secrets in guard tests and records which scans ran."""
    format_findings = staticmethod(scan_secrets.format_findings)

    def __init__(self, findings=(), untracked=()):
        self.findings = list(findings)
        self.untracked = list(untracked)
        self.calls = []

    def load_denylist(self):
        return ()

    def scan_text(self, text, source, denylist):
        self.calls.append(("text", source))
        return scan_secrets.scan_text(text, source, denylist)

    def scan_staged(self, cwd, denylist):
        self.calls.append(("staged",))
        return list(self.findings)

    def scan_worktree(self, cwd, denylist):
        self.calls.append(("worktree",))
        return []

    def untracked_files(self, cwd):
        return list(self.untracked)

    def scan_untracked(self, paths, cwd, denylist):
        self.calls.append(("untracked", tuple(paths)))
        return []

    def scan_unpushed(self, cwd, denylist):
        self.calls.append(("unpushed",))
        return list(self.findings)


def shell_event(command, tool="execute_pwsh"):
    return {"hook_event_name": "PreToolUse", "cwd": str(ROOT), "tool_name": tool,
            "tool_input": {"command": command, "cwd": str(ROOT)}}


class HookIoTests(unittest.TestCase):
    def test_event_paths_collects_nested_paths_once(self):
        event = {"tool_input": {"path": "a.py"}, "files": ["b.py", "a.py"], "other": {"note": "x.py"}}
        self.assertEqual(_hookio.event_paths(event), ["a.py", "b.py"])

    def test_read_event_tolerates_invalid_input(self):
        self.assertEqual(_hookio.read_event(io.StringIO("")), {})
        self.assertEqual(_hookio.read_event(io.StringIO("not json")), {})
        self.assertEqual(_hookio.read_event(io.StringIO("[1, 2]")), {})
        self.assertEqual(_hookio.read_event(io.StringIO('{"a": 1}')), {"a": 1})
        self.assertEqual(_hookio.read_event(io.StringIO('\ufeff{"a": 1}\r\n')), {"a": 1})
        stream = io.TextIOWrapper(io.BytesIO(b'\xef\xbb\xbf{"path": "\xe4\xb8\xad.py"}'), encoding="cp1252")
        self.assertEqual(_hookio.read_event(stream), {"path": "\u4e2d.py"})

    def test_repo_relative(self):
        self.assertEqual(_hookio.repo_relative(str(ROOT / "web" / "server.py")), "web/server.py")
        self.assertEqual(_hookio.repo_relative("web/server.py"), "web/server.py")
        self.assertIsNone(_hookio.repo_relative(str(ROOT.parent / "elsewhere.py")))


class HookRegistrationTests(unittest.TestCase):
    def test_all_eight_hooks_have_the_expected_trigger_and_action(self):
        expected = {
            "docs-pair.json": ("PostFileSave", "agent", None, None),
            "file-guard.json": ("PreToolUse", "command", "python -X utf8 tools/kiro/guard_shell.py", 30),
            "related-tests.json": ("Stop", "command", "python -X utf8 tools/kiro/run_related_tests.py --changed", 150),
            "session-brief-after-compaction.json": (
                "PostCompact", "command", "python -X utf8 tools/kiro/session_brief.py", 30),
            "session-brief.json": ("SessionStart", "command", "python -X utf8 tools/kiro/session_brief.py", 30),
            "shell-guard.json": ("PreToolUse", "command", "python -X utf8 tools/kiro/guard_shell.py", 60),
            "stdlib-only.json": ("PostFileSave", "command", "python -X utf8 tools/kiro/check_stdlib.py", 30),
            "task-verify.json": ("PostTaskExec", "command", "python -X utf8 tools/kiro/run_related_tests.py --all", 600),
        }
        hook_dir = ROOT / ".kiro" / "hooks"
        self.assertEqual({path.name for path in hook_dir.glob("*.json")}, set(expected))
        for name, (trigger, action_type, command, timeout) in expected.items():
            document = json.loads((hook_dir / name).read_text(encoding="utf-8"))
            self.assertEqual(document.get("version"), "v1", name)
            self.assertEqual(len(document.get("hooks", [])), 1, name)
            hook = document["hooks"][0]
            self.assertEqual(hook.get("trigger"), trigger, name)
            self.assertEqual(hook.get("action", {}).get("type"), action_type, name)
            if command is not None:
                self.assertEqual(hook["action"].get("command"), command, name)
                self.assertEqual(hook["action"].get("timeout"), timeout, name)
        self.assertIn("run_with_proxy", json.loads((hook_dir / "shell-guard.json").read_text(
            encoding="utf-8"))["hooks"][0]["matcher"])
        self.assertIn("read", json.loads((hook_dir / "file-guard.json").read_text(
            encoding="utf-8"))["hooks"][0]["matcher"])


class StdlibCheckTests(unittest.TestCase):
    def test_third_party_import_is_reported_with_line(self):
        problems = check_stdlib.check_source("import json\nimport requests\nfrom sdk import config\n", "web/x.py")
        self.assertEqual(len(problems), 1)
        self.assertIn("web/x.py:2", problems[0])
        self.assertIn("'requests'", problems[0])

    def test_optional_import_inside_import_error_handler_is_allowed(self):
        source = "try:\n    import yaml\nexcept ImportError:\n    yaml = None\n"
        self.assertEqual(check_stdlib.check_source(source, "web/x.py"), [])
        source = "try:\n    import yaml\nexcept ValueError:\n    yaml = None\n"
        self.assertEqual(len(check_stdlib.check_source(source, "web/x.py")), 1)

    def test_local_and_relative_imports_are_allowed(self):
        source = "from web import server\nimport sdk.config\nfrom . import sibling\nimport with_proxy\n"
        self.assertEqual(check_stdlib.check_source(source, "web/x.py"), [])

    def test_syntax_error_is_reported(self):
        self.assertIn("syntax error", check_stdlib.check_source("def broken(:\n", "web/x.py")[0])

    def test_runtime_classification(self):
        for rel in ("launcher.py", "web/server.py", "sdk/config.py", "bin/session_env.py", "tools/kiro/guard_shell.py"):
            self.assertTrue(check_stdlib.is_runtime(rel), rel)
        for rel in ("test/test_management.py", "packaging/smoke.py", "docs/render_architecture.py",
                    "scratch/x.py", "README.md", "build/lib/web/server.py"):
            self.assertFalse(check_stdlib.is_runtime(rel), rel)

    def test_python38_fallback_rejects_modules_added_after_python38(self):
        with mock.patch.object(check_stdlib, "stdlib_names", return_value=check_stdlib.FALLBACK_STDLIB):
            for module in ("graphlib", "tomllib", "zoneinfo"):
                problems = check_stdlib.check_source("import {}\n".format(module), "web/x.py")
                self.assertEqual(len(problems), 1, module)

    def test_repository_runtime_and_pyproject_are_clean(self):
        self.assertEqual(check_stdlib.check_paths(list(check_stdlib.runtime_files()) + ["pyproject.toml"]), [])

    def test_declared_dependencies_fallback_parser(self):
        text = '[project]\nname = "x"\ndependencies = [\n  "requests>=2",\n]\n'
        self.assertEqual(check_stdlib.declared_dependencies(text), ["requests>=2"])
        self.assertEqual(check_stdlib.declared_dependencies('[project]\ndependencies = []\n'), [])

    def test_declared_dependencies_fallback_only_reads_project_table(self):
        text = ('[tool.example]\ndependencies = ["tool-only"]\n'
                '[project]\nname = "x"\ndependencies = []\n'
                '[project.optional-dependencies]\ntest = ["pytest"]\n')
        with mock.patch.dict(sys.modules, {"tomllib": None}):
            self.assertEqual(check_stdlib.declared_dependencies(text), [])

    def test_hook_exit_code_reports_violation_on_stderr(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT / "web")) as directory:
            target = Path(directory) / "violation.py"
            target.write_text("import requests\n", encoding="utf-8")
            event = json.dumps({"hook_event_name": "PostFileSave", "file_path": str(target)})
            completed = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/kiro/check_stdlib.py")],
                                       input=event.encode(), capture_output=True, cwd=str(ROOT), timeout=60, env=QUIET)
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertIn(b"requests", completed.stderr)


class ShellGuardTests(unittest.TestCase):
    def decide(self, command, scanner=None, tool="execute_pwsh"):
        return guard_shell.evaluate(shell_event(command, tool), scanner or FakeScanner())

    def test_commands_that_print_remote_urls_are_blocked(self):
        for command in ("git remote -v", "git remote -vv", "git -C . remote --verbose",
                        "git remote get-url public",
                        "git remote show public", "git config --get remote.public.url", "git config -l",
                        "git config --list --show-origin", "git config list", "git config --get-regexp url",
                        "git ls-remote --get-url public", "Get-Content .git/config", "type .git\\config",
                        "cat ./.git/config", "echo start; git remote -v", "git status && git remote -v | more",
                        "git credential fill", "gh auth token", "gh auth status --show-token",
                        'cmd /c "git remote -v > remotes.txt"', "powershell -NoProfile -Command \"git remote -v\"",
                        "bash -c 'git status && git config --list'", 'echo "$(git remote -v)"',
                        "echo `git remote -v`", 'iex "git remote get-url public"', "wsl git remote -v",
                        'cmd /c "type .git\\config"', "awk '{print}' .git/config",
                        "command gh auth token", "env gh auth status -t"):
            decision = self.decide(command)
            self.assertEqual(decision.action, "block", command)
        self.assertIn("git remote", self.decide("git remote -v").message)
        self.assertEqual(self.decide('cmd /c "type config.json"').rule, "console-config")
        self.assertEqual(self.decide('echo "$(Get-Content config.json)"').rule, "console-config")

    def test_safe_git_commands_are_allowed(self):
        for command in ("git remote", "git remote show", "git status --short", "git log -1 --oneline",
                        "git config user.name", "git branch -vv", "git diff HEAD", "git fetch public",
                        "git remote set-url public https://github.com/xuarehere/net-proxy-tool.git",
                        'git commit -m "explain why git remote -v is blocked"', "gh auth status",
                        "Get-Content README.md", "python -X utf8 -m unittest discover -s test",
                        'cmd /c "python -X utf8 -m unittest discover -s test > out.log 2>&1"',
                        'echo "git remote -v"', "echo 'use `git remote` for names'"):
            decision = self.decide(command)
            self.assertEqual(decision.action, "allow", command)

    def test_force_and_mirror_pushes_are_blocked(self):
        for command in ("git push --force", "git push -f public main", "git push -uf public x",
                        "git push --force-with-lease=main public main", "git push public +main",
                        "git push --mirror public"):
            self.assertEqual(self.decide(command).rule, "force-push", command)

    def test_push_scans_unpushed_commits(self):
        clean = FakeScanner()
        self.assertEqual(self.decide("git push -u public kiro/v1.5.0", clean).action, "allow")
        self.assertIn(("unpushed",), clean.calls)
        finding = scan_secrets.Finding("github-token", "web/x.py@abc", 3, "ghp_... (40 chars)")
        decision = self.decide("git push public kiro/v1.5.0", FakeScanner([finding]))
        self.assertEqual((decision.action, decision.rule), ("block", "secret-scan"))
        self.assertIn("web/x.py@abc:3", decision.message)
        self.assertNotIn(GITHUB_TOKEN, decision.message)

    def test_commit_scans_staged_changes_and_the_message(self):
        scanner = FakeScanner()
        self.assertEqual(self.decide('git commit -m "Add guard"', scanner).action, "allow")
        self.assertIn(("staged",), scanner.calls)
        self.assertNotIn(("worktree",), scanner.calls)
        decision = self.decide('git commit -m "token {}"'.format(GITHUB_TOKEN), FakeScanner())
        self.assertEqual(decision.rule, "secret-scan")
        self.assertNotIn(GITHUB_TOKEN, decision.message)

    def test_add_then_commit_also_scans_worktree_and_named_untracked_files(self):
        scanner = FakeScanner(untracked=["tools/kiro/new.py", "scratch/other.txt", "web/new.py"])
        self.decide('git add tools/kiro web/new.py; git commit -m "x"', scanner)
        self.assertIn(("worktree",), scanner.calls)
        self.assertIn(("untracked", ("tools/kiro/new.py", "web/new.py")), scanner.calls)
        scanner = FakeScanner(untracked=["a.txt", "b/c.txt"])
        self.decide('git add -A && git commit -m "x"', scanner)
        self.assertIn(("untracked", ("a.txt", "b/c.txt")), scanner.calls)
        scanner = FakeScanner()
        self.decide('git commit -am "x"', scanner)
        self.assertIn(("worktree",), scanner.calls)

    def test_add_then_commit_scans_untracked_files_selected_by_wildcard(self):
        scanner = FakeScanner(untracked=["web/one.py", "web/two.txt", "sdk/other.py"])
        self.decide('git add "web/*.py" && git commit -m "x"', scanner)
        self.assertIn(("untracked", ("web/one.py",)), scanner.calls)

    def test_console_configuration_reads_are_blocked(self):
        for command in ("Get-Content config.json", "cat ./config.json", "type .\\config.json",
                        "Copy-Item config.json backup.json", "awk '{print}' config.json",
                        "Get-Content '{}'".format(ROOT / "config.json")):
            self.assertEqual(self.decide(command).rule, "console-config", command)
        for command in ("Get-Content config.example.json", "Get-Content docs/kiro/mcp.json"):
            self.assertEqual(self.decide(command).action, "allow", command)
        read = {"tool_name": "read_file", "tool_input": {"path": str(ROOT / "config.json")}}
        self.assertEqual(guard_shell.evaluate(read, FakeScanner()).rule, "console-config")
        relative = {"tool_name": "read_file", "cwd": str(ROOT), "tool_input": {"path": "config.json"}}
        self.assertEqual(guard_shell.evaluate(relative, FakeScanner()).rule, "console-config")
        other = {"tool_name": "read_file", "tool_input": {"path": str(ROOT / "config.example.json")}}
        self.assertEqual(guard_shell.evaluate(other, FakeScanner()).action, "allow")

    def test_indirect_reads_and_changes_of_console_configuration_are_blocked(self):
        for command in ("$c = Get-Content config.json", "(Get-Content .\\config.json | ConvertFrom-Json).nodes",
                        "python -c \"print(open('config.json').read())\"", "[IO.File]::ReadAllText('config.json')",
                        "Set-Content config.json '{}'", "echo {} > config.json", "Remove-Item config.json",
                        "bash -c 'cat config.json'"):
            self.assertEqual(self.decide(command).rule, "console-config", command)
        for command in ('$env:NET_PROXY_CONFIG = Join-Path $tmp "config.json"', "git check-ignore -v config.json",
                        "python -X utf8 tools/kiro/redacted_config.py", "python -m web.server --port 18900",
                        "Get-Content $env:TEMP\\npt\\config.json"):
            self.assertEqual(self.decide(command).action, "allow", command)

    def test_writes_that_add_third_party_runtime_imports_are_blocked(self):
        def write(tool, path, **tool_input):
            tool_input["path"] = str(path)
            return guard_shell.evaluate({"tool_name": tool, "cwd": str(ROOT), "tool_input": tool_input},
                                        FakeScanner())

        decision = write("fs_write", ROOT / "web" / "new_module.py", text="import json\nimport requests\n")
        self.assertEqual((decision.action, decision.rule), ("block", "stdlib-only"))
        self.assertIn("'requests'", decision.message)
        self.assertEqual(write("fs_write", "test/test_new.py", text="import hypothesis\n").action, "allow")
        self.assertEqual(write("fs_write", "web/new_module.py", text="try:\n    import yaml\n"
                                                                     "except ImportError:\n    yaml = None\n").action,
                         "allow")
        self.assertEqual(write("read_file", "web/new_module.py").action, "allow")
        with tempfile.TemporaryDirectory(dir=str(ROOT / "web")) as directory:
            target = Path(directory) / "existing.py"
            target.write_text("import json\n\nVALUE = 1\n", encoding="utf-8")
            decision = write("str_replace", target, oldStr="import json\n", newStr="import json\nimport yaml\n")
            self.assertEqual(decision.rule, "stdlib-only")
            self.assertEqual(write("str_replace", target, oldStr="VALUE = 1", newStr="VALUE = (").action, "allow")
            self.assertEqual(write("str_replace", target, oldStr="absent", newStr="import yaml").action, "allow")
            self.assertEqual(write("fs_append", target, text="import requests").rule, "stdlib-only")
            self.assertEqual(write("fs_append", target, text="import sdk").action, "allow")

    def test_mcp_argv_is_checked_like_a_command(self):
        event = {"tool_name": "mcp_net_proxy_tool_run_with_proxy",
                 "tool_input": {"argv": ["git", "remote", "-v"], "gateway_id": "local-gateway"}}
        self.assertEqual(guard_shell.evaluate(event, FakeScanner()).rule, "remote-url")
        event["tool_input"]["argv"] = ["git", "ls-remote", "https://github.com/xuarehere/net-proxy-tool"]
        self.assertEqual(guard_shell.evaluate(event, FakeScanner()).action, "allow")

    def test_malformed_events_are_allowed(self):
        for event in ({}, {"tool_input": "text"}, {"tool_input": {"command": 3}}, {"tool_input": {"argv": [1]}}):
            self.assertEqual(guard_shell.evaluate(event, FakeScanner()).action, "allow")

    def test_hook_process_blocks_with_exit_code_two(self):
        completed = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/kiro/guard_shell.py")],
                                   input=json.dumps(shell_event("git remote -v")).encode(),
                                   capture_output=True, cwd=str(ROOT), timeout=60, env=QUIET)
        self.assertEqual(completed.returncode, 2)
        self.assertIn(b"git remote", completed.stderr)
        self.assertEqual(completed.stdout, b"")
        completed = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/kiro/guard_shell.py")],
                                   input=json.dumps(shell_event("git status")).encode(),
                                   capture_output=True, cwd=str(ROOT), timeout=60, env=QUIET)
        self.assertEqual((completed.returncode, completed.stdout), (0, b""))


class SecretScanTests(unittest.TestCase):
    def test_known_secret_kinds_are_found_and_masked(self):
        url_credentials = "https://" + "user:" + "pw@" + "example.com/"
        text = "a = {}\nkey {}\n{}\n{}\nproxy = {}\n".format(
            GITHUB_TOKEN, AWS_KEY, PRIVATE_KEY, SSH_PASSWORD, url_credentials)
        findings = scan_secrets.scan_text(text, "sample.txt")
        self.assertEqual([f.kind for f in findings], ["github-token", "aws-access-key-id", "private-key",
                                                      "ssh-password", "url-credentials"])
        self.assertEqual([f.line for f in findings], [1, 2, 3, 4, 5])
        rendered = scan_secrets.format_findings(findings)
        for secret in (GITHUB_TOKEN, AWS_KEY, "hunter2"):
            self.assertNotIn(secret, rendered)

    def test_allowlist_marker_and_empty_passwords(self):
        self.assertEqual(scan_secrets.scan_text(GITHUB_TOKEN + "  # pragma: allowlist secret"), [])
        self.assertEqual(scan_secrets.scan_text('"ssh' + '_pass": ""'), [])
        self.assertEqual(scan_secrets.scan_text("target.get('ssh_pass') and https://github.com/x"), [])

    def test_denylist_is_case_insensitive_and_loaded_from_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deny.txt"
            path.write_text("# comment\n\nSecret-Host.example\n", encoding="utf-8")
            denylist = scan_secrets.load_denylist(path)
        self.assertEqual(denylist, ("secret-host.example",))
        findings = scan_secrets.scan_text("ssh root@SECRET-HOST.example", denylist=denylist)
        self.assertEqual([f.kind for f in findings], ["private-denylist"])
        self.assertEqual(scan_secrets.load_denylist(Path(directory) / "missing.txt"), ())

    def test_diff_scan_reports_added_lines_only_with_new_line_numbers(self):
        diff = "\n".join([
            "commit:0123456789abcdef", "diff --git a/web/x.py b/web/x.py", "--- a/web/x.py", "+++ b/web/x.py",
            "@@ -10,3 +10,4 @@", " context", "-removed " + AWS_KEY, "+added " + GITHUB_TOKEN,
            "+++ an added line that looks like a header", " more",
            "diff --git a/gone.txt b/gone.txt", "--- a/gone.txt", "+++ /dev/null", "@@ -1 +0,0 @@",
            "-" + GITHUB_TOKEN, ""])
        findings = scan_secrets.scan_diff(diff)
        self.assertEqual([(f.kind, f.source, f.line) for f in findings],
                         [("github-token", "web/x.py@0123456789ab", 11)])

    def test_real_repository_index_scan_runs(self):
        self.assertIsInstance(scan_secrets.scan_staged(), list)

    def test_scan_file_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "outside.txt"
            target.write_text(GITHUB_TOKEN, encoding="utf-8")
            link = Path(directory) / "link.txt"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest("file symlinks are unavailable: {}".format(exc))
            self.assertEqual(scan_secrets.scan_file(link), [])

    def test_unpushed_scan_includes_detached_head(self):
        calls = []

        def fake_git(args, cwd=scan_secrets.ROOT, timeout=60):
            calls.append(list(args))
            return ""

        with mock.patch.object(scan_secrets, "git", side_effect=fake_git):
            self.assertEqual(scan_secrets.scan_unpushed(), [])
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("HEAD" in args for args in calls))


class RelatedTestsTests(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(run_related_tests.related_modules(["test/test_management.py"]), ["test_management.py"])
        self.assertIn("test_kiro_tools.py", run_related_tests.related_modules(["tools/kiro/guard_shell.py"]))
        self.assertEqual(run_related_tests.related_modules(["README.md", "packaging/smoke.py", None]), [])
        self.assertLessEqual(len(run_related_tests.related_modules(["web/server.py"])), run_related_tests.MAX_MODULES)

    def test_changed_mode_runs_once_per_state_of_the_changed_files(self):
        calls = []
        with mock.patch.object(run_related_tests, "changed_files",
                               return_value=["README.md", "tools/kiro/guard_shell.py"]), \
                mock.patch.object(run_related_tests, "run_modules",
                                  side_effect=lambda modules: calls.append(modules) or []), \
                tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            label, failures = run_related_tests.run_changed(state)
            self.assertIn("test_kiro_tools.py", label)
            self.assertEqual(failures, [])
            self.assertIsNone(run_related_tests.run_changed(state))
            self.assertTrue(json.loads(state.read_text(encoding="utf-8"))["passed"])
        self.assertEqual(len(calls), 1)
        with mock.patch.object(run_related_tests, "changed_files", return_value=["README.md"]):
            self.assertIsNone(run_related_tests.run_changed(Path(directory) / "unused.json"))

    def test_summary_parsing(self):
        output = "....\n----\nRan 4 tests in 0.5s\n\nFAILED (failures=1)\n"
        self.assertEqual(run_related_tests.summary(output), "Ran 4 tests in 0.5s FAILED (failures=1)")


class RedactedConfigTests(unittest.TestCase):
    def test_redacted_view_hides_passwords_and_baselines(self):
        secret = "pw-" + "7f3a9c"
        config = {"version": "1.4.3", "gateways": [{"id": "gw", "host": "127.0.0.1", "port": 7890,
                                                    "protocol": "http", "password": secret}],
                  "clients": [{"id": "n1", "host": "192.0.2.10", "access_mode": "ssh", "ssh_user": "root",
                               "ssh_pass": secret, "_node_baseline": {"files": {"x": secret}}}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            completed = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/kiro/redacted_config.py")],
                                       capture_output=True, cwd=str(ROOT), timeout=60,
                                       env=dict(QUIET, NET_PROXY_CONFIG=str(path)))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = completed.stdout.decode("utf-8")
        self.assertIn("192.0.2.10", output)
        self.assertNotIn(secret, output)
        self.assertNotIn("_node_baseline", output)


class SessionBriefTests(unittest.TestCase):
    def test_brief_reports_state_without_urls(self):
        text = session_brief.brief()
        self.assertIn("Branch:", text)
        self.assertIn("Version:", text)
        self.assertNotIn("://", text)
        self.assertLess(len(text), 3000)

    def test_brief_does_not_include_the_commit_subject(self):
        def fake_git(*args):
            if args[:2] == ("branch", "--show-current"):
                return "kiro/v1.5.0"
            if args[:2] == ("log", "-1"):
                return "abc1234 https://example.com/change"
            if args[:2] == ("status", "--porcelain"):
                return ""
            return "abc1234"

        with mock.patch.object(session_brief, "git", side_effect=fake_git):
            text = session_brief.brief()
        self.assertNotIn("example.com", text)
        self.assertNotIn("://", text)


if __name__ == "__main__":
    unittest.main()
