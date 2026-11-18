"""Build a self-contained distribution from allowlisted files and a verified CPython archive."""
import argparse
import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from itertools import chain
from pathlib import Path, PurePosixPath
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "packaging/runtimes.lock.json").read_text(encoding="utf-8"))
PREFIX = "net-proxy-tool/"
FILES = """
Start.bat runtime-select.cmd net-proxy-tool launcher.py with_proxy.py
config.example.json LICENSE README.md README_EN.md QUICKSTART.md CHANGELOG.md SECURITY.md
QUICKSTART_EN.md CONTRIBUTING.md docs/operations.md docs/operations_en.md docs/assets/console.png
docs/assets/architecture.zh.svg docs/assets/architecture.en.svg docs/render_architecture.py
install-cli.sh sdk/__init__.py sdk/config.py sdk/proxy_session.py
web/start.bat web/stop.bat web/start.sh web/stop.sh web/server.py web/ssh_askpass.py web/node_probe.py web/__init__.py web/provision.sh
web/static/index.html web/static/style.css web/static/app.js
bin/with-proxy bin/with-proxy.ps1 bin/with-proxy.cmd bin/docker-proxy bin/with-proxy-docker
bin/proxy-on bin/proxy-off bin/proxy-on.ps1 bin/proxy-off.ps1 bin/python-env.sh bin/session_env.py
gateway-watchdog/watchdog.sh gateway-watchdog/install-watchdog.sh
""".split()


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch_runtime(platform, cache):
    triple, expected = LOCK["targets"][platform]
    name = f"cpython-{LOCK['version']}+{LOCK['build']}-{triple}-install_only_stripped.tar.gz"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{expected}.tar.gz"
    if path.is_file() and sha256(path) == expected:
        return path
    url = LOCK["source"] + "/" + quote(name)
    with tempfile.NamedTemporaryFile(dir=cache, delete=False) as temp:
        partial = Path(temp.name)
    try:
        with urllib.request.urlopen(url, timeout=90) as src, partial.open("wb") as out:
            shutil.copyfileobj(src, out)
        if sha256(partial) != expected:
            raise ValueError(f"{name}: runtime SHA256 mismatch")
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)
    return path


def portable_files():
    for name in FILES:
        data = (ROOT / name).read_bytes()
        cmd = name.endswith((".bat", ".cmd"))
        if not name.endswith(".png"):
            data = data.replace(b"\r\n", b"\n")
        if cmd:
            data = data.replace(b"\n", b"\r\n")
        executable = name.endswith(".sh") or ("/" not in name and name == "net-proxy-tool") or (
            name.startswith("bin/") and not PurePosixPath(name).suffix
        )
        meta = tarfile.TarInfo(PREFIX + name)
        meta.mode = 0o755 if executable else 0o644
        meta.size = len(data)
        yield meta, io.BytesIO(data)


def runtime_files(archive):
    for member in archive:
        path = PurePosixPath(member.name)
        if path.parts[:1] != ("python",) or ".." in path.parts:
            raise ValueError(f"Unexpected runtime path: {path}")
        if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
            raise ValueError(f"Unexpected runtime member: {path}")
        source = archive.extractfile(member) if member.isfile() else None
        member.name = PREFIX + "runtime/" + "/".join(path.parts[1:])
        if member.islnk():
            target = PurePosixPath(member.linkname).relative_to("python")
            member.linkname = PREFIX + "runtime/" + str(target)
        yield member, source


def build(platform, output_dir, cache):
    runtime = fetch_runtime(platform, cache)
    windows = platform.startswith("windows-")
    suffix = "zip" if windows else "tar.gz"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"net-proxy-tool-{platform}.{suffix}"
    with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as temp:
        partial = Path(temp.name)
    try:
        with tarfile.open(runtime, "r|gz") as upstream:
            files = chain(portable_files(), runtime_files(upstream))
            if windows:
                with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, compresslevel=5) as out:
                    for member, source in files:
                        if member.isdir():
                            continue
                        if source is None:
                            raise ValueError(f"Unsupported Windows runtime link: {member.name}")
                        with out.open(member.name, "w") as dest:
                            shutil.copyfileobj(source, dest)
            else:
                with tarfile.open(partial, "w:gz", compresslevel=5) as out:
                    for member, source in files:
                        out.addfile(member, source)
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=LOCK["targets"])
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--cache", type=Path, default=ROOT / "build/runtime-cache")
    args = parser.parse_args()
    result = build(args.platform, args.output, args.cache)
    print(f"{sha256(result)}  {result.name}")
