---
inclusion: fileMatch
fileMatchPattern: ["*.md", "docs/**"]
---
# Documentation style

- Write for someone who has never seen the tool. Start with what the reader can do, then how.
- Plain words, short sentences, active voice. Name the command, file, port or field exactly.
- Do not claim more than the tests and CI prove. Name the platforms and versions that were tested.
- English and Chinese pairs stay in step: `README.md` with `README.zh-CN.md`, `QUICKSTART_EN.md` with `QUICKSTART.md`, `docs/operations_en.md` with `docs/operations.md`. Update both in the same change. Each file links to its counterpart at the top.
- Commands are shown for the platform they run on. When they differ, show Windows PowerShell and POSIX shell side by side.
- Never include real addresses, host names, account names or tokens. Use `192.0.2.x`, `198.51.100.x`, `example.com` and placeholder names.
- `CHANGELOG.md` entries describe user-visible changes in the past tense, grouped as Added, Changed, Fixed and Security.
- Files under `.kiro/` and code comments are written in English.
