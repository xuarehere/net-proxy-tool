# net-proxy-tool: 跨平台通用代理穿透与 Docker 容器隔离出海调度系统 (v1.3.0)

<p align="center">
  <a href="README.md">简体中文</a> •
  <a href="README_EN.md">English</a> •
  <a href="QUICKSTART.md">3 分钟极速上手</a> •
  <a href="CHANGELOG.md">更新日志</a> •
  <a href="CONTRIBUTING.md">贡献指南</a>
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

`net-proxy-tool` 是一款面向 **x86/ARM Linux 服务器、Docker 容器、Windows/macOS 开发工作站以及工业边缘节点** 的**纯原生、零外部依赖、绝对零系统污染、双层免命令**网络代理调度与分发系统。

专为解决混合架构研发中心与生产网络中：**受限节点（如深度学习工作站、工控机、Docker 沙箱容器）无法顺畅访问 GitHub、Google、HuggingFace、PyPI、OpenAI API 等海外资源，同时又绝不允许污染宿主机或其他并行生产业务容器**的核心痛点而设计。

> 📖 **急着上手？直接查看 [👉 3 分钟极速开箱手册 (QUICKSTART.md)](QUICKSTART.md)**，包含物理机、映射端口容器与无公钥裸机的即抄即用配方！

---

## 🌟 核心特性 (Key Features)

1. **工业级全局管控与批量运维 (Industrial Batch Operations)**：
   * **🛑 一键恢复全部直连**：一键并行向所有已出海节点下发清除指令，清退代理环境并销毁配置，1 秒恢复 100% 原生直连网络；
   * **🔍 毫秒级搜索与分类过滤**：支持按节点名、IP、端口、容器名、业务标签实时模糊检索，并支持按容器/物理机/状态多维过滤；
   * **📋 一键克隆节点配置 (Clone Node)**：针对多开发容器（如 `6600`、`6601`、`6602`），一键带入所有通道属性，3 秒完成相邻容器扩容；
   * **🔄 全网并发健康巡检与 📜 审计流水日志**：一键并发探测全网节点实际外网连通状态与延迟，所有操作严格记录审计日志并提供可视化抽屉查看。
2. **全场景通用远程节点接入引擎 (Unified Provisioning Engine)**：
   * **跨平台物理工作站与工控机直连**：原生支持 x86_64 / ARM64 边缘物理机、工业视觉主机、Linux 服务器（默认端口 22）；
   * **端口映射 Docker 容器直连**：支持各类暴露自定义 SSH 端口（如 `-p 6600:22`）的独立开发/调试容器（如 `app-container`），跳过宿主机直接进入容器内部配置，不再强依赖宿主机 Docker 特权；
   * **向下兼容 Docker 宿主机穿透**：无缝保留针对未暴露 SSH 端口容器的宿主机穿透管理通道（`access_mode: "docker_host"`）；
   * **零依赖密码建信与公钥免密自愈**：基于 Linux 标准库 `SSH_ASKPASS` + `setsid` 机制，免装任何外部依赖；首次以密码接入成功后，自动将控制节点公钥植入目标节点的 `~/.ssh/authorized_keys`，后续操作彻底免密！
   * **三阶全链路深度预检引擎 (Deep Preflight Check)**：递进式校验 TCP 握手延迟 -> SSH 协议 Banner 校验 -> 凭据鉴权预检，精准区分端口未开与密码错误。
3. **全栈双层免命令引擎 (Dual-Layer Zero-Command Engine)**：
   * **工具专有配置层 (Level 1)**：自动在目标节点/容器维护 `~/.curlrc`、`~/.gitconfig`、`~/.config/pip/pip.conf`、`~/.wgetrc` 与 `/etc/apt/apt.conf.d/`。
     * **技术优势**：`curl`、`git`、`pip` 每次启动时均强制重新读取自身配置文件。**即使在已运行数天、未退出的旧终端或 tmux 会话中，直接输入 `curl https://www.google.com`、`git clone`、`pip install` 即可瞬间出海，完全免输任何代理命令**！
   * **全局环境顶层注入 (Level 2)**：在 `~/.bashrc` **第 1 行最顶端** 注入代理环境变量，规避 Ubuntu 交互式非登录 Shell 的 `[ -z "$PS1" ] && return` 提前返回机制，全面覆盖 Python `requests`/`urllib`、Go、Node.js 等通过环境变量探测代理的进程。
4. **Docker 容器独立出海与环境绝对隔离 (Zero-Pollution Docker Isolation)**：
   * **目标容器精准渗透**：纯容器内部署与配置，仅让指定的容器通过局域网代理出海；
   * **宿主机与同机容器零破坏**：宿主机本身及其余所有容器（如 10+ 个并行算法与微服务容器）网络栈与文件系统保持 100% 原生直连，杜绝任何全局污染。
5. **现代化 5 列轻量 Web 集中控制中心 (Standalone Web Console @ 8899)**：
   * **纯 Python 3 标准库**：基于 `http.server`、`urllib`、`socket`，**无需 `pip install` 任何第三方包**，开箱即启；
   * **全栈强防缓存机制 (Anti-Cache Protection)**：服务端响应头强制下发 `Cache-Control: no-cache, no-store, must-revalidate`，前端资源附加版本指纹，彻底根治浏览器由于脏缓存导致的假死与拥挤排版；
   * **极简 5 列拓扑管理**：重构旧版 8 列 5 按钮堆叠结构，引入一体化交互状态胶囊（`.status-capsule`，带呼吸绿灯动效）、独立毫秒级测速按钮与气泡折叠操作菜单；
   * **7 大全球服务实时诊断**：并发诊断 Google、GitHub、Raw GitHub、HuggingFace、PyPI、OpenAI API、YouTube 连通性与回环延迟；
   * **实机连通性复测**：支持在 Web 界面一键触发针对远程节点/容器的真实出海复测（`/api/node-test`）。
6. **多形态跨平台即启即销工具链 (Ephemeral Proxy Suite)**：
   * `with-proxy` CLI：跨平台单命令执行器（Linux/macOS Bash, Windows PowerShell/CMD），任务退出后环境变量彻底注销；支持 `--no-check` 跳过预检；
   * Python 原生上下文管理器 SDK：`with ProxySession(): ...`，作用域退出或异常时 `finally` 强制安全销毁；
   * 会话级临时开关：`proxy-on` / `proxy-off`。

---

## 🏛️ 整体拓扑与数据流向架构 (Architecture)

```
                 +-------------------------------------------------------+
                 |     Web 集中控制中心 (http://localhost:8899)          |
                 |  - 4 步接入向导    - 拓扑节点 CRUD    - 7大服务实时诊断  |
                 |  - 交互状态胶囊    - 一键出海下发     - 实机回环复测     |
                 +---------------------------+---------------------------+
                                             |
             +-------------------------------+-------------------------------+
             | (通道 1: 通用 SSH 直连)                                       | (通道 2: 宿主机穿透)
             v                                                               v
+---------------------------------+                         +---------------------------------+
| 目标节点 A: Linux 物理机/工作站  |                         | 宿主机 (保持 100% 纯净直连)     |
| (x86_64 / ARM64 / 工控机)       |                         | env | grep proxy 严格为空       |
| - 端口 22 直连                  |                         +----------------+----------------+
| - 首次密码建信自动植入公钥      |                                          | docker exec
| 👉 终端直接输入 curl 瞬间出海   |                                          v
+---------------------------------+                         +---------------------------------+
                                                            | 目标节点 C: 微服务容器          |
+---------------------------------+                         | (未暴露 SSH 的轻量容器)         |
| 目标节点 B: 端口映射独立容器    |                         | - 仅容器内部注入配置            |
| (如暴露 6600 端口的开发沙箱)    |                         | 👉 容器内直接执行命令出海       |
| - 宿主机映射端口 6600 -> 22     |                         +---------------------------------+
| - 独立文件系统与网络沙箱        |
| 👉 容器内直接输入 curl 瞬间出海 |
+---------------------------------+
             |
             +-------------------------------+-------------------------------+
                                             |
                                             v
                            +---------------------------------+
                            |   局域网出海网关 (192.168.1.100)|
                            |   端口 7890 (Clash / Mihomo 等) |
                            +---------------------------------+
                                             |
                                             v
                            +---------------------------------+
                            |   全球互联网络 (Google/GitHub/   |
                            |   HuggingFace/PyPI/OpenAI API)  |
                            +---------------------------------+
```

---

## 📁 工程目录结构 (Repository Structure)

```text
net-proxy-tool/
├── .github/                   # GitHub 协作规范与自动化 CI
│   ├── ISSUE_TEMPLATE/        # Issue 模板 (Bug 报告 / 功能建议)
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/ci.yml       # 多平台多版本自动化构建与测试
├── .gitignore                 # 严格忽略运行时私有配置、日志与临时文件
├── LICENSE                    # MIT 开源许可证
├── CHANGELOG.md               # 语义化版本演进与发布日志
├── QUICKSTART.md              # 3 分钟极速开箱即用手册 (强烈推荐)
├── README.md                  # 中文全景架构手册
├── README_EN.md               # English Documentation
├── CONTRIBUTING.md            # 开源贡献规范
├── CODE_OF_CONDUCT.md         # 社区行为准则 (Contributor Covenant 2.1)
├── SECURITY.md                # 安全与漏洞披露指引
├── pyproject.toml             # PEP 517/621 标准打包与 CLI 入口声明
├── Dockerfile                 # 极简轻量级容器化镜像
├── docker-compose.yml         # 一键编排启动服务
├── config.example.json        # 标准化拓扑配置模板（脱敏公开）
├── with_proxy.py              # 跨平台通用 Python 驱动引擎
├── install-cli.sh             # Linux/macOS 命令行软链接安装脚本
├── bin/                       # 命令行与会话执行套件
│   ├── with-proxy             # Linux/macOS 单任务即启即销执行器
│   ├── with-proxy.ps1         # Windows PowerShell 单任务执行器
│   ├── with-proxy.cmd         # Windows CMD 批处理执行器
│   ├── with-proxy-docker      # 专属 Docker 容器单任务执行器
│   ├── proxy-on / proxy-off   # Linux 会话级临时出海开关
│   ├── proxy-on.ps1 / off.ps1 # Windows PowerShell 会话级临时开关
│   └── docker-proxy           # Docker 独立环境辅助脚本
├── sdk/                       # Python 原生 SDK
│   ├── __init__.py
│   └── proxy_session.py       # with ProxySession(): 原生上下文管理器
├── web/                       # 独立微型 Web 控制台（监听端口 8899）
│   ├── server.py              # 原生 HTTP 服务端（双层下发 + 拓扑 CRUD + 实时诊断）
│   ├── static/                # 控制台前端 SPA 静态文件
│   │   ├── index.html         # 4 步向导 + 5列轻量拓扑池 + 开发者手册
│   │   ├── app.js             # 实时交互与流水线状态机
│   │   └── style.css          # 现代化深色质感 UI 规范
│   ├── start.sh / stop.sh     # Linux 后台启停控制脚本
│   └── start.bat / stop.bat   # Windows 启停脚本
├── gateway-watchdog/          # 网关守护组件
│   ├── watchdog.sh            # 用户态自愈检测脚本
│   └── install-watchdog.sh    # 定时检测安装脚本
└── test/                      # 跨平台自动化测试套件
    └── test_cross_platform.py # 100% 覆盖率回归测试用例 (5/5 全部通过)
```

---

## 🚀 极速上手 (Quick Start)

### 1. 启动 Web 控制中心
推荐在具有网络管理权限的边缘中心节点、开发工作站或服务器上部署：

- **方式 A：Python 直接运行（零外部依赖）**
  ```bash
  # Linux / macOS (常驻后台)
  ./web/start.sh

  # Windows (双击直启)
  web\start.bat
  ```
  控制台默认监听 `http://0.0.0.0:8899`，访问 `http://localhost:8899` 或目标 IP 即可。

- **方式 B：Docker 一键部署**
  ```bash
  docker compose up -d
  ```

---

### 2. 在 Web 控制台进行免命令节点管理

1. 打开浏览器访问控制台；
2. 切换至 **【🌐 拓扑与业务节点管理】** 面板；
3. 点击 **【➕ 登记新业务节点】** 录入目标（详见 [QUICKSTART.md](QUICKSTART.md) 场景配方）；
4. 在表格中找到目标节点，点击交互状态胶囊中的 **【⚡ 开启】**：
   - 系统自动通过 SSH / 穿透通道下发双层配置，胶囊动效变为 **`● 已出海`**；
5. 点击操作栏的 **【🔍 测外网】** 按钮：
   - 自动在远端容器/机器执行真实海外 HTTP 回环测试，实时显示毫秒级延迟与状态码。

---

### 3. 目标终端直接出海（100% 零配置命令）

当在 Web 界面开启出海后，直接在目标环境操作：

- **在工作站 / 服务器终端**：
  ```bash
  curl -I https://www.google.com
  git clone https://github.com/octocat/Hello-World.git
  pip install requests
  ```
- **在 Docker 容器终端**：
  ```bash
  # 方式 1: 直接通过 SSH 映射端口登录容器
  ssh -p 6600 root@192.168.1.102

  # 方式 2: 通过宿主机 docker exec 进入容器
  docker exec -it app-container /bin/bash
  
  # 直接执行出海命令（返回 HTTP/2 200 OK）
  curl -I https://www.google.com
  curl -s https://api.github.com/zen
  ```

---

### 4. 命令行单任务即启即销（临时出海）

如果不想全局开启，仅希望某一条命令临时通过代理出海：

- **Linux / macOS**：
  ```bash
  ./bin/with-proxy curl -I https://www.google.com
  ./bin/with-proxy git clone https://github.com/torvalds/linux.git
  ./bin/with-proxy pip install torch torchvision
  ```
- **Windows PowerShell**：
  ```powershell
  .\bin\with-proxy.ps1 curl.exe -I https://www.google.com
  ```

---

### 5. Python 代码中原生调用 (SDK)

在 Python 脚本或自动化流水线中使用上下文管理器：

```python
from sdk.proxy_session import ProxySession
import urllib.request

# 离开 with 代码块或抛出异常后，环境变量 100% 自动清空恢复直连
with ProxySession():
    req = urllib.request.Request("https://api.github.com/zen", headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("GitHub Zen:", resp.read().decode().strip())
```

---

## 🛡️ 环境隔离与安全保障 (Isolation Guarantees)

1. **宿主机零污染**：
   在宿主机执行：
   ```bash
   env | grep -i proxy
   cat ~/.curlrc
   ```
   输出严格为空，宿主机维持 100% 原生直连网络。
2. **非目标容器零污染**：
   同机器上的其余生产容器配置文件与环境变量完全未受任何变更，保持 100% 原生直连网络。
3. **彻底清理机制 (OFF)**：
   在 Web 界面关闭代理时，系统自动移除所有工具专有配置文件与 `~/.bashrc` 中的特定标记块，恢复 100% 纯净直连。

---

## 📡 REST API 参考 (API Reference)

微型 Web 服务端提供标准的 RESTful JSON 接口：

| 请求方法 | 接口路径 | 说明 | 请求参数示例 |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/status?gateway_id=<id>` | 获取当前网关状态与 7 大海外服务实时诊断延迟 | Query 参数: `gateway_id` |
| `GET` | `/api/config` | 获取系统完整拓扑配置（网关、节点、白名单） | 无 |
| `POST` | `/api/config` | 保存/更新全局配置 | `{"no_proxy": "..."}` |
| `POST` | `/api/node-switch` | 节点/容器出海开关切换 | `{"node_id": "...", "action": "on/off"}` |
| `POST` | `/api/node-test` | 节点/容器真实出海连通性复测 | `{"node_id": "..."}` |
| `POST` | `/api/nodes/batch-switch` | 工业级全局切断或批量开启代理 | `{"action": "off/on"}` |
| `POST` | `/api/test-node-preflight` | 递进三阶全链路深度预检 (TCP/SSH/Auth) | `{"host": "...", "port": ..., "access_mode": "..."}` |
| `GET` | `/api/audit-logs` | 获取系统操作审计流水日志 | 无 |
| `POST` | `/api/test-host` | 探测目标主机端口网络可达性 | `{"host": "...", "port": 22}` |
| `POST` | `/api/test-gateway` | 探测指定网关端口连通性 | `{"host": "...", "port": 7890}` |
| `POST` | `/api/clients/add` | 动态登记新的业务节点/容器 | 详见节点数据结构 |
| `POST` | `/api/clients/update` | 更新业务节点参数配置 | 包含 `id` 的完整节点对象 |
| `POST` | `/api/clients/delete` | 删除指定业务节点 | `{"id": "..."}` |
| `POST` | `/api/gateways/add` | 新增出海代理网关 | `{"name": "...", "host": "...", "port": ...}` |
| `POST` | `/api/set-active-gateway` | 动态切换全局默认出海网关 | `{"gateway_id": "..."}` |

---

## 🧪 自动化回归测试 (Automated Testing)

运行全链路跨平台回归测试用例：
```bash
python test/test_cross_platform.py
```
**测试覆盖范围**：
- 默认网关连通性探测
- `ProxySession` 上下文退出后环境变量零残留
- 抛出异常后 `finally` 强制安全销毁
- 子进程沙箱隔离与 `--no-check` 跳过预检验证
- Web 控制台多网关、节点 CRUD 与动态配置 API
- 全景 7 大海外服务诊断矩阵并发测试
- 节点出海开关下发与实机回环复测 API
- 工业级批量操作（`batch-switch`）与深度预检（`preflight`）
- 审计日志流水读写与持久化验证

---

## 📄 开源许可证 (License)

本项目采用 [MIT License](LICENSE) 许可证开源。
作者：`xuarehere` (2026)
