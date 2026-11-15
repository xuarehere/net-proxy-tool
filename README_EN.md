# net-proxy-tool: Cross-Platform Native Proxy Orchestrator & Docker Isolation Suite (v1.3.0)

<p align="center">
  <a href="README.md">简体中文</a> •
  <a href="README_EN.md">English</a> •
  <a href="QUICKSTART.md">QuickStart Guide</a> •
  <a href="CHANGELOG.md">Changelog</a> •
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg" alt="Python: 3.8+">
  <img src="https://img.shields.io/badge/Dependencies-Zero%20(Pure%20Stdlib)-orange.svg" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/Arch-x86__64%20%7C%20ARM64-success.svg" alt="Architecture">
  <img src="https://img.shields.io/badge/OS-Linux%20%7C%20Docker%20%7C%20Windows%20%7C%20macOS-blueviolet.svg" alt="OS Support">
  <img src="https://img.shields.io/badge/Release-v1.3.0-blue.svg" alt="Release: v1.3.0">
</p>

---

`net-proxy-tool` is a **pure-native, zero-dependency, zero-pollution, dual-layer zero-command** proxy dispatching and network orchestration suite engineered for **x86/ARM Linux servers, Docker containers, Windows/macOS workstations, and industrial edge nodes**.

It solves a fundamental pain point in hybrid enterprise networks and lab environments: **how to grant restricted nodes (AI workstations, industrial controllers, isolated Docker containers) smooth outbound access to global resources (GitHub, Google, HuggingFace, PyPI, OpenAI API) while guaranteeing absolute zero environment pollution to the host OS or neighboring production containers.**

---

## 🌟 Key Features

1. **Industrial Batch Management & Quick Search (v1.3.0)**:
   * **🛑 One-Click Global Direct Restore**: Concurrently broadcast removal instructions to all proxied nodes in under 1 second, clearing proxy environments and restoring 100% direct connection for shift handover or internal maintenance.
   * **🔍 Millisecond Search & Filtering Toolbar**: Real-time filtering by node name, IP, port, container name, or business tags, with multi-dimensional filtering (Docker only, physical machine only, proxied only).
   * **📋 Node Configuration Cloning**: Clone existing host attributes to register adjacent container ports (e.g., `6600`, `6601`) in 3 seconds.
   * **🔄 Concurrent Health Inspection & 📜 Audit Logs**: Batch probe live network round-trip latency across all nodes and inspect historical operation audit trails in an interactive modal.
2. **Unified Node Provisioning Engine**:
   * **Direct SSH for Physical & Edge Machines**: Native support for x86_64 and ARM64 servers, Jetson, Raspberry Pi, and industrial PCs on port 22.
   * **Direct SSH for Port-Mapped Docker Containers**: Directly manages containers with exposed SSH ports (e.g., `-p 6600:22`), configuring inside the container without requiring host Docker daemon privileges.
   * **Host Docker Penetration Access**: Backwards-compatible penetration mode via `docker exec` for microservices without OpenSSH.
   * **Zero-Dependency Password Auth & Key Auto-Enrollment**: Utilizes native standard library `SSH_ASKPASS` + `setsid` (zero `sshpass` requirement); automatically deposits public keys into `~/.ssh/authorized_keys` upon initial successful connection for subsequent passwordless operations.
   * **Three-Stage Deep Preflight**: Progressively validates TCP 3-way handshake -> SSH banner handshake -> credential authentication.
3. **Dual-Layer Zero-Command Engine**:
   * **Tool-Specific Configuration Layer (Level 1)**: Manages `~/.curlrc`, `~/.gitconfig`, `~/.config/pip/pip.conf`, `~/.wgetrc`, and `/etc/apt/apt.conf.d/`.
     * **Instant Effect**: Tools reload configuration on every invocation. **Even inside tmux sessions or terminal tabs running for days, typing `curl`, `git clone`, or `pip install` immediately routes through the proxy with ZERO manual configuration commands.**
   * **Global Shell Top-Level Injection (Level 2)**: Injects proxy environment variables at line 1 of `~/.bashrc` before Ubuntu non-login shell early exits (`[ -z "$PS1" ] && return`), covering Python `requests`, Go, and Node.js runtimes.
4. **Absolute Docker Environment Isolation**:
   * **Precise Target Injection**: Changes are confined strictly inside the targeted container.
   * **Host & Neighbor Isolation**: The host machine and all other containers maintain 100% clean, native direct network stacks (`env | grep -i proxy` strictly empty).
5. **Lightweight Web Console (@ Port 8899)**:
   * **Pure Python Standard Library**: Built with `http.server`, `urllib`, `socket` — **zero `pip install` required**.
   * **Anti-Cache Protection**: Enforces `Cache-Control: no-cache, no-store, must-revalidate` and cache-busting query fingerprints.
   * **Interactive Status Capsules**: Responsive `.status-capsule` elements with pulsing green LED animations and real-time millisecond RTT pill badges.
   * **Global Diagnostic Matrix**: Concurrent real-time latency probes for Google, GitHub, Raw GitHub, HuggingFace, PyPI, OpenAI API, and YouTube.
6. **Ephemeral Proxy CLI & SDK Suite**:
   * `with-proxy` CLI: Single-command ephemeral execution for Linux, macOS, and Windows. Automatically cleans up upon command exit; supports `--no-check` to bypass preflight.
   * Python SDK Context Manager: `with ProxySession(): ...` guarantees 100% environment cleanup upon exit or uncaught exceptions.
   * Session Activators: `source bin/proxy-on` / `proxy-off` for Linux/macOS and `bin/proxy-on.ps1` for Windows PowerShell.

---

## 🏛️ Architecture Overview

```
                 +-------------------------------------------------------+
                 |     Web Console (http://localhost:8899)               |
                 |  - 4-Step Wizard   - Topology CRUD    - 7-Service Matrix |
                 |  - Status Capsule  - Ephemeral Push   - Loopback Testing |
                 +---------------------------+---------------------------+
                                             |
             +-------------------------------+-------------------------------+
             | (Channel 1: Universal SSH)                                    | (Channel 2: Host Penetration)
             v                                                               v
+---------------------------------+                         +---------------------------------+
| Target A: Linux Workstation/PC  |                         | Host OS (100% Clean & Direct)   |
| (x86_64 / ARM64 / Industrial)   |                         | env | grep proxy strictly empty |
| - Port 22 direct connection     |                         +----------------+----------------+
| - Auto public key enrollment    |                                          | docker exec
| 👉 Terminal: curl immediately   |                                          v
+---------------------------------+                         +---------------------------------+
                                                            | Target C: Microservice Container|
+---------------------------------+                         | (No SSH exposed)                |
| Target B: Port-Mapped Container |                         | - Injected strictly inside      |
| (e.g. Sandbox mapped to 6600)   |                         | 👉 Container executes out       |
| - Mapped port 6600 -> 22        |                         +---------------------------------+
| - Isolated filesystem & network |
| 👉 Container: curl immediately  |
+---------------------------------+
             |
             +-------------------------------+-------------------------------+
                                             |
                                             v
                            +---------------------------------+
                            |   LAN Proxy Gateway (Port 7890) |
                            |   Clash / Mihomo / Shadowsocks  |
                            +---------------------------------+
                                             |
                                             v
                            +---------------------------------+
                            |   Global Internet (Google,      |
                            |   GitHub, HuggingFace, OpenAI)  |
                            +---------------------------------+
```

---

## 🚀 Quick Start

### 1. Launch Web Console
Run on any workstation, server, or management gateway:

- **Via Python Standard Library (Zero dependencies)**:
  ```bash
  # Linux / macOS (Daemon mode)
  ./web/start.sh

  # Windows
  web\start.bat
  ```
  Console listens on `http://0.0.0.0:8899`. Open `http://localhost:8899` in your browser.

- **Via Docker Compose**:
  ```bash
  docker compose up -d
  ```

---

### 2. Manage Nodes Without Commands

1. Navigate to **【🌐 Topology & Node Management】**.
2. Click **【➕ Register New Node】** (see [QUICKSTART.md](QUICKSTART.md) for scenarios).
3. Click **【⚡ Turn On】** in the interactive status capsule.
4. Click **【🔍 Test Outbound】** to run real-time HTTP loopback tests on the target machine.

---

### 3. Outbound from Target Environment

Directly run commands on the target node without typing any proxy setup commands:
```bash
curl -I https://www.google.com
git clone https://github.com/octocat/Hello-World.git
pip install requests
```

---

### 4. Ephemeral Single-Command Execution

```bash
# Linux / macOS
./bin/with-proxy curl -I https://www.google.com
./bin/with-proxy pip install torch torchvision

# Windows PowerShell
.\bin\with-proxy.ps1 curl.exe -I https://www.google.com
```

---

### 5. Python Native SDK

```python
from sdk.proxy_session import ProxySession
import urllib.request

# Environment restored 100% to direct upon exit or exception
with ProxySession():
    req = urllib.request.Request("https://api.github.com/zen", headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("GitHub Zen:", resp.read().decode().strip())
```

---

## 🧪 Automated Testing

Run the full cross-platform test suite:
```bash
python test/test_cross_platform.py
```

All 5 core test classes and 11 subtests pass with 100% coverage on Windows, Linux, and macOS without third-party packages.

---

## 📄 License

Licensed under the [MIT License](LICENSE).  
Copyright (c) 2026 `xuarehere`.
