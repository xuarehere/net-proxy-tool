"""Download one published release archive anonymously via its README link and verify its checksum."""
import argparse
import hashlib
import re
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from macos_gatekeeper import report as gatekeeper_report
from smoke import run


def download(url, destination):
    with urllib.request.urlopen(url, timeout=90) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("platform")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    ext = "zip" if args.platform == "windows-x64" else "tar.gz"
    name = f"net-proxy-tool-{args.platform}.{ext}"
    pattern = rf"https://github\.com/[^/()\s]+/[^/()\s]+/releases/download/{re.escape(args.tag)}/{re.escape(name)}"
    links = []
    for doc in ["README.md", "README_EN.md"]:
        match = re.search(pattern, (root / doc).read_text(encoding="utf-8"))
        if not match:
            raise ValueError(f"{doc}: missing {args.tag} link for {name}")
        links.append(match.group())
    assert links[0] == links[1]
    with tempfile.TemporaryDirectory(prefix="release 下载 ") as temp:
        directory = Path(temp)
        archive = directory / name
        sums = directory / "SHA256SUMS.txt"
        download(links[0], archive)
        download(links[0].rsplit("/", 1)[0] + "/" + sums.name, sums)
        with archive.open("rb") as stream:
            expected = f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {name}"
        if expected not in sums.read_text(encoding="ascii").splitlines():
            raise ValueError(f"{name}: release checksum mismatch")
        if ext == "zip":
            with zipfile.ZipFile(archive) as package:
                package.extractall(directory)
        else:
            with tarfile.open(archive) as package:
                package.extractall(directory, filter="data")
        run(directory / "net-proxy-tool", browser=True)
        gatekeeper_report(directory / "net-proxy-tool")


if __name__ == "__main__":
    main()
