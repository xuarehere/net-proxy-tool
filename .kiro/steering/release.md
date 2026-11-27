---
inclusion: manual
---
# Release procedure

Use this when preparing a version. Every step that publishes something needs the maintainer's explicit approval first: push, pull request, merge, tag, GitHub Release and repository settings.

1. Versions match: `sdk/config.py: VERSION`, `pyproject.toml` `version`, `config.example.json` `version`, the download table in both READMEs and the newest `CHANGELOG.md` heading. Run `python -X utf8 tools/kiro/check_release_consistency.py`.
2. Full suite passes with a temporary `NET_PROXY_CONFIG`: `python -X utf8 -m unittest discover -s test`. Property tests run with `HYPOTHESIS_PROFILE=ci`.
3. Local packaging checks pass: `python -X utf8 packaging/test_wheel.py` and `python packaging/build_portable.py windows-x64`, followed by `packaging/smoke.py` on the extracted archive.
4. `python -X utf8 tools/kiro/scan_secrets.py --unpushed` reports nothing, and `git status` shows no stray files.
5. With approval: push the branch and open a pull request. CI must pass on all five platforms, the three Linux distributions and the container job.
6. With approval: merge, tag `vX.Y.Z` on `main` and push the tag. The release job builds, uploads and verifies the archives and checksums, and `verify_public` downloads and runs them.
7. Check the Release page: five archives, `SHA256SUMS.txt`, and notes taken from `CHANGELOG.md`.
