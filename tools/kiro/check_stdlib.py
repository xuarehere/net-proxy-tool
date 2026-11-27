"""Keep the runtime on the Python standard library.

Kiro runs this after a Python file or pyproject.toml is saved. It parses the saved
runtime files with `ast` and reports any import that is neither part of the
standard library nor a module of this repository. It also checks that
pyproject.toml declares no runtime dependencies.

Runtime code is the root scripts and everything under sdk/, web/, bin/ and
tools/. Tests (test/, packaging/) may use Hypothesis and Playwright.

Exit codes: 0 clean, 2 violations (reported on stderr so Kiro shows them to the agent).

    python -X utf8 tools/kiro/check_stdlib.py            # hook mode, reads the event on STDIN
    python -X utf8 tools/kiro/check_stdlib.py --all      # check every runtime file
    python -X utf8 tools/kiro/check_stdlib.py web/x.py   # check named files
"""
import argparse
import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _hookio import ROOT, event_paths, read_event, record, repo_relative  # noqa: E402

RUNTIME_DIRS = ("sdk/", "web/", "bin/", "tools/")
SKIPPED_DIRS = ("build/", "dist/", "scratch/", ".git/", ".kiro/")

# Python 3.8 and 3.9 have no sys.stdlib_module_names. This covers their top-level modules.
FALLBACK_STDLIB = frozenset("""
__future__ _abc _ast _thread _winapi abc aifc argparse array ast asynchat asyncio asyncore atexit audioop
base64 bdb binascii binhex bisect builtins bz2 cProfile calendar cgi cgitb chunk cmath cmd code codecs
codeop collections colorsys compileall concurrent configparser contextlib contextvars copy copyreg crypt
csv ctypes curses dataclasses datetime dbm decimal difflib dis distutils doctest email encodings
ensurepip enum errno faulthandler fcntl filecmp fileinput fnmatch formatter fractions ftplib functools gc
getopt getpass gettext glob grp gzip hashlib heapq hmac html http imaplib imghdr imp importlib
inspect io ipaddress itertools json keyword lib2to3 linecache locale logging lzma mailbox mailcap
marshal math mimetypes mmap modulefinder msilib msvcrt multiprocessing netrc nis nntplib nt ntpath
nturl2path numbers opcode operator optparse os ossaudiodev parser pathlib pdb pickle pickletools pipes
pkgutil platform plistlib poplib posix posixpath pprint profile pstats pty pwd py_compile pyclbr pydoc
pydoc_data pyexpat queue quopri random re readline reprlib resource rlcompleter runpy sched secrets
select selectors shelve shlex shutil signal site smtpd smtplib sndhdr socket socketserver spwd sqlite3
sre_compile sre_constants sre_parse ssl stat statistics string stringprep struct subprocess sunau symbol
symtable sys sysconfig syslog tabnanny tarfile telnetlib tempfile termios textwrap threading time
timeit tkinter token tokenize trace traceback tracemalloc tty turtle turtledemo types typing
unicodedata unittest urllib uu uuid venv warnings wave weakref webbrowser winreg winsound wsgiref xdrlib
xml xmlrpc zipapp zipfile zipimport zlib
""".split())


def stdlib_names():
    return frozenset(getattr(sys, "stdlib_module_names", ())) or FALLBACK_STDLIB


def is_runtime(rel):
    """True for Python files that ship with the console, CLI, SDK or hooks."""
    if not rel or not rel.endswith(".py") or rel.startswith(SKIPPED_DIRS):
        return False
    return "/" not in rel or rel.startswith(RUNTIME_DIRS)


def runtime_files():
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if is_runtime(rel) and "__pycache__" not in rel:
            yield rel


def is_local(name, file_dir):
    for base in (ROOT, file_dir):
        if (base / name).is_dir() or (base / (name + ".py")).is_file():
            return True
    return False


def handles_import_error(node):
    """True when a try statement has a handler for ImportError or ModuleNotFoundError."""
    for handler in node.handlers:
        names = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        if any(isinstance(name, ast.Name) and name.id in ("ImportError", "ModuleNotFoundError") for name in names):
            return True
    return False


def imported_modules(tree):
    """Yield (line, top-level module) for required absolute imports.

    Imports inside the body of a `try` that handles ImportError are optional
    fallbacks and are not reported.
    """
    pending = [(tree, False)]
    while pending:
        node, optional = pending.pop()
        if isinstance(node, (ast.Try, getattr(ast, "TryStar", ast.Try))):
            for child in node.body:
                pending.append((child, optional or handles_import_error(node)))
            for child in node.handlers + node.orelse + node.finalbody:
                pending.append((child, optional))
            continue
        if not optional and isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name.split(".")[0]
        elif not optional and isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module.split(".")[0]
        pending.extend((child, optional) for child in ast.iter_child_nodes(node))


def check_source(source, rel, file_dir=None, report_syntax_errors=True):
    """Return violation messages for one runtime file's source text.

    The pre-write guard passes report_syntax_errors=False: an edit in the middle
    of a multi-step change may leave a file briefly unparsable, and that is not
    an import violation.
    """
    file_dir = file_dir or (ROOT / rel).parent
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as exc:
        if not report_syntax_errors:
            return []
        return ["{}:{}: syntax error: {}".format(rel, exc.lineno or 0, exc.msg)]
    standard = stdlib_names()
    problems = []
    for line, module in imported_modules(tree):
        if module in standard or is_local(module, file_dir):
            continue
        problems.append("{}:{}: imports '{}', which is not in the Python standard library".format(rel, line, module))
    return problems


def declared_dependencies(text):
    try:
        import tomllib
    except ImportError:
        tomllib = None
    if tomllib:
        return tomllib.loads(text).get("project", {}).get("dependencies", [])
    project = re.search(r"^\s*\[project\]\s*(?:#.*)?$\n?(.*?)(?=^\s*\[|\Z)",
                        text, re.MULTILINE | re.DOTALL)
    if not project:
        return []
    matched = re.search(r"^\s*dependencies\s*=\s*\[(.*?)\]", project.group(1), re.MULTILINE | re.DOTALL)
    return re.findall(r"['\"]([^'\"]+)['\"]", matched.group(1)) if matched else []


def check_pyproject(path=None):
    path = path or ROOT / "pyproject.toml"
    try:
        dependencies = declared_dependencies(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return ["pyproject.toml: cannot read dependencies: {}".format(exc)]
    if dependencies:
        return ["pyproject.toml: [project].dependencies must stay empty, found {}".format(dependencies)]
    return []


def check_paths(rels):
    problems = []
    for rel in rels:
        if rel == "pyproject.toml":
            problems.extend(check_pyproject())
        elif is_runtime(rel):
            path = ROOT / rel
            try:
                source = path.read_text(encoding="utf-8")
            except OSError:
                continue
            problems.extend(check_source(source, rel, path.parent))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report runtime imports outside the Python standard library.")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--all", action="store_true", help="check every runtime file and pyproject.toml")
    args = parser.parse_args(argv)
    if args.all:
        rels = list(runtime_files()) + ["pyproject.toml"]
    elif args.paths:
        rels = [repo_relative(path) for path in args.paths]
    else:
        event = read_event()
        rels = [repo_relative(path, event.get("cwd")) for path in event_paths(event)]
        if not rels:  # The event named no file we recognize: check everything.
            rels = list(runtime_files()) + ["pyproject.toml"]
        record("stdlib-only", "run", "", ", ".join(rel or "?" for rel in rels[:3]) +
               (" and {} more".format(len(rels) - 3) if len(rels) > 3 else ""))
    problems = check_paths([rel for rel in rels if rel])
    if problems:
        record("stdlib-only", "flag", "third-party-import", "; ".join(problems)[:200])
        print("stdlib-only: the runtime must use the Python standard library only "
              "(see .kiro/steering/tech.md).\n" + "\n".join(problems), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
