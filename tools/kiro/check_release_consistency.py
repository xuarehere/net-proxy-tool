"""Report the version placeholders of a release.

Every place that names the release version must agree before an archive is
published. The tool reads files and prints findings; it never changes them and
never prints configuration content or a URL.

    python -X utf8 tools/kiro/check_release_consistency.py
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sdk.config import NO_PROXY  # noqa: E402

VERSION_FILES = (
    ("sdk/config.py", re.compile(r'^VERSION\s*=\s*"([^"]+)"', re.MULTILINE)),
    ("pyproject.toml", re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)),
    ("config.example.json", re.compile(r'"version"\s*:\s*"([^"]+)"')),
)
README_FILES = ("README.md", "README.zh-CN.md")
RELEASE_LINK = re.compile(r"releases/(?:download|tag)/v([0-9]+\.[0-9]+\.[0-9]+)")
DOWNLOAD_HEADING = re.compile(r"(?:下载|Download)\s+v([0-9]+\.[0-9]+\.[0-9]+)")
CHANGELOG_HEADING = re.compile(r"^##\s+\[([0-9]+\.[0-9]+\.[0-9]+)\]", re.MULTILINE)
EXAMPLE_NO_PROXY = re.compile(r'"no_proxy"\s*:\s*"([^"]*)"')


def read(path):
    """Return the text of a file, or an empty string when it cannot be read."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def find_all(text, pattern):
    return [match.group(1) for match in pattern.finditer(text)]


def collect(root=ROOT):
    """Return the versions found in each place and the list of mismatches.

    The first entry of the returned pair maps a source name to the version it
    holds; the second lists the sources that disagree with the reference.
    """
    root = Path(root)
    found = {}
    for name, pattern in VERSION_FILES:
        values = find_all(read(root / name), pattern)
        found[name] = values[0] if values else None
    for name in README_FILES:
        text = read(root / name)
        values = find_all(text, RELEASE_LINK) + find_all(text, DOWNLOAD_HEADING)
        found[name] = sorted(set(values))
    changelog = find_all(read(root / "CHANGELOG.md"), CHANGELOG_HEADING)
    found["CHANGELOG.md"] = changelog[0] if changelog else None

    reference = found.get("sdk/config.py")
    mismatches = []
    for name in ("pyproject.toml", "config.example.json", "CHANGELOG.md"):
        if found.get(name) != reference:
            mismatches.append((name, found.get(name), reference))
    for name in README_FILES:
        versions = found.get(name) or []
        if not versions:
            mismatches.append((name, None, reference))
        elif len(versions) > 1 or versions[0] != reference:
            mismatches.append((name, ", ".join(versions), reference))

    example = read(root / "config.example.json")
    example_no_proxy = find_all(example, EXAMPLE_NO_PROXY)
    if not example_no_proxy:
        mismatches.append(("config.example.json:no_proxy", None, NO_PROXY))
    elif example_no_proxy[0] != NO_PROXY:
        mismatches.append(("config.example.json:no_proxy", example_no_proxy[0], NO_PROXY))
    return found, mismatches


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report the version placeholders of a release.")
    parser.add_argument("--root", default=str(ROOT), help="repository root to inspect")
    args = parser.parse_args(argv)
    found, mismatches = collect(args.root)
    for name, value in found.items():
        shown = ", ".join(value) if isinstance(value, list) else (value or "not found")
        print("{:<24} {}".format(name + ":", shown))
    if mismatches:
        print("release-consistency: {} mismatch(es)".format(len(mismatches)))
        for name, value, reference in mismatches:
            print("  {}: found {!r}, expected {!r}".format(name, value, reference))
        return 1
    print("release-consistency: every version placeholder agrees")
    return 0


if __name__ == "__main__":
    sys.exit(main())
