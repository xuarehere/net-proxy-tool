# Contributing to net-proxy-tool

First off, thank you for considering contributing to `net-proxy-tool`! 🎉

We welcome contributions from developers worldwide to make multi-node and container proxy orchestration simpler, safer, and cleaner.

---

## 🧭 Core Principles

Before opening a pull request, please keep our fundamental engineering tenets in mind:

1. **Zero External Dependencies (纯标准库原则)**:
   - The runtime core (`web/server.py`, `with_proxy.py`, `sdk/proxy_session.py`) must remain **100% pure Python standard library**.
   - Do **NOT** add third-party pip dependencies (e.g. `requests`, `flask`, `fastapi`, `paramiko`, `pydantic`). We rely solely on `http.server`, `urllib`, `socket`, `subprocess`, `json`, etc.
2. **Strict System Isolation & Zero Host Pollution (绝对环境隔离)**:
   - Any modification to client environments or containers must be strictly targeted and 100% reversible (`off` action must leave the system in its pristine state).
   - The host system and non-targeted containers must never have their network or filesystem altered.
3. **Cross-Platform Compatibility (全平台兼容)**:
   - Core CLI, SDK, and tests must pass on Linux (x86_64 and ARM64), Windows (10/11/Server), and macOS.
4. **Data Sanitization & Privacy (敏感数据零泄露)**:
   - Never commit private IP addresses (use RFC 1918 `192.168.1.x`), internal hostnames/domains, or credentials.
   - Keep `config.json` untracked. Only update `config.example.json` with generic placeholders.

---

## 🛠️ Development & Testing Workflow

### 1. Fork & Clone
```bash
git clone https://github.com/<your-username>/net-proxy-tool.git
cd net-proxy-tool
```

### 2. Create a Feature Branch
```bash
git checkout -b feat/your-feature-name
# or
git checkout -b fix/your-bugfix-name
```

### 3. Run Automated Tests
Before committing, ensure all tests pass:
```bash
python test/test_cross_platform.py
```

### 4. Verify Data Sanitization
Ensure no private IP or credential traces remain:
```bash
# On Linux / macOS:
grep -rnE "10\.[0-9]+\.[0-9]+\.[0-9]+" . --exclude="*.git*" --exclude="config.json"

# On Windows PowerShell:
Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notmatch '\\.git' -and $_.Name -ne 'config.json' } | Select-String -Pattern "10\.192\."
```

### 5. Commit Guidelines
We follow the [Conventional Commits](https://www.conventionalcommits.org/) convention:
- `feat: add socks5 proxy support to with-proxy`
- `fix: handle edge case in socket timeout on ARM64`
- `docs: update quickstart guide for raspberry pi`
- `refactor: optimize batch-switch concurrency`

### 6. Submit a Pull Request
Push to your fork and submit a PR against `main`. Clearly explain the problem solved, changes made, and include verification results.
