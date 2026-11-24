"""Kiro PreToolUse guard for shell commands, command-running MCP tools and file tools.

The hook blocks a tool call by exiting with code 2 and explaining why on stderr.
It blocks:

* commands that print git remote URLs or the whole git configuration, because
  this repository's remotes have carried embedded access tokens;
* `gh auth token`, `gh auth status --show-token` and `git credential fill`;
* force and mirror pushes;
* reading or changing the maintainer's console configuration (`config.json` at
  the repository root), which stores SSH passwords, from a shell or a file tool;
* `git commit` and `git push` when the content being committed or pushed contains
  a credential or an entry of `scratch/private-denylist.txt`;
* a file write that would give a runtime Python file an import from outside the
  standard library (the same check as check_stdlib.py, before the file changes).

Everything else is allowed with exit code 0 and no output. Unexpected internal
errors also allow the call and print a warning, so a broken guard cannot stop
all tool use.
"""
import fnmatch
import os
import re
import shlex
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _hookio import ROOT, event_paths, read_event, record, repo_relative  # noqa: E402
import check_stdlib  # noqa: E402
import scan_secrets  # noqa: E402

Decision = namedtuple("Decision", "action rule message")
ALLOW = Decision("allow", "", "")

GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                          "--super-prefix", "--config-env", "--list-cmds", "--attr-source"}
# Programs that can show or change a file. Interpreters count because inline code can print a file.
READ_VERBS = {"cat", "type", "gc", "get-content", "more", "less", "head", "tail", "bat", "nl",
              "select-string", "sls", "findstr", "grep", "rg", "egrep", "fgrep", "strings", "awk",
              "format-hex", "od", "xxd", "hexdump", "notepad", "code", "vim", "vi", "nano", "copy",
              "cp", "copy-item", "scp", "base64", "certutil", "jq", "python", "python3", "py", "node",
              "perl", "ruby", "php", "powershell", "pwsh", "cmd", "bash", "sh", "wsl"}
CHANGE_VERBS = {"set-content", "add-content", "clear-content", "out-file", "tee", "tee-object", "move-item",
                "mv", "move", "rename-item", "ren", "remove-item", "rm", "del", "erase", "sed"}
# Programs that run their arguments as another command line.
SHELLS = {"cmd", "powershell", "pwsh", "bash", "sh", "zsh", "dash", "wsl", "iex", "invoke-expression"}
READ_CALL = re.compile(r"(?i)\b(?:ReadAll(?:Text|Lines|Bytes)|WriteAll(?:Text|Lines|Bytes))\b|>")
QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
SEPARATOR = re.compile(r"\|\||&&|[;|&\n]")
REMOTE_URL_CONFIG = re.compile(r"(?i)^(remote\.[^=]*\.(url|pushurl)|url\..*)$")
GIT_CONFIG_FILE = re.compile(r"(?i)(^|[\s'\"=(/\\])\.git[\\/]+config(\s|$|['\")])")
CONFIG_JSON = re.compile(r"(?i)([^\s'\"<>|;&]*config\.json)\b")
WRITE_TOOL = re.compile(r"(?i)write|append|replace|edit|create_file")

REMOTE_HINT = ("it prints remote URLs, and this repository's remotes have carried embedded access tokens. "
               "Run `git remote` to list remote names, or `git branch -vv` to see tracking branches.")
CONFIG_HINT = ("config.json stores SSH passwords. For a redacted view run "
               "`python -X utf8 tools/kiro/redacted_config.py`.")


def split_segments(command):
    """Split a command line into simple commands on ; && || | & and newlines outside quotes."""
    segments, current, quote = [], [], None
    index = 0
    while index < len(command):
        char = command[index]
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
            current.append(char)
            index += 1
            continue
        matched = SEPARATOR.match(command, index)
        if matched:
            segments.append("".join(current))
            current = []
            index = matched.end()
            continue
        current.append(char)
        index += 1
    segments.append("".join(current))
    return [segment.strip() for segment in segments if segment.strip()]


def tokens(segment):
    """Tokenize without treating backslashes as escapes, so Windows paths survive."""
    try:
        parts = shlex.split(segment, posix=False)
    except ValueError:
        parts = segment.split()
    cleaned = []
    for part in parts:
        if len(part) >= 2 and part[0] == part[-1] and part[0] in ("'", '"'):
            part = part[1:-1]
        cleaned.append(part)
    return cleaned


def program_name(token):
    name = re.split(r"[\\/]", token)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


def git_invocation(parts):
    """Return (git_cwd, subcommand, args) for a git command, or None."""
    for start, part in enumerate(parts):
        if program_name(part) == "git":
            break
    else:
        return None
    git_cwd = None
    index = start + 1
    while index < len(parts):
        part = parts[index]
        if part in GIT_OPTIONS_WITH_VALUE:
            if part == "-C" and index + 1 < len(parts):
                git_cwd = parts[index + 1]
            index += 2
            continue
        if part.startswith("-"):
            index += 1
            continue
        return git_cwd, part.lower(), parts[index + 1:]
    return git_cwd, "", []


def gh_invocation(parts):
    """Return the lower-cased arguments after a gh executable, including command wrappers."""
    for start, part in enumerate(parts):
        if program_name(part) == "gh":
            return [item.lower() for item in parts[start + 1:]]
    return None


def positional(args):
    return [arg for arg in args if not arg.startswith("-")]


def remote_url_rule(subcommand, args):
    if subcommand == "remote":
        names = positional(args)
        if "--verbose" in args or any(re.fullmatch(r"-[A-Za-z]*v[A-Za-z]*", arg) for arg in args):
            return "git remote -v"
        if names[:1] == ["get-url"] or (names[:1] == ["show"] and len(names) > 1):
            return "git remote " + names[0]
    if subcommand == "config":
        names = positional(args)
        if {"-l", "--list", "--get-regexp", "--get-urlmatch"} & set(args) or names[:1] == ["list"]:
            return "git config --list"
        if any(REMOTE_URL_CONFIG.match(name) for name in names):
            return "git config remote.*.url"
    if subcommand == "ls-remote" and "--get-url" in args:
        return "git ls-remote --get-url"
    if subcommand == "credential" and "fill" in args:
        return "git credential fill"
    return None


def force_push_rule(args):
    for arg in args:
        if arg in ("--force", "--force-with-lease", "--force-if-includes", "--mirror") or \
                arg.startswith("--force-with-lease="):
            return arg
        if re.fullmatch(r"-[A-Za-z]*f[A-Za-z]*", arg):
            return arg
        if arg.startswith("+") and len(arg) > 1:
            return "+refspec"
    return None


def resolve(path, cwd):
    """Absolute, case-normalized path. Backslashes count as separators on every platform."""
    path = os.path.expanduser(path.replace("\\", "/"))
    return os.path.normcase(os.path.abspath(os.path.join(cwd, path)))


def can_read(parts, raw):
    """True when a simple command can show or change file contents.

    Every word is checked, not only the first, so `$x = Get-Content f` and
    `(Get-Content f)` count. Redirection (`>`) outside quotes counts as a change.
    """
    if READ_CALL.search(QUOTED.sub("", raw)):
        return True
    verbs = READ_VERBS | CHANGE_VERBS
    return any(program_name(part.lstrip("(@$&.")) in verbs for part in parts)


def reads_console_config(parts, raw, cwd):
    if not can_read(parts, raw):
        return False
    target = os.path.normcase(str(ROOT / "config.json"))
    return any(resolve(match.group(1), cwd) == target for match in CONFIG_JSON.finditer(raw))


def staged_paths_for_add(segments_parts):
    """Return (scan_all_untracked, named_paths, adds_tracked) for `git add` segments in the command."""
    scan_all, named, adds = False, [], False
    for parts in segments_parts:
        invocation = git_invocation(parts)
        if not invocation or invocation[1] != "add":
            continue
        adds = True
        args = invocation[2]
        if {"-A", "--all", ".", "*", ":/"} & set(args):
            scan_all = True
        named.extend(positional(args))
    return scan_all, named, adds


def scan_for_commit(cwd, segments_parts, commit_args, raw_command, scanner):
    denylist = scanner.load_denylist()
    findings = scanner.scan_text(raw_command, "command line", denylist)
    findings.extend(scanner.scan_staged(cwd, denylist))
    scan_all, named, adds = staged_paths_for_add(segments_parts)
    commit_all = any(re.fullmatch(r"-[A-Za-z]*a[A-Za-z]*", arg) or arg == "--all" for arg in commit_args)
    if adds or commit_all:
        findings.extend(scanner.scan_worktree(cwd, denylist))
    if scan_all or named:
        untracked = scanner.untracked_files(cwd)
        if not scan_all:
            prefixes = [name.replace("\\", "/").rstrip("/") for name in named]
            prefixes = [name[2:] if name.startswith("./") else name for name in prefixes]
            if not any(name.startswith(":") for name in prefixes):
                untracked = [name for name in untracked
                             if any(name == prefix or name.startswith(prefix + "/") or
                                    (any(char in prefix for char in "*?[") and
                                     fnmatch.fnmatchcase(name, prefix))
                                    for prefix in prefixes)]
        findings.extend(scanner.scan_untracked(untracked, cwd, denylist))
    return findings


def blocked(rule, message):
    return Decision("block", rule, message)


def substitutions(segment):
    """Return the command texts inside `$( ... )` and backticks. Shells run these even inside double quotes."""
    found = []
    start = segment.find("$(")
    while start >= 0:
        depth, position = 1, start + 2
        while position < len(segment) and depth:
            depth += {"(": 1, ")": -1}.get(segment[position], 0)
            position += 1
        found.append(segment[start + 2:position - 1 if depth == 0 else position])
        start = segment.find("$(", start + 2)
    found.extend(re.findall(r"`([^`]+)`", segment))
    return found


def nested_commands(parts, segment):
    """Command lines that a segment hands to another shell, such as `cmd /c "..."` or `bash -c '...'`."""
    nested = substitutions(segment)
    if parts and program_name(parts[0]) in SHELLS and len(parts) > 1:
        nested.append(" ".join(parts[1:]))
    return nested


def segment_rule(segment, parts, cwd, depth=0):
    """Return a blocking Decision for one simple command, or None."""
    if GIT_CONFIG_FILE.search(segment) and can_read(parts, segment):
        return blocked("remote-url", "shell-guard: blocked access to .git/config: " + REMOTE_HINT)
    if reads_console_config(parts, segment, cwd):
        return blocked("console-config", "shell-guard: blocked reading or changing config.json at the "
                                         "repository root. " + CONFIG_HINT)
    words = gh_invocation(parts)
    if words is not None:
        if words[:2] == ["auth", "token"] or (words[:2] == ["auth", "status"] and
                                                ("--show-token" in words or "-t" in words)):
            return blocked("gh-token", "shell-guard: blocked a command that prints the GitHub CLI token.")
    invocation = git_invocation(parts)
    if invocation:
        git_cwd, subcommand, args = invocation
        rule = remote_url_rule(subcommand, args)
        if rule:
            return blocked("remote-url", "shell-guard: blocked `{}`: {}".format(rule, REMOTE_HINT))
        if subcommand == "push":
            forced = force_push_rule(args)
            if forced:
                return blocked("force-push", "shell-guard: blocked `git push {}`. Force and mirror pushes "
                                             "rewrite published history; push without force, or ask the "
                                             "maintainer to do it.".format(forced))
    if depth < 3:
        for inner in nested_commands(parts, segment):
            for inner_segment in split_segments(inner):
                decision = segment_rule(inner_segment, tokens(inner_segment), cwd, depth + 1)
                if decision:
                    return decision
    return None


def evaluate_command(command, cwd, scanner=scan_secrets):
    segments = split_segments(command)
    segments_parts = [tokens(segment) for segment in segments]
    for segment, parts in zip(segments, segments_parts):
        decision = segment_rule(segment, parts, cwd)
        if decision:
            return decision
    for parts in segments_parts:
        invocation = git_invocation(parts)
        if not invocation or invocation[1] not in ("commit", "push"):
            continue
        git_cwd, subcommand, args = invocation
        repo = resolve(git_cwd, cwd) if git_cwd else cwd
        try:
            if subcommand == "commit":
                findings = scan_for_commit(repo, segments_parts, args, command, scanner)
            else:
                findings = scanner.scan_unpushed(repo, scanner.load_denylist())
        except RuntimeError as exc:
            print("shell-guard: warning: secret scan skipped: {}".format(exc), file=sys.stderr)
            continue
        if findings:
            return blocked("secret-scan", "shell-guard: blocked `git {}`: {} finding(s) in the content being "
                                          "{}:\n{}\nRemove them. A deliberate test fixture can carry "
                                          "`pragma: allowlist secret` on the same line.".format(
                                              subcommand, len(findings),
                                              "committed" if subcommand == "commit" else "pushed",
                                              scanner.format_findings(findings)))
    return ALLOW


def tool_command(tool_input):
    command = tool_input.get("command")
    if isinstance(command, str):
        return command
    argv = tool_input.get("argv")
    if isinstance(argv, list) and all(isinstance(item, str) for item in argv):
        return " ".join(shlex.quote(item) if re.search(r"\s", item) else item for item in argv)
    return None


def first_text(tool_input, *keys):
    for key in keys:
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return None


def proposed_text(tool_name, tool_input, path):
    """Return the file text a write tool would leave behind, or None when it cannot be known."""
    text = first_text(tool_input, "text", "content", "file_text", "fileText")
    if text is not None and "append" not in tool_name:
        return text
    try:
        current = Path(path).read_text(encoding="utf-8")
    except OSError:
        current = None
    if text is not None:  # Append: Kiro adds a newline first when the file does not end with one.
        current = current or ""
        return current + ("\n" if current and not current.endswith("\n") else "") + text
    old = first_text(tool_input, "oldStr", "old_str", "oldString", "old_string")
    new = first_text(tool_input, "newStr", "new_str", "newString", "new_string")
    if current is None or old is None or new is None or old not in current:
        return None
    replace_all = tool_input.get("replace_all") is True or tool_input.get("replaceAll") is True
    return current.replace(old, new) if replace_all else current.replace(old, new, 1)


def stdlib_rule(tool_name, tool_input, path, cwd):
    """Block a write that would give a runtime file an import from outside the standard library."""
    rel = repo_relative(path, cwd)
    if not WRITE_TOOL.search(tool_name) or not check_stdlib.is_runtime(rel):
        return None
    source = proposed_text(tool_name.lower(), tool_input, os.path.join(cwd, path))
    if source is None:
        return None
    problems = check_stdlib.check_source(source, rel, (ROOT / rel).parent, report_syntax_errors=False)
    if not problems:
        return None
    return blocked("stdlib-only", "stdlib-guard: blocked this write. Runtime code must use the Python standard "
                                  "library only (.kiro/steering/tech.md):\n" + "\n".join(problems) +
                   "\nMake the import optional (try/except ImportError) or keep test-only code under test/.")


def evaluate(event, scanner=scan_secrets):
    """Decide whether a PreToolUse event may proceed."""
    tool_input = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    tool_name = event.get("tool_name") if isinstance(event.get("tool_name"), str) else ""
    cwd = tool_input.get("cwd") or event.get("cwd") or str(ROOT)
    if not os.path.isdir(str(cwd)):
        cwd = str(ROOT)
    command = tool_command(tool_input)
    if command:
        return evaluate_command(command, str(cwd), scanner)
    target = os.path.normcase(str(ROOT / "config.json"))
    paths = event_paths(tool_input)
    for path in paths:
        if resolve(path, str(cwd)) == target:
            return blocked("console-config", "config-guard: blocked access to config.json at the repository "
                                             "root. " + CONFIG_HINT)
    for path in paths[:1]:
        decision = stdlib_rule(tool_name, tool_input, path, str(cwd))
        if decision:
            return decision
    return ALLOW


def main():
    event = read_event()
    try:
        decision = evaluate(event)
    except Exception as exc:  # A broken guard must not stop every tool call.
        print("shell-guard: warning: guard error, call allowed: {}".format(exc), file=sys.stderr)
        return 0
    if decision.action == "block":
        tool_input = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
        record("shell-guard" if tool_command(tool_input) else "file-guard", "block", decision.rule,
               event.get("tool_name", ""))
        print(decision.message, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
