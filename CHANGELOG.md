# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-11-15

### 🚀 Industrial Operations, Deep Preflight & Live Container Integration (工业管控增强、深度预检与实机联调)

- **工业级全网批量管控 (Batch Operations)**：
  - 新增「🛑 一键恢复全部直连」操作，交接班或外网维护时 1 秒全局切断所有节点出海代理，清除配置并恢复 100% 直连；
  - 后端提供 `POST /api/nodes/batch-switch` 支持批量开启与关闭，提供详细执行明细。
- **节点毫秒级搜索与分类过滤工具栏 (Search & Filter Toolbar)**：
  - 在【🌐 拓扑与节点管理】表格上方新增实时搜索过滤工具栏，支持按节点名称、IP、端口、容器名、业务标签快速模糊匹配；
  - 提供多维类型过滤（全部 / 仅 Docker 容器 / 仅 Linux 物理机 / 仅出海中 / 仅原生直连），并实时展示状态统计徽章。
- **一键克隆节点配置 (Clone Node)**：
  - 在节点操作下拉菜单中新增「📋 克隆节点」，一键带入宿主机 IP、用户名、接入通道、网关绑定与标签，助力相邻端口（如 6600, 6601）秒级扩容。
- **向导智能联动与三阶全链路深度预检 (Deep Preflight Check)**：
  - 架构感知联动：选择 Docker 容器时自动切换端口 placeholder 为 `6600`，用户名默认 `root`，并提示容器独立直连隔离特性；
  - 深度预检引擎升级：`/api/test-node-preflight` 采用递进三阶探测（TCP 三次握手 RTT -> SSH 协议 Banner 握手 -> 纯标准库 ASKPASS 密码/密钥鉴权验证），精准定位端口未通与密码错误。
- **全网并发健康巡检与操作审计日志 (Health Guard & Audit Logs)**：
  - 新增「🔄 全网巡检」功能（`POST /api/nodes/health-check-all`），并发探测全网节点实际出海状态并回填延迟徽章；
  - 新增轻量级审计日志流水（`data/audit.log` 与 `GET /api/audit-logs`），并在 Web 端提供「📜 审计日志」可视化弹窗面板。
- **容器与跨平台实机联调实测通过**：
  - 针对 Docker 映射端口（`192.168.1.102:6600`）容器，实测通过初始密码自动建信、公钥植入免密自愈，并在容器内成功验证 `curl -I https://www.google.com` (HTTP/2 200) 与 `git ls-remote` 秒级出海！

---

## [1.2.0] - 2026-11-15

### 📖 Comprehensive QuickStart Guide & Full Documentation Overhaul (全新开箱即用手册与文档全景重构)

- **全新《极简开箱即用速查手册 (QUICKSTART.md)》**：
  - 提炼 3 分钟极速上手第一站，涵盖控制台访问、4 大工业场景开箱配方、终端零命令出海检验与常见排查 FAQ；
  - 覆盖映射端口 Docker 容器（如 6600 端口）、免密 Linux 物理工作站、全新裸机密码建信自愈、轻量容器宿主机穿透等核心场景。
- **重构《README.md》官方全景手册**：
  - 增加 3 分钟极速上手置顶导航条，更新整体架构数据流向图；
  - 整合 v1.1+ 通用 SSH 远程引擎、密码建信自愈、5 列现代化拓扑 UI、一体化交互状态胶囊、强防缓存机制与完整 RESTful API 参数参考。
- **Web 控制台【📖 开发者手册】（Tab 4）交互升级**：
  - 内置 3 步场景化开箱配方与终端零命令验证指令卡片，支持一键点击复制代码。
- **系统版本统一升级至 v1.2.0**。

---

## [1.1.1] - 2026-11-15

### 🩹 Hotfix & Anti-Cache Architecture (热修复与全局防缓存升级)

- **修复 `app.js` 语法异常阻断问题**：
  - 清理多余闭合语法标记，经 `node -c` 严密编译检测通过，彻底解决外部 Chrome / Edge / 无痕模式下 JavaScript 引擎中断、Tab 切换与按钮点击无响应的严重问题。
- **全栈强制防脏缓存机制 (Anti-Cache Protection)**：
  - `web/server.py` 服务端所有静态与动态请求统一注入 `Cache-Control: no-cache, no-store, must-revalidate, max-age=0`、`Pragma: no-cache`、`Expires: 0`。
  - `index.html` 引入 `<meta>` 防缓存标签，并为 `style.css?v=1.1.1` 与 `app.js?v=1.1.1` 追加版本指纹，彻底杜绝客户端运行老旧脏缓存。
- **拓扑与节点管理界面呼吸感与空间优化**：
  - 表格设定 `min-width: 880px` 保护，单元格纵向内边距提升至 `14px 16px`，确保 5 列布局在大屏与移动端均拥有充裕呼吸空间与平滑滚动。
  - 经由真实浏览器内核多步实测通过，Tab 切换秒级生效，模态框与状态胶囊交互流畅。

---

## [1.1.0] - 2026-11-15

### 🚀 Industrial Unified Node Provisioning & Modern UI (工业级统一接入引擎与界面轻量美化)

- **全场景通用远程 SSH 接入引擎 (Unified SSH Provisioning Engine)**：
  - **物理工作站与工控机直连**：原生支持边缘物理机、工业视觉主机、ARM 开发板（默认端口 22）。
  - **端口映射 Docker 容器直连**：支持各类暴露自定义 SSH 端口（如 `-p 6600:22`）的独立开发/调试容器（如 `app-container`），直接进入容器内部配置，不再强依赖宿主机 Docker 特权。
  - **向下兼容 Docker 穿透接入**：无缝保留针对未暴露 SSH 端口容器的宿主机穿透管理通道（`access_mode: "docker_host"`）。
- **零依赖密码建信与公钥免密自愈 (Zero-Dependency Password Auth & Public-Key Auto-Enrollment)**：
  - 基于 Linux 标准库 `SSH_ASKPASS` + `setsid` 机制，在免安装 `sshpass` 等任何外部依赖的前提下，原生支持账号密码远程自动化执行脚本。
  - **工业自愈**：目标机器首次以密码接入成功后，控制节点自动将其公钥植入目标节点的 `~/.ssh/authorized_keys`，实现后续所有出海启闭、复测的“彻底免密自动巡航”。
- **拓扑与节点管理界面现代极简美化 (Streamlined Modern UI)**：
  - 表格由原先臃肿的 8 列 5 按钮全面精简重构为 5 列现代化布局（业务节点名称、终端访问地址与模式、绑定出网网关、出海通道开关、运维操作）。
  - 引入**一体化交互状态胶囊 (`.status-capsule`)**，将绿/红呼吸动效状态徽标与启闭按钮合二为一，彻底告别视觉拥挤。
  - 提取高频操作“🔍 测外网”为独立测速按钮，点击直接在按钮内呈现实时 RTT 延迟药丸（如 `1648.7ms`）；低频运维操作（编辑参数、主机连通探测、删除节点）收归至极简气泡下拉菜单（`•••`）。

---

## [1.0.0] - 2026-11-15

### 🎉 Initial Enterprise Release (v1.0.0 正式发布)

`net-proxy-tool` 是一款面向企业级局域网、受限边缘节点与 Docker 容器环境的**原生、零依赖、零系统污染、双层免命令**出海代理调度系统。

### ✨ Key Features (核心特性)
- **全栈双层免命令引擎 (Dual-Layer Zero-Command Engine)**：
  - **第一层（工具级专有即时配置）**：自动化注入并维护 `~/.curlrc`、`~/.gitconfig`、`~/.config/pip/pip.conf`、`~/.wgetrc` 与 `/etc/apt/apt.conf.d/`。即使在已运行数天、已打开的终端/tmux 会话中，直接输入 `curl`、`git`、`pip` 无需重启终端、无需执行任何配置或 source 命令即可瞬间直接出海。
  - **第二层（全局环境顶层注入）**：在 `~/.bashrc` 第 1 行首部强行注入代理环境变量，规避 Ubuntu 交互式非登录 shell 的 `[ -z "$PS1" ] && return` 提前返回机制，全面覆盖 Python `requests`/`urllib`、Go、Node.js 等通过环境变量探测代理的进程。
- **Docker 容器独立出海与环境绝对隔离 (Zero-Pollution Docker Isolation)**：
  - 纯容器内部署，精准仅让目标容器（如 `app-container`）通过局域网代理工作站出海。
  - 宿主机自身及其余容器网络栈与文件系统 100% 保持原生纯净直连，杜绝任何环境污染。
- **独立微型 Web 集中控制台 (Standalone Web Console @ Port 8899)**：
  - 纯 Python 3 原生标准库实现（基于 `http.server`、`urllib`、`socket`），**零外部 pip 依赖**。
  - 4 步渐进式接入向导（流水线状态机）。
  - 目标业务节点池（Worker Nodes）与代理网关池（Gateway Pool）完整增删改查（CRUD）管理。
  - 7 大全球顶级服务（Google、GitHub、Raw GitHub、HuggingFace、PyPI、OpenAI API、YouTube）多线程并发实时连通性诊断与延迟测试。
  - 节点出海开关一键切换（`/api/node-switch`）与实机连通性实时回环复测（`/api/node-test`）。
- **多形态跨平台即启即销工具链 (Ephemeral Proxy Suite)**：
  - 跨平台 `with-proxy` CLI（Linux/macOS Bash, Windows PowerShell/CMD）。
  - Python 原生上下文管理器 SDK (`with ProxySession(): ...`)，退出作用域或抛出异常时 100% 保证环境变量注销。
  - 会话级临时出海开关脚本 (`proxy-on` / `proxy-off`)。
- **网关保活看门狗 (Gateway Watchdog)**：
  - 局域网代理服务（如 Clash / Mihomo）故障自动检测与用户态保活自愈机制。
