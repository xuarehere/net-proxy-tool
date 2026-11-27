"""The console messages in English and Simplified Chinese.

Every key exists in both languages. The browser receives this catalogue
from /api/i18n.js, and the server uses it to localize the `error` and
`message` fields of an API answer.
"""

import json
import re

LANGUAGES = ("en", "zh-CN")
DEFAULT_LANGUAGE = "zh-CN"
PLACEHOLDER = re.compile(r"\{([A-Za-z0-9_]+)\}")

MESSAGES = {
    'HTTP 请求完成': {
        "en": 'The HTTP request is complete',
        "zh-CN": 'HTTP 请求完成',
    },
    'HTTP 请求超过总超时': {
        "en": 'The HTTP request exceeded the total timeout',
        "zh-CN": 'HTTP 请求超过总超时',
    },
    'SSH 密钥免密验证通过': {
        "en": 'The SSH key authentication succeeded',
        "zh-CN": 'SSH 密钥免密验证通过',
    },
    'SSH 连接、主机密钥核验或所选身份认证失败': {
        "en": 'The SSH connection, the host key check or the selected identity failed',
        "zh-CN": 'SSH 连接、主机密钥核验或所选身份认证失败',
    },
    'SSH 连接探测异常: {e}': {
        "en": 'The SSH connection probe failed: {e}',
        "zh-CN": 'SSH 连接探测异常: {e}',
    },
    'Windows 本机请使用单命令或 PowerShell 会话代理': {
        "en": 'On Windows, use the one-command proxy or a PowerShell session proxy',
        "zh-CN": 'Windows 本机请使用单命令或 PowerShell 会话代理',
    },
    'action 必须是 start 或 stop': {
        "en": 'action must be start or stop',
        "zh-CN": 'action 必须是 start 或 stop',
    },
    'advanced-wizard-h2': {
        "en": '🎯 Worker node tunnel and proxy wizard',
        "zh-CN": '🎯 业务节点网络穿透与代理接入向导',
    },
    'advanced-wizard-p': {
        "en": 'To keep a long-term proxy setting on a Linux account or a container, choose the gateway, choose the worker node and check the connection.',
        "zh-CN": '要为 Linux 账号或容器保存长期代理设置时，请依次选择网关、目标节点并检查连接。',
    },
    'attachCopyButtons': {
        "en": 'Copied! ✓',
        "zh-CN": '已复制! ✓',
    },
    'bindRowTarget': {
        "en": 'Use the target of the node pool',
        "zh-CN": '使用节点池目标',
    },
    'brand-sub': {
        "en": 'HTTP proxy console',
        "zh-CN": 'HTTP 代理控制台',
    },
    'card-step-1-h3': {
        "en": 'Confirm and verify the proxy gateway',
        "zh-CN": '确认并验证代理网关节点 (Gateway)',
    },
    'card-step-1-step-badge': {
        "en": 'Step 1',
        "zh-CN": '步骤 1',
    },
    'card-step-2-h3': {
        "en": 'Choose or register the worker node',
        "zh-CN": '指定/登记目标业务节点 (Worker Node)',
    },
    'card-step-2-step-badge': {
        "en": 'Step 2',
        "zh-CN": '步骤 2',
    },
    'card-step-3-h3': {
        "en": 'End-to-end diagnostic',
        "zh-CN": '全链路穿透体检 (End-to-End Diagnostic)',
    },
    'card-step-3-step-badge': {
        "en": 'Step 3',
        "zh-CN": '步骤 3',
    },
    'card-step-4-h3': {
        "en": 'Apply the proxy configuration and verify the node',
        "zh-CN": '下发代理配置并验证目标节点',
    },
    'card-step-4-step-badge': {
        "en": 'Step 4',
        "zh-CN": '步骤 4',
    },
    'curl 未完成请求 (exit {})': {
        "en": 'curl did not complete the request (exit {})',
        "zh-CN": 'curl 未完成请求 (exit {})',
    },
    'curl 未返回可解析的请求结果': {
        "en": 'curl returned no result that could be parsed',
        "zh-CN": 'curl 未返回可解析的请求结果',
    },
    'finishSetupSave': {
        "en": 'Switching the default gateway…',
        "zh-CN": '正在切换默认网关…',
    },
    'finishSetupSave-2': {
        "en": 'It is now the default gateway.',
        "zh-CN": '已设为默认网关。',
    },
    'finishSetupSave-3': {
        "en": 'Saving and reading the gateway configuration…',
        "zh-CN": '正在保存并读取网关配置…',
    },
    'finishSetupSave-4': {
        "en": 'The gateway is saved. Click Send a proxy request to check the target site.',
        "zh-CN": '已保存网关。点击“发送代理请求”以验证目标站点。',
    },
    'finishSetupSave-5': {
        "en": 'Connecting to the proxy and requesting the target site…',
        "zh-CN": '正在连接代理并请求目标站点…',
    },
    'footer-gw-label': {
        "en": 'Not configured',
        "zh-CN": '未配置',
    },
    'footer-gw-label-text': {
        "en": 'Current outbound gateway:',
        "zh-CN": '当前出网网关:',
    },
    'form-client-access-mode-option': {
        "en": 'Local execution (with the account that runs the console)',
        "zh-CN": '本机执行（使用运行控制台的账号）',
    },
    'form-client-access-mode-option-2': {
        "en": '🚀 Direct SSH access (recommended: physical workstations, controllers, edge devices and containers with a mapped port)',
        "zh-CN": '🚀 通用 SSH 直连接入 (推荐：支持物理工作站、工控机、边缘设备及映射端口容器)',
    },
    'form-client-access-mode-option-3': {
        "en": '🐳 Docker host access (compatible: for lightweight containers without an exposed SSH port)',
        "zh-CN": '🐳 宿主机 Docker 穿透接入 (向下兼容：适用于未暴露 SSH 的轻量微服务容器)',
    },
    'form-client-auth-type-option': {
        "en": '🔑 SSH key without a password (recommended, the public key is already trusted)',
        "zh-CN": '🔑 SSH 密钥免密 (默认推荐，已有公钥信任)',
    },
    'form-client-auth-type-option-2': {
        "en": '🔒 Password authentication (Linux and macOS controllers)',
        "zh-CN": '🔒 密码认证（Linux / macOS 控制端）',
    },
    'form-client-container-label': {
        "en": 'Docker host IP *:',
        "zh-CN": '宿主机 IP 地址 *:',
    },
    'form-client-gw-label': {
        "en": 'Operations and delivery channel *:',
        "zh-CN": '节点运维与下发通道 *:',
    },
    'form-client-host-label': {
        "en": 'SSH port *:',
        "zh-CN": 'SSH 端口 *:',
    },
    'form-client-host-port-label': {
        "en": 'Docker host user (key authentication) *:',
        "zh-CN": '宿主机免密用户名 *:',
    },
    'form-client-id-label': {
        "en": 'Operating system:',
        "zh-CN": '操作系统架构:',
    },
    'form-client-mode-label': {
        "en": 'Worker node name *:',
        "zh-CN": '业务节点名称 *:',
    },
    'form-client-name-label': {
        "en": 'Node identifier (ID, generated when left empty):',
        "zh-CN": '节点唯一标识 (ID, 留空自动生成):',
    },
    'form-client-os-label': {
        "en": 'Default outbound gateway:',
        "zh-CN": '绑定默认出网网关:',
    },
    'form-client-os-option': {
        "en": 'Linux workstation, virtual machine or edge device',
        "zh-CN": 'Linux 物理工作站 / 虚拟机 / 边缘设备',
    },
    'form-client-os-option-2': {
        "en": 'Docker container (isolated environment)',
        "zh-CN": 'Docker 容器 (独立环境)',
    },
    'form-client-os-option-3': {
        "en": 'Windows machine or developer computer',
        "zh-CN": 'Windows 本机 / 开发机',
    },
    'form-client-os-option-4': {
        "en": 'macOS workstation',
        "zh-CN": 'macOS 工作站',
    },
    'form-client-port-label': {
        "en": 'SSH user *:',
        "zh-CN": 'SSH 登录用户名 *:',
    },
    'form-client-ssh-host-label': {
        "en": 'Docker host SSH port',
        "zh-CN": '宿主机 SSH 端口',
    },
    'form-client-ssh-pass-input-tip-sub': {
        "en": 'Windows, Linux and macOS all support SSH keys and passwords against a verified host key. The password belongs only to the address, port and account given here; a change of identity needs it again, and no public key is registered for you. Leaving the password empty while editing keeps the password saved for that identity.',
        "zh-CN": 'Windows、Linux 与 macOS 均支持已核验主机密钥的 SSH 密钥或密码登录。密码只用于此处明确的地址、端口与账号；修改身份时需重新输入，不会自动注册公钥。编辑时密码留空表示沿用原身份已保存的密码。',
    },
    'form-client-ssh-user-host-label': {
        "en": 'Tags (comma separated):',
        "zh-CN": '业务标签 (逗号分隔):',
    },
    'form-client-ssh-user-label': {
        "en": 'SSH authentication:',
        "zh-CN": 'SSH 认证方式:',
    },
    'form-client-tags-label': {
        "en": 'Description:',
        "zh-CN": '节点描述备注:',
    },
    'form-group-client-pass-label': {
        "en": 'SSH password',
        "zh-CN": 'SSH 登录密码',
    },
    'form-gw-host-label': {
        "en": 'Port *:',
        "zh-CN": '端口 *:',
    },
    'form-gw-id-label': {
        "en": 'Gateway name *:',
        "zh-CN": '网关名称 *:',
    },
    'form-gw-mode-label': {
        "en": 'Gateway identifier (ID, generated when left empty):',
        "zh-CN": '网关唯一标识 (ID, 留空自动生成):',
    },
    'form-gw-name-label': {
        "en": 'Server IP or name *:',
        "zh-CN": '服务器 IP / 域名 *:',
    },
    'form-gw-port-label': {
        "en": 'Protocol:',
        "zh-CN": '协议类型:',
    },
    'form-gw-protocol-label': {
        "en": 'Description:',
        "zh-CN": '描述说明:',
    },
    'form-gw-protocol-option': {
        "en": 'HTTP or HTTPS proxy',
        "zh-CN": 'HTTP / HTTPS 代理',
    },
    'form-gw-protocol-option-2': {
        "en": 'SOCKS5 proxy',
        "zh-CN": 'SOCKS5 代理',
    },
    'formatPeer': {
        "en": 'not obtained',
        "zh-CN": '未取得',
    },
    'gateway-target-label': {
        "en": 'Gateway probe target',
        "zh-CN": '网关探测目标地址',
    },
    'gateway-target-url-th': {
        "en": 'Gateway',
        "zh-CN": '网关名称',
    },
    'gateway-target-url-th-2': {
        "en": 'IP or host name',
        "zh-CN": 'IP / 主机名',
    },
    'gateway-target-url-th-3': {
        "en": 'Port',
        "zh-CN": '端口',
    },
    'gateway-target-url-th-4': {
        "en": 'Protocol',
        "zh-CN": '协议',
    },
    'gateway-target-url-th-5': {
        "en": 'Default',
        "zh-CN": '默认状态',
    },
    'gateway-target-url-th-6': {
        "en": 'Description',
        "zh-CN": '描述',
    },
    'gateway-target-url-th-7': {
        "en": 'Actions',
        "zh-CN": '操作',
    },
    'global-gw-status-text': {
        "en": 'No gateway selected',
        "zh-CN": '尚未选择网关',
    },
    'handbook-docker-p-1': {
        "en": 'Run it in a Bash terminal with the Docker CLI and access to the container. Replace ',
        "zh-CN": '在有 Docker CLI 和容器访问权限的 Bash 终端执行。把',
    },
    'handbook-docker-p-2': {
        "en": ' with the name of a running container that has curl installed. The proxy address saved in the console must be reachable from the container; ',
        "zh-CN": '换为已运行且安装了 curl 的容器名称。控制台里保存的代理地址须从容器可达；容器内的',
    },
    'handbook-docker-p-3': {
        "en": ' points at the container itself.',
        "zh-CN": '指向容器自身。',
    },
    'handbook-sdk-p-1': {
        "en": 'Save the code as ',
        "zh-CN": '将代码保存为包根目录的',
    },
    'handbook-sdk-p-2': {
        "en": ' in the root of the package and run it from the same directory. On Windows use ',
        "zh-CN": '，从同一目录运行。Windows 使用',
    },
    'handbook-sdk-p-3': {
        "en": ', on Linux or macOS use ',
        "zh-CN": '，Linux / macOS 使用',
    },
    'handbook-sdk-p-4': {
        "en": '. The proxy variables of the current process are restored when the block exits.',
        "zh-CN": '。退出上下文后会还原当前进程原有的代理环境变量。',
    },
    'handover-gw-label': {
        "en": '| Bound gateway:',
        "zh-CN": '| 已绑定网关:',
    },
    'handover-gw-name': {
        "en": 'Not selected',
        "zh-CN": '未选择',
    },
    'handover-target-label': {
        "en": 'Current node:',
        "zh-CN": '当前目标节点:',
    },
    'handover-target-name': {
        "en": 'Not selected',
        "zh-CN": '未选择',
    },
    'hb-docker-h3': {
        "en": 'Keep a proxy enabled for a remote account',
        "zh-CN": '为远程账号长期启用代理',
    },
    'hb-docker-p': {
        "en": 'Register a Linux node or a container in the node management view with its SSH user, host and real port. A Windows controller uses an OpenSSH key. The Docker host mode also needs that account to run docker exec. Save it and run the pre-check first.',
        "zh-CN": '在「拓扑与节点管理」登记 Linux 节点或容器，填写 SSH 用户、主机和实际端口。Windows 控制端使用 OpenSSH 密钥。宿主机 Docker 模式还需要该登录账号可执行 docker exec。保存后可先做预检。',
    },
    'hb-docker-p-2': {
        "en": 'The tool and shell configuration is written only when you enable it explicitly. The target is the selected account or container, and running as root can also change system-wide settings on the target. Stopping restores the snapshot. When the file was edited by hand or an older version left no snapshot, read the notice and check the backup.',
        "zh-CN": '显式开启时才会下发工具和 shell 配置。操作目标是所选账号或容器，以 root 执行时还可能修改目标系统级配置。关闭时按快照恢复。遇到人工编辑或旧版缺少快照时，请查看提示并核对备份。',
    },
    'hb-docker-span': {
        "en": 'Net-Proxy-Tool v1.5.0 · HTTP proxy console',
        "zh-CN": 'Net-Proxy-Tool v1.5.0 · HTTP 代理控制台',
    },
    'hb-sdk-btn-copy': {
        "en": 'Copy the example',
        "zh-CN": '复制示例',
    },
    'hb-sdk-strong': {
        "en": 'One command inside a container',
        "zh-CN": '容器内运行单次命令',
    },
    'hb-unix-btn-copy': {
        "en": 'Copy the example',
        "zh-CN": '复制示例',
    },
    'hb-win-btn-copy': {
        "en": 'Copy the command',
        "zh-CN": '复制命令',
    },
    'hb-win-p': {
        "en": 'Run it in the extracted folder of the portable archive. Bash and curl must already be installed. The source archive also needs Python 3.8 or newer.',
        "zh-CN": '在便携包的解压目录执行。需要系统中已有 Bash 和 curl。源码包另需 Python 3.8 或更高版本。',
    },
    'hb-win-strong': {
        "en": 'One command on Linux or macOS',
        "zh-CN": 'Linux / macOS 单次命令',
    },
    'httpJourney': {
        "en": 'First hop HTTP ',
        "zh-CN": '首跳 HTTP ',
    },
    'httpJourney-2': {
        "en": 'First hop status unknown',
        "zh-CN": '首跳状态未知',
    },
    'httpJourney-3': {
        "en": 'Final HTTP ',
        "zh-CN": '最终 HTTP ',
    },
    'httpJourney-4': {
        "en": 'No final HTTP status received',
        "zh-CN": '未收到最终 HTTP 状态',
    },
    'initTargetGridPlaceholder': {
        "en": 'No multi-site target is configured; you can still verify the selected node.',
        "zh-CN": '没有配置多站目标，可继续验证所选节点。',
    },
    'initTargetGridPlaceholder-10': {
        "en": 'No multi-site target is configured',
        "zh-CN": '未配置多站目标',
    },
    'initTargetGridPlaceholder-11': {
        "en": 'The multi-site test was skipped',
        "zh-CN": '已跳过多站测试',
    },
    'initTargetGridPlaceholder-12': {
        "en": 'The multi-site test is complete',
        "zh-CN": '多站测试已完成',
    },
    'initTargetGridPlaceholder-13': {
        "en": '⚠️ The path check is unusual ({onlineCount}/{length} online)',
        "zh-CN": '⚠️ 穿透异常 ({onlineCount}/{length} 在线)',
    },
    'initTargetGridPlaceholder-14': {
        "en": 'Most of the external target sites were not reachable through the proxy. Check the node configuration of the selected gateway or the network policy.',
        "zh-CN": '大部分境外目标站点未能通过代理访问，请检查所选网关的节点配置或网络策略。',
    },
    'initTargetGridPlaceholder-15': {
        "en": '❌ The diagnostic request failed',
        "zh-CN": '❌ 诊断请求异常',
    },
    'initTargetGridPlaceholder-16': {
        "en": 'The diagnostic request failed: ',
        "zh-CN": '体检请求失败: ',
    },
    'initTargetGridPlaceholder-17': {
        "en": '<span class="btn-icon">🚀</span> Run the end-to-end diagnostic again',
        "zh-CN": '<span class="btn-icon">🚀</span> 重新执行全链路体检',
    },
    'initTargetGridPlaceholder-2': {
        "en": '<span class="btn-icon">⏳</span> Running the end-to-end diagnostic…',
        "zh-CN": '<span class="btn-icon">⏳</span> 正在执行全网穿透体检...',
    },
    'initTargetGridPlaceholder-3': {
        "en": '⚡ Probing the path…',
        "zh-CN": '⚡ 正在穿透探测...',
    },
    'initTargetGridPlaceholder-4': {
        "en": 'Probing…',
        "zh-CN": '探测中...',
    },
    'initTargetGridPlaceholder-5': {
        "en": 'Diagnostic time: {timestamp}',
        "zh-CN": '体检时间: {timestamp}',
    },
    'initTargetGridPlaceholder-6': {
        "en": '🟢 Online (HTTP {code})',
        "zh-CN": '🟢 在线 (HTTP {code})',
    },
    'initTargetGridPlaceholder-7': {
        "en": 'The request did not succeed',
        "zh-CN": '请求未成功',
    },
    'initTargetGridPlaceholder-8': {
        "en": 'Check the gateway and the target address',
        "zh-CN": '请查看网关与目标地址',
    },
    'initTargetGridPlaceholder-9': {
        "en": 'Tested: {onlineCount}/{length} target requests succeeded',
        "zh-CN": '已测试，{onlineCount}/{length} 个目标请求成功',
    },
    'loadAuditLogs': {
        "en": '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:18px;">Reading the audit trail…</td></tr>',
        "zh-CN": '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:18px;">正在读取审计流水...</td></tr>',
    },
    'loadAuditLogs-2': {
        "en": '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:18px;">No operation has been recorded yet</td></tr>',
        "zh-CN": '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:18px;">暂无操作审计记录</td></tr>',
    },
    'loadAuditLogs-3': {
        "en": 'succeeded',
        "zh-CN": '成功',
    },
    'loadAuditLogs-4': {
        "en": 'failed',
        "zh-CN": '失败',
    },
    'loadAuditLogs-5': {
        "en": '<tr><td colspan="5" style="color:var(--danger);">Could not load it: {message}</td></tr>',
        "zh-CN": '<tr><td colspan="5" style="color:var(--danger);">加载失败: {message}</td></tr>',
    },
    'loadConfig': {
        "en": 'Could not load the configuration: ',
        "zh-CN": '加载配置失败: ',
    },
    'loadConfig-2': {
        "en": 'The configuration could not be loaded',
        "zh-CN": '配置加载失败',
    },
    'loadLocalGatewayState': {
        "en": 'The state of the local gateway could not be read',
        "zh-CN": '无法读取本机网关状态',
    },
    'local-gateway-demo': {
        "en": 'Try it now',
        "zh-CN": '立即体验',
    },
    'local-gateway-panel-p': {
        "en": 'The tool ships with an observation gateway that listens only on this machine, so you can try the whole proxy flow right away.',
        "zh-CN": '工具自带一个只监听本机的观测网关，可以立刻体验代理请求的完整过程。',
    },
    'local-gateway-panel-strong': {
        "en": 'No proxy yet?',
        "zh-CN": '没有可用的代理？',
    },
    'local-gateway-start': {
        "en": 'Enable the local observation gateway',
        "zh-CN": '启用本机观测网关',
    },
    'local-gateway-stop': {
        "en": 'Stop the local gateway',
        "zh-CN": '停止本机网关',
    },
    'localGatewayAction': {
        "en": 'The local gateway action failed',
        "zh-CN": '本机网关操作失败',
    },
    'localGatewayAction-2': {
        "en": 'Local observation gateway',
        "zh-CN": '本机观测网关',
    },
    'modal-audit-close-audit-subdesc': {
        "en": 'Managed switches, configuration restorations, node changes and health checks (the last 60 entries)',
        "zh-CN": '查看托管开关、配置恢复、节点变更和巡检记录（最近 60 条）',
    },
    'modal-audit-close-btn': {
        "en": 'Close',
        "zh-CN": '关闭',
    },
    'modal-audit-h3': {
        "en": '📜 Audit trail of node operations',
        "zh-CN": '📜 节点出海操作审计与事件流水',
    },
    'modal-audit-refresh-btn': {
        "en": '🔄 Refresh',
        "zh-CN": '🔄 刷新流水',
    },
    'modal-audit-refresh-btn-th': {
        "en": 'Time',
        "zh-CN": '记录时间',
    },
    'modal-audit-refresh-btn-th-2': {
        "en": 'Action',
        "zh-CN": '操作类型',
    },
    'modal-audit-refresh-btn-th-3': {
        "en": 'Node',
        "zh-CN": '目标节点',
    },
    'modal-audit-refresh-btn-th-4': {
        "en": 'Result',
        "zh-CN": '结果',
    },
    'modal-audit-refresh-btn-th-5': {
        "en": 'Details',
        "zh-CN": '事件详情 / 提示',
    },
    'modal-client-title': {
        "en": '➕ Register a worker node',
        "zh-CN": '➕ 登记新业务节点',
    },
    'modal-gw-title': {
        "en": '➕ Add a proxy gateway',
        "zh-CN": '➕ 添加新代理网关',
    },
    'modal-target-label': {
        "en": 'Request target address',
        "zh-CN": '请求目标地址',
    },
    'node-default-target-label': {
        "en": 'Default and check target of the node pool',
        "zh-CN": '节点池默认及巡检目标',
    },
    'node-filter-type-option': {
        "en": '🌐 All node types',
        "zh-CN": '🌐 全部节点类型',
    },
    'node-filter-type-option-2': {
        "en": '🐳 Docker containers only',
        "zh-CN": '🐳 仅 Docker 容器',
    },
    'node-filter-type-option-3': {
        "en": '🐧 Linux machines and workstations only',
        "zh-CN": '🐧 仅 Linux 物理机 / 工作站',
    },
    'node-filter-type-option-4': {
        "en": 'Managed state enabled only',
        "zh-CN": '仅托管记录已开启',
    },
    'node-filter-type-option-5': {
        "en": 'Not verified',
        "zh-CN": '未核验',
    },
    'node-filter-type-option-6': {
        "en": '🛑 Managed state disabled only',
        "zh-CN": '🛑 仅托管记录已关闭',
    },
    'node-stats-badge': {
        "en": 'Reading the nodes',
        "zh-CN": '正在读取节点',
    },
    'node-stats-badge-th': {
        "en": 'Worker node',
        "zh-CN": '业务节点名称',
    },
    'node-stats-badge-th-2': {
        "en": 'Address and mode',
        "zh-CN": '终端访问地址 & 模式',
    },
    'node-stats-badge-th-3': {
        "en": 'Bound gateway',
        "zh-CN": '绑定出网网关',
    },
    'node-stats-badge-th-4': {
        "en": 'Managed state',
        "zh-CN": '托管配置记录',
    },
    'node-stats-badge-th-5': {
        "en": 'Actions',
        "zh-CN": '运维操作',
    },
    'nodeCheckLabel': {
        "en": 'Succeeded (HTTP request)',
        "zh-CN": '成功（HTTP 请求）',
    },
    'nodeCheckLabel-2': {
        "en": 'Did not succeed (HTTP request)',
        "zh-CN": '未成功（HTTP 请求）',
    },
    'nodeCheckLines': {
        "en": 'Not executed',
        "zh-CN": '未执行',
    },
    'nodeCheckLines-10': {
        "en": 'SSH authentication · ',
        "zh-CN": 'SSH 认证 · ',
    },
    'nodeCheckLines-11': {
        "en": 'passed',
        "zh-CN": '通过',
    },
    'nodeCheckLines-12': {
        "en": 'failed',
        "zh-CN": '失败',
    },
    'nodeCheckLines-13': {
        "en": 'Service identity and permissions · ',
        "zh-CN": '业务身份/权限 · ',
    },
    'nodeCheckLines-14': {
        "en": 'The target refused the access',
        "zh-CN": '目标拒绝访问',
    },
    'nodeCheckLines-15': {
        "en": 'verified',
        "zh-CN": '已验证',
    },
    'nodeCheckLines-16': {
        "en": 'The login state and the account permissions were not verified',
        "zh-CN": '未验证登录状态及账户权限',
    },
    'nodeCheckLines-17': {
        "en": 'Hop ',
        "zh-CN": '第 ',
    },
    'nodeCheckLines-18': {
        "en": ' peer · ',
        "zh-CN": ' 跳对端 · ',
    },
    'nodeCheckLines-19': {
        "en": 'Final address · ',
        "zh-CN": '最终地址 · ',
    },
    'nodeCheckLines-2': {
        "en": 'Scope · ',
        "zh-CN": '执行范围 · ',
    },
    'nodeCheckLines-20': {
        "en": 'Explicit proxy · ',
        "zh-CN": '显式代理 · ',
    },
    'nodeCheckLines-21': {
        "en": 'TCP peer · ',
        "zh-CN": 'TCP 对端 · ',
    },
    'nodeCheckLines-22': {
        "en": 'Proxy CONNECT · HTTP ',
        "zh-CN": '代理 CONNECT · HTTP ',
    },
    'nodeCheckLines-23': {
        "en": 'connected to the selected proxy',
        "zh-CN": '连接了选定的代理',
    },
    'nodeCheckLines-24': {
        "en": 'the same proxy peer as the explicit request',
        "zh-CN": '与显式请求的代理对端一致',
    },
    'nodeCheckLines-25': {
        "en": 'a different proxy peer than the explicit request',
        "zh-CN": '与显式请求的代理对端不同',
    },
    'nodeCheckLines-26': {
        "en": 'The proxy path could not be confirmed',
        "zh-CN": '未能确认代理路径',
    },
    'nodeCheckLines-27': {
        "en": 'Proxy path · ',
        "zh-CN": '代理路径 · ',
    },
    'nodeCheckLines-28': {
        "en": 'Execution user',
        "zh-CN": '执行用户',
    },
    'nodeCheckLines-29': {
        "en": 'Detected curl configuration · ',
        "zh-CN": '检测到的 curl 配置 · ',
    },
    'nodeCheckLines-3': {
        "en": 'Independent login shell (the account starts its own configuration)',
        "zh-CN": '独立登录 shell（按该账号启动配置）',
    },
    'nodeCheckLines-30': {
        "en": '(the explicit request ignores it with -q)',
        "zh-CN": '（显式请求以 -q 忽略）',
    },
    'nodeCheckLines-31': {
        "en": 'Command exit code ',
        "zh-CN": '命令退出码 ',
    },
    'nodeCheckLines-4': {
        "en": 'Console process on this machine',
        "zh-CN": '本机控制台进程',
    },
    'nodeCheckLines-5': {
        "en": 'This console machine',
        "zh-CN": '控制台本机',
    },
    'nodeCheckLines-6': {
        "en": 'SSH node',
        "zh-CN": 'SSH 节点',
    },
    'nodeCheckLines-7': {
        "en": 'Target container on the Docker host over SSH',
        "zh-CN": 'SSH 宿主机上的目标容器',
    },
    'nodeCheckLines-8': {
        "en": 'Execution place · ',
        "zh-CN": '执行位置 · ',
    },
    'nodeCheckLines-9': {
        "en": 'Request duration · ',
        "zh-CN": '请求耗时 · ',
    },
    'nodeCheckPairs': {
        "en": 'Explicitly selected gateway',
        "zh-CN": '显式指定网关',
    },
    'nodeCheckPairs-2': {
        "en": 'Plain curl (the current settings of the target)',
        "zh-CN": '普通 curl（目标当前设置）',
    },
    'nodeCheckPairs-3': {
        "en": 'A proxy that existed before the enabling may still apply. Repeat the current path with a plain curl to check.',
        "zh-CN": '启用前已有的代理可能继续生效。可用普通 curl 复测当前路径。',
    },
    'nodeContext': {
        "en": 'unknown',
        "zh-CN": '未知',
    },
    'nodeContext-10': {
        "en": 'Latest configuration check · ',
        "zh-CN": '最近配置核验 · ',
    },
    'nodeContext-11': {
        "en": 'Verification scope · ',
        "zh-CN": '核验范围 · ',
    },
    'nodeContext-12': {
        "en": 'the independent login environment and the managed files',
        "zh-CN": '独立登录环境与托管文件',
    },
    'nodeContext-13': {
        "en": 'the original snapshot files (a direct connection is not assumed)',
        "zh-CN": '原快照文件（不推定直连）',
    },
    'nodeContext-14': {
        "en": 'the managed files and the execution identity',
        "zh-CN": '托管文件与执行身份',
    },
    'nodeContext-15': {
        "en": 'not verified yet',
        "zh-CN": '尚未核验',
    },
    'nodeContext-16': {
        "en": 'Public exit IP · not verified',
        "zh-CN": '公网出口 IP · 未核验',
    },
    'nodeContext-2': {
        "en": 'enabled',
        "zh-CN": '已开启',
    },
    'nodeContext-3': {
        "en": 'disabled',
        "zh-CN": '已关闭',
    },
    'nodeContext-4': {
        "en": 'verified as enabled',
        "zh-CN": '已核验开启',
    },
    'nodeContext-5': {
        "en": 'verified as restored to the original baseline',
        "zh-CN": '已核验恢复原基线',
    },
    'nodeContext-6': {
        "en": 'not verified',
        "zh-CN": '未核验',
    },
    'nodeContext-7': {
        "en": 'Request target · ',
        "zh-CN": '请求目标 · ',
    },
    'nodeContext-8': {
        "en": 'unknown',
        "zh-CN": '未知',
    },
    'nodeContext-9': {
        "en": 'Managed configuration record · ',
        "zh-CN": '托管配置记录 · ',
    },
    'nodeProbeSummary': {
        "en": 'No result for a target request yet',
        "zh-CN": '尚无目标请求结果',
    },
    'openClientModal': {
        "en": 'Not bound (choose one and enable it after saving)',
        "zh-CN": '未绑定（保存后再选择开启）',
    },
    'openClientModal-10': {
        "en": '<span class="btn-icon">⏳</span> Running the deep pre-check…',
        "zh-CN": '<span class="btn-icon">⏳</span> 深度预检中...',
    },
    'openClientModal-11': {
        "en": '🔍 Running the three-stage pre-check (TCP handshake → SSH banner → credential check)…',
        "zh-CN": '🔍 正在进行三阶深度预检 (TCP握手 -> SSH协议Banner -> 凭据鉴权)...',
    },
    'openClientModal-12': {
        "en": 'The probe failed: {message}',
        "zh-CN": '探测异常: {message}',
    },
    'openClientModal-13': {
        "en": '<span class="btn-icon">⚡</span> Pre-check the host connectivity',
        "zh-CN": '<span class="btn-icon">⚡</span> 预检主机连通性',
    },
    'openClientModal-14': {
        "en": 'Fill in the node name',
        "zh-CN": '请填写节点名称',
    },
    'openClientModal-15': {
        "en": '❌ Fill in the node name, the Docker host IP and the container name',
        "zh-CN": '❌ 请填写节点名称、宿主机 IP 以及 Docker 容器名称',
    },
    'openClientModal-16': {
        "en": '❌ Fill in the node name and the host IP',
        "zh-CN": '❌ 请填写节点名称和主机 IP',
    },
    'openClientModal-17': {
        "en": '❌ {error}{mode______edit_________________________________}',
        "zh-CN": '❌ {error}{mode______edit_________________________________}',
    },
    'openClientModal-18': {
        "en": 'Could not save it: {message}',
        "zh-CN": '保存异常: {message}',
    },
    'openClientModal-2': {
        "en": '📋 Clone the registration',
        "zh-CN": '📋 克隆登记新节点',
    },
    'openClientModal-3': {
        "en": '➕ Register a worker node',
        "zh-CN": '➕ 登记新业务节点',
    },
    'openClientModal-4': {
        "en": '{name} (copy)',
        "zh-CN": '{name} (副本)',
    },
    'openClientModal-5': {
        "en": 'Change the execution address or the identity. The same execution identity keeps the original record, and the password has to be entered again.',
        "zh-CN": '请修改执行地址或身份；相同执行身份会保留原登记，密码需重新输入。',
    },
    'openClientModal-6': {
        "en": '✏️ Edit the worker node',
        "zh-CN": '✏️ 编辑业务节点',
    },
    'openClientModal-7': {
        "en": 'The old record was executed locally. Save it in the local mode and restore the baseline first, then move it to SSH.',
        "zh-CN": '旧记录曾按本机执行。请先选择本机模式保存并恢复基线，再迁移到 SSH。',
    },
    'openClientModal-8': {
        "en": '❌ Fill in the Docker host IP and the container name first',
        "zh-CN": '❌ 请先填写宿主机 IP 和 Docker 容器内部名称',
    },
    'openClientModal-9': {
        "en": '❌ Fill in the target host IP first',
        "zh-CN": '❌ 请先填写目标主机 IP',
    },
    'openGatewayModal': {
        "en": '➕ Add a proxy gateway',
        "zh-CN": '➕ 添加新代理网关',
    },
    'openGatewayModal-2': {
        "en": '✏️ Edit the proxy gateway',
        "zh-CN": '✏️ 编辑代理网关',
    },
    'openGatewayModal-3': {
        "en": '❌ Fill in the gateway host and port',
        "zh-CN": '❌ 请填写网关主机与端口',
    },
    'openGatewayModal-4': {
        "en": 'The test failed: {message}',
        "zh-CN": '测试异常: {message}',
    },
    'openGatewayModal-5': {
        "en": '❌ Fill in the gateway name, the host IP and the port',
        "zh-CN": '❌ 请填写网关名称、主机 IP 和端口',
    },
    'openGatewayModal-6': {
        "en": 'Could not save it: {message}',
        "zh-CN": '保存异常: {message}',
    },
    'pipe-step-1-pipe-name': {
        "en": 'Verify the proxy gateway',
        "zh-CN": '校验代理网关',
    },
    'pipe-step-2-pipe-name': {
        "en": 'Bind the worker node',
        "zh-CN": '绑定业务节点',
    },
    'pipe-step-3-pipe-name': {
        "en": 'Diagnose the whole path',
        "zh-CN": '全链路穿透诊断',
    },
    'pipe-step-4-pipe-name': {
        "en": 'Hand over a working setup',
        "zh-CN": '开箱即用交付',
    },
    'probeConclusion': {
        "en": 'Proxy request succeeded · final HTTP ',
        "zh-CN": '代理请求成功 · 最终 HTTP ',
    },
    'probeConclusion-10': {
        "en": 'the target',
        "zh-CN": '目标',
    },
    'probeConclusion-11': {
        "en": ' returned no final HTTP response',
        "zh-CN": ' 未返回最终 HTTP 响应',
    },
    'probeConclusion-12': {
        "en": 'The proxy',
        "zh-CN": '代理',
    },
    'probeConclusion-13': {
        "en": 'asks for authentication',
        "zh-CN": '要求身份验证',
    },
    'probeConclusion-14': {
        "en": 'refused to open the tunnel',
        "zh-CN": '拒绝建立隧道',
    },
    'probeConclusion-15': {
        "en": 'The redirect did not complete',
        "zh-CN": '重定向未完成',
    },
    'probeConclusion-16': {
        "en": 'The target request did not succeed · HTTP ',
        "zh-CN": '目标请求未成功 · HTTP ',
    },
    'probeConclusion-17': {
        "en": 'The proxy request',
        "zh-CN": '代理请求',
    },
    'probeConclusion-18': {
        "en": 'failed',
        "zh-CN": '失败',
    },
    'probeConclusion-2': {
        "en": 'Target address check',
        "zh-CN": '目标地址校验',
    },
    'probeConclusion-3': {
        "en": 'Gateway TCP connection',
        "zh-CN": '网关 TCP 连接',
    },
    'probeConclusion-4': {
        "en": 'Proxy CONNECT',
        "zh-CN": '代理 CONNECT',
    },
    'probeConclusion-5': {
        "en": 'TLS handshake',
        "zh-CN": 'TLS 握手',
    },
    'probeConclusion-6': {
        "en": 'Waiting for the target response',
        "zh-CN": '等待目标响应',
    },
    'probeConclusion-7': {
        "en": 'Reading the response body',
        "zh-CN": '读取响应内容',
    },
    'probeConclusion-8': {
        "en": 'Request',
        "zh-CN": '请求',
    },
    'probeConclusion-9': {
        "en": 'Timed out · ',
        "zh-CN": '超时 · ',
    },
    'probeEvidence': {
        "en": 'Proxy gateway · ',
        "zh-CN": '代理网关 · ',
    },
    'probeEvidence-10': {
        "en": 'Redirect to ',
        "zh-CN": '跳转至 ',
    },
    'probeEvidence-11': {
        "en": 'Hop ',
        "zh-CN": '第 ',
    },
    'probeEvidence-12': {
        "en": '',
        "zh-CN": ' 跳',
    },
    'probeEvidence-13': {
        "en": ' (retry)',
        "zh-CN": '（重试）',
    },
    'probeEvidence-14': {
        "en": 'Gateway TCP ',
        "zh-CN": '网关 TCP ',
    },
    'probeEvidence-15': {
        "en": 'connected',
        "zh-CN": '已连接',
    },
    'probeEvidence-16': {
        "en": 'not connected',
        "zh-CN": '未连接',
    },
    'probeEvidence-17': {
        "en": 'First hop HTTP ',
        "zh-CN": '首跳 HTTP ',
    },
    'probeEvidence-18': {
        "en": 'First hop status unknown',
        "zh-CN": '首跳状态未知',
    },
    'probeEvidence-19': {
        "en": 'No final HTTP status received',
        "zh-CN": '未收到最终 HTTP 状态',
    },
    'probeEvidence-2': {
        "en": 'Request · ',
        "zh-CN": '请求 · ',
    },
    'probeEvidence-20': {
        "en": 'Final HTTP ',
        "zh-CN": '最终 HTTP ',
    },
    'probeEvidence-21': {
        "en": 'Reconnected once after a TLS handshake EOF',
        "zh-CN": 'TLS 握手 EOF 后已重连一次',
    },
    'probeEvidence-22': {
        "en": 'Last attempt · ',
        "zh-CN": '最后尝试 · ',
    },
    'probeEvidence-23': {
        "en": 'took ',
        "zh-CN": '耗时 ',
    },
    'probeEvidence-24': {
        "en": ' · whole-request budget ',
        "zh-CN": ' · 整次请求预算 ',
    },
    'probeEvidence-25': {
        "en": ' s',
        "zh-CN": ' 秒',
    },
    'probeEvidence-26': {
        "en": 'The time budget for the whole request ran out',
        "zh-CN": '整次请求的时间预算已用完',
    },
    'probeEvidence-27': {
        "en": 'The account login and its permissions were not verified',
        "zh-CN": '账户登录与权限未验证',
    },
    'probeEvidence-3': {
        "en": 'TLS verified',
        "zh-CN": 'TLS 已验证',
    },
    'probeEvidence-4': {
        "en": 'TLS handshake EOF',
        "zh-CN": 'TLS 握手 EOF',
    },
    'probeEvidence-5': {
        "en": 'TLS handshake timed out',
        "zh-CN": 'TLS 握手超时',
    },
    'probeEvidence-6': {
        "en": 'TLS certificate verification failed',
        "zh-CN": 'TLS 证书验证失败',
    },
    'probeEvidence-7': {
        "en": 'TLS handshake failed',
        "zh-CN": 'TLS 握手失败',
    },
    'probeEvidence-8': {
        "en": 'Gateway TCP connected',
        "zh-CN": '网关 TCP 已连接',
    },
    'probeEvidence-9': {
        "en": 'Gateway TCP not connected',
        "zh-CN": '网关 TCP 未连接',
    },
    'quick-target-label': {
        "en": 'Quick target',
        "zh-CN": '快捷目标',
    },
    'readonly-node-label': {
        "en": 'Nodes bound to this gateway',
        "zh-CN": '已绑定此网关的节点',
    },
    'refreshTargetOptions': {
        "en": 'Custom URL',
        "zh-CN": '自定义 URL',
    },
    'renderAll': {
        "en": 'Add a gateway',
        "zh-CN": '新增网关',
    },
    'renderAll-2': {
        "en": 'Edit ',
        "zh-CN": '编辑 ',
    },
    'renderAll-3': {
        "en": 'The default gateway of the current configuration',
        "zh-CN": '当前配置的默认网关',
    },
    'renderAll-4': {
        "en": 'Gateway: {gwStr}',
        "zh-CN": '网关: {gwStr}',
    },
    'renderClientsTable': {
        "en": 'Enable the {length} nodes shown? Every node must have its own saved gateway binding.',
        "zh-CN": '开启当前显示的 {length} 个节点？每个节点必须保存自己的网关绑定。',
    },
    'renderClientsTable-10': {
        "en": 'The shutdown failed: ',
        "zh-CN": '切断异常: ',
    },
    'renderClientsTable-11': {
        "en": '<span class="btn-icon">🛑</span> Restore the shown nodes',
        "zh-CN": '<span class="btn-icon">🛑</span> 恢复当前列表',
    },
    'renderClientsTable-12': {
        "en": 'Checking…',
        "zh-CN": '巡检中…',
    },
    'renderClientsTable-13': {
        "en": 'Target · ',
        "zh-CN": '目标 · ',
    },
    'renderClientsTable-14': {
        "en": '/2 HTTP requests succeeded',
        "zh-CN": '/2 路 HTTP 成功',
    },
    'renderClientsTable-15': {
        "en": 'The check failed: ',
        "zh-CN": '巡检异常：',
    },
    'renderClientsTable-16': {
        "en": 'Check every node',
        "zh-CN": '全网巡检',
    },
    'renderClientsTable-2': {
        "en": '<span class="btn-icon">⏳</span> Applying to the selection…',
        "zh-CN": '<span class="btn-icon">⏳</span> 正在批量下发...',
    },
    'renderClientsTable-3': {
        "en": 'The action did not complete',
        "zh-CN": '操作未完成',
    },
    'renderClientsTable-4': {
        "en": 'The batch failed: ',
        "zh-CN": '批量下发异常: ',
    },
    'renderClientsTable-5': {
        "en": '<span class="btn-icon">⚡</span> Enable the shown nodes',
        "zh-CN": '<span class="btn-icon">⚡</span> 开启当前列表',
    },
    'renderClientsTable-6': {
        "en": 'Restore the baseline of the {length} shown nodes from before the enabling? A proxy that already existed may still apply; a node that fails keeps its record.',
        "zh-CN": '恢复当前显示的 {length} 个节点的启用前基线？原有代理可能继续生效；失败节点会保留登记。',
    },
    'renderClientsTable-7': {
        "en": '<span class="btn-icon">⏳</span> Restoring node by node…',
        "zh-CN": '<span class="btn-icon">⏳</span> 正在逐节点恢复...',
    },
    'renderClientsTable-8': {
        "en": 'not restored',
        "zh-CN": '未恢复',
    },
    'renderClientsTable-9': {
        "en": 'Check the restoration result of each node',
        "zh-CN": '请查看各节点的恢复结果',
    },
    'renderClientsTableRows': {
        "en": '<tr><td colspan="5" style="text-align:center; color:var(--text-dim); padding: 24px;">No worker node matches the filter</td></tr>',
        "zh-CN": '<tr><td colspan="5" style="text-align:center; color:var(--text-dim); padding: 24px;">未匹配到符合条件的业务节点</td></tr>',
    },
    'renderClientsTableRows-10': {
        "en": '<span class="addr-badge" style="background:rgba(234,179,8,0.15);color:#facc15;">Docker host</span>',
        "zh-CN": '<span class="addr-badge" style="background:rgba(234,179,8,0.15);color:#facc15;">Docker穿透</span>',
    },
    'renderClientsTableRows-11': {
        "en": '<span class="addr-badge" style="background:rgba(6,182,212,0.15);color:#22d3ee;">Container with a mapped port (:{port})</span>',
        "zh-CN": '<span class="addr-badge" style="background:rgba(6,182,212,0.15);color:#22d3ee;">端口映射容器 (:{port})</span>',
    },
    'renderClientsTableRows-12': {
        "en": 'HTTP proxy :{port}',
        "zh-CN": 'HTTP 代理 :{port}',
    },
    'renderClientsTableRows-13': {
        "en": ' · confirm the execution place',
        "zh-CN": ' · 请确认执行位置',
    },
    'renderClientsTableRows-14': {
        "en": 'Send a request',
        "zh-CN": '发送业务请求',
    },
    'renderClientsTableRows-15': {
        "en": 'Stop the managed state',
        "zh-CN": '停止托管',
    },
    'renderClientsTableRows-16': {
        "en": '⚡ Enable',
        "zh-CN": '⚡ 开启',
    },
    'renderClientsTableRows-17': {
        "en": 'Target of this node probe',
        "zh-CN": '此节点探测目标',
    },
    'renderClientsTableRows-18': {
        "en": 'Custom URL of this node',
        "zh-CN": '此节点自定义 URL',
    },
    'renderClientsTableRows-19': {
        "en": 'Measure the latency and the reachability',
        "zh-CN": '实测出海延迟与连通状态',
    },
    'renderClientsTableRows-2': {
        "en": 'Not bound (cannot be enabled)',
        "zh-CN": '未绑定（禁止开启）',
    },
    'renderClientsTableRows-20': {
        "en": 'More operations',
        "zh-CN": '更多运维操作',
    },
    'renderClientsTableRows-21': {
        "en": '<button class="dropdown-item" data-action="restore-client" data-id="{id_}" data-action-type="off">↩ Restore the baseline from before the enabling</button>',
        "zh-CN": '<button class="dropdown-item" data-action="restore-client" data-id="{id_}" data-action-type="off">↩ 恢复启用前基线</button>',
    },
    'renderClientsTableRows-22': {
        "en": 'HTTP succeeded',
        "zh-CN": 'HTTP 成功',
    },
    'renderClientsTableRows-23': {
        "en": 'See the result',
        "zh-CN": '查看结果',
    },
    'renderClientsTableRows-24': {
        "en": 'Restore the baseline of {name} from before the enabling? A proxy that already existed may still apply.',
        "zh-CN": '恢复 {name} 的启用前基线？原有代理可能继续生效。',
    },
    'renderClientsTableRows-25': {
        "en": 'The switch failed: ',
        "zh-CN": '切换失败: ',
    },
    'renderClientsTableRows-26': {
        "en": 'The switch failed: ',
        "zh-CN": '切换异常: ',
    },
    'renderClientsTableRows-27': {
        "en": 'Checking',
        "zh-CN": '检测中',
    },
    'renderClientsTableRows-28': {
        "en": 'HTTP succeeded',
        "zh-CN": 'HTTP 成功',
    },
    'renderClientsTableRows-29': {
        "en": 'See the result',
        "zh-CN": '查看结果',
    },
    'renderClientsTableRows-3': {
        "en": 'Verified as enabled',
        "zh-CN": '已核验开启',
    },
    'renderClientsTableRows-30': {
        "en": 'The request failed',
        "zh-CN": '请求失败',
    },
    'renderClientsTableRows-31': {
        "en": 'The removal did not complete, the record is kept: ',
        "zh-CN": '删除未完成，登记保留: ',
    },
    'renderClientsTableRows-32': {
        "en": 'The removal failed: ',
        "zh-CN": '删除异常: ',
    },
    'renderClientsTableRows-33': {
        "en": '🟢 The host answers ({host}:{port}), it took {latency_ms} ms',
        "zh-CN": '🟢 主机连通正常 ({host}:{port})，耗时: {latency_ms} ms',
    },
    'renderClientsTableRows-34': {
        "en": '⚠️ The reachability pre-check of the host did not pass ({host}:{port})',
        "zh-CN": '⚠️ 主机网络可达性预检未通过 ({host}:{port})',
    },
    'renderClientsTableRows-35': {
        "en": 'The probe failed: ',
        "zh-CN": '探测异常: ',
    },
    'renderClientsTableRows-36': {
        "en": '⚡ Connectivity check',
        "zh-CN": '⚡ 连通探测',
    },
    'renderClientsTableRows-4': {
        "en": 'Verified as restored',
        "zh-CN": '已核验恢复',
    },
    'renderClientsTableRows-5': {
        "en": 'Not verified',
        "zh-CN": '未核验',
    },
    'renderClientsTableRows-6': {
        "en": 'Not verified',
        "zh-CN": '未核验',
    },
    'renderClientsTableRows-7': {
        "en": '<span class="addr-badge">Direct SSH</span>',
        "zh-CN": '<span class="addr-badge">SSH直连</span>',
    },
    'renderClientsTableRows-8': {
        "en": '<span class="addr-badge" style="background:rgba(168,85,247,0.15);color:#c084fc;">This console</span>',
        "zh-CN": '<span class="addr-badge" style="background:rgba(168,85,247,0.15);color:#c084fc;">本机控制台</span>',
    },
    'renderClientsTableRows-9': {
        "en": '<code>127.0.0.1 (local execution)</code>',
        "zh-CN": '<code>127.0.0.1 (本机执行)</code>',
    },
    'renderGatewaysTable': {
        "en": '<span class="t-pill success">Default gateway</span>',
        "zh-CN": '<span class="t-pill success">默认网关</span>',
    },
    'renderGatewaysTable-10': {
        "en": 'Could not save it: ',
        "zh-CN": '保存失败: ',
    },
    'renderGatewaysTable-11': {
        "en": 'The local mode uses the account that runs the console; the SSH identity is not used for a local command.',
        "zh-CN": '本机模式使用运行控制台的账号；SSH 身份不会用于本机命令。',
    },
    'renderGatewaysTable-12': {
        "en": 'For example: 6600 (a mapped SSH port of a container)',
        "zh-CN": '例如: 6600 (容器映射 SSH 端口)',
    },
    'renderGatewaysTable-13': {
        "en": '💡 Fill in the mapped port when the container runs an SSH service; choose the Docker host mode when you manage it through the host.',
        "zh-CN": '💡 容器有 SSH 服务时填写映射端口；通过宿主机管理时请选择 Docker 穿透模式。',
    },
    'renderGatewaysTable-14': {
        "en": 'The standard SSH port 22',
        "zh-CN": '标准 SSH 端口 22',
    },
    'renderGatewaysTable-2': {
        "en": '<span style="color:var(--text-dim)">Standby</span>',
        "zh-CN": '<span style="color:var(--text-dim)">备用</span>',
    },
    'renderGatewaysTable-3': {
        "en": '<button class="btn-mini" data-action="set-default-gw" data-id="{id_}">Set as default</button>',
        "zh-CN": '<button class="btn-mini" data-action="set-default-gw" data-id="{id_}">设为默认</button>',
    },
    'renderGatewaysTable-4': {
        "en": '<button class="btn-mini btn-danger" data-action="delete-gw" data-id="{id_}">🗑️ Delete</button>',
        "zh-CN": '<button class="btn-mini btn-danger" data-action="delete-gw" data-id="{id_}">🗑️ 删除</button>',
    },
    'renderGatewaysTable-5': {
        "en": 'The probe failed: ',
        "zh-CN": '探测异常: ',
    },
    'renderGatewaysTable-6': {
        "en": '⚡ Test',
        "zh-CN": '⚡ 测通',
    },
    'renderGatewaysTable-7': {
        "en": 'Delete the gateway {gid}?',
        "zh-CN": '确定要删除网关【{gid}】吗？',
    },
    'renderGatewaysTable-8': {
        "en": 'The gateway could not be deleted: ',
        "zh-CN": '删除网关失败: ',
    },
    'renderGatewaysTable-9': {
        "en": '✅ The bypass list is saved',
        "zh-CN": '✅ 直连白名单已保存',
    },
    'renderHandoverBlocks': {
        "en": 'Send a request on this machine',
        "zh-CN": '在本机发送业务请求',
    },
    'renderHandoverBlocks-10': {
        "en": 'After the node proxy is enabled, verify it on the target workstation or container',
        "zh-CN": '开启节点代理后，在目标工作站或容器内验证',
    },
    'renderHandoverBlocks-11': {
        "en": '<div class="code-delivery-header"><span class="code-delivery-title"></span><button class="btn-copy">Copy the code</button></div><pre><code></code></pre>',
        "zh-CN": '<div class="code-delivery-header"><span class="code-delivery-title"></span><button class="btn-copy">复制代码</button></div><pre><code></code></pre>',
    },
    'renderHandoverBlocks-2': {
        "en": 'Enable the node proxy',
        "zh-CN": '开启节点代理',
    },
    'renderHandoverBlocks-3': {
        "en": 'Target IP: {host} | Container: {container_name_____app_container_}',
        "zh-CN": '目标 IP: {host} | 容器名: {container_name_____app_container_}',
    },
    'renderHandoverBlocks-4': {
        "en": 'Target IP: {host} | Bound gateway: {host_2}:{port}',
        "zh-CN": '目标 IP: {host} | 绑定网关: {host_2}:{port}',
    },
    'renderHandoverBlocks-5': {
        "en": 'One request',
        "zh-CN": '单次请求',
    },
    'renderHandoverBlocks-6': {
        "en": 'The binding changed; enable it again to apply it',
        "zh-CN": '已更换绑定，需重新开启以应用',
    },
    'renderHandoverBlocks-7': {
        "en": 'Managed record · enabled',
        "zh-CN": '托管记录 · 已开启',
    },
    'renderHandoverBlocks-8': {
        "en": 'Managed record · disabled',
        "zh-CN": '托管记录 · 已关闭',
    },
    'renderHandoverBlocks-9': {
        "en": 'Run one proxied request in the Windows tools directory',
        "zh-CN": '在 Windows 工具目录中运行单次代理请求',
    },
    'renderLocalGatewayState': {
        "en": 'The local observation gateway is running at ',
        "zh-CN": '本机观测网关已启动：',
    },
    'renderProbe': {
        "en": 'See the evidence of every hop',
        "zh-CN": '查看逐跳证据',
    },
    'renderSandboxSelectors': {
        "en": 'Use the default gateway',
        "zh-CN": '使用默认网关',
    },
    'renderWizardSelectors': {
        "en": ' [default]',
        "zh-CN": ' [默认]',
    },
    'request-target-label': {
        "en": 'Request target',
        "zh-CN": '请求目标',
    },
    'resetBusinessMetrics': {
        "en": 'Not configured',
        "zh-CN": '尚未配置',
    },
    'resetBusinessMetrics-2': {
        "en": 'Save a gateway in the wizard first',
        "zh-CN": '请在接入向导保存网关',
    },
    'resetBusinessMetrics-3': {
        "en": 'Not checked',
        "zh-CN": '尚未检测',
    },
    'resetBusinessMetrics-4': {
        "en": 'Send a request or refresh the connectivity',
        "zh-CN": '可发送请求或刷新连通性',
    },
    'resetBusinessMetrics-5': {
        "en": 'Waiting for a request.',
        "zh-CN": '等待发送请求。',
    },
    'resetBusinessMetrics-6': {
        "en": 'Ready',
        "zh-CN": '就绪',
    },
    'resetWizard': {
        "en": 'Probe this gateway for connectivity',
        "zh-CN": '探测该网关连通性',
    },
    'resetWizard-2': {
        "en": 'Verify the proxy gateway',
        "zh-CN": '校验代理网关',
    },
    'resetWizard-3': {
        "en": 'To verify',
        "zh-CN": '待验证',
    },
    'resetWizard-4': {
        "en": 'Continue after the selected gateway is verified.',
        "zh-CN": '验证所选网关后可继续。',
    },
    'resetWizard-5': {
        "en": 'Waiting for a saved binding',
        "zh-CN": '等待保存绑定',
    },
    'resetWizard-6': {
        "en": 'Waiting for the verification',
        "zh-CN": '等待验证',
    },
    'resetWizard-7': {
        "en": 'Waiting for the hand-over',
        "zh-CN": '等待交付',
    },
    'resetWizard-8': {
        "en": 'Not selected',
        "zh-CN": '未选择',
    },
    'restoredEnvironmentNote': {
        "en": 'The original login environment',
        "zh-CN": '原登录环境',
    },
    'restoredEnvironmentNote-2': {
        "en": 'The current independent login environment',
        "zh-CN": '当前独立登录环境',
    },
    'restoredEnvironmentNote-3': {
        "en": '{context} still has a proxy · {port_} (it matches a known gateway)',
        "zh-CN": '{context}仍有代理 · {port_}（与已知网关吻合）',
    },
    'restoredEnvironmentNote-4': {
        "en": '{context} still has a proxy (another source, the address is not shown)',
        "zh-CN": '{context}仍有代理（其他来源，地址未回显）',
    },
    'restoredEnvironmentNote-5': {
        "en": '{context} shows no proxy variables (this does not mean that every application connects directly)',
        "zh-CN": '{context}未检测到代理变量（不代表所有应用直连）',
    },
    'runWizardAction': {
        "en": 'Running',
        "zh-CN": '执行中',
    },
    'runWizardAction-2': {
        "en": ' · request result',
        "zh-CN": ' · 请求结果',
    },
    'runWizardAction-3': {
        "en": 'The action did not complete',
        "zh-CN": '操作未完成',
    },
    'sb-active-gw-sub': {
        "en": 'Save a gateway in the wizard first',
        "zh-CN": '请在接入向导保存网关',
    },
    'sb-active-gw-sub-m-label': {
        "en": 'Gateway TCP connection',
        "zh-CN": '网关 TCP 连接',
    },
    'sb-active-gw-val': {
        "en": 'Not configured',
        "zh-CN": '尚未配置',
    },
    'sb-clear-term-btn': {
        "en": 'Clear',
        "zh-CN": '清屏',
    },
    'sb-clear-term-btn-t-dim': {
        "en": 'Choose a gateway and enter a target address to send a request.',
        "zh-CN": '选择网关并输入目标地址后发送请求。',
    },
    'sb-cmd-input-label': {
        "en": 'Common requests:',
        "zh-CN": '常用请求:',
    },
    'sb-diag-rate-val': {
        "en": 'Not checked',
        "zh-CN": '尚未检测',
    },
    'sb-diag-summary': {
        "en": 'Use refresh to check the target response',
        "zh-CN": '点击刷新检查目标响应',
    },
    'sb-diag-summary-h2': {
        "en": 'Send an HTTP request from the console host',
        "zh-CN": '从控制台主机发送 HTTP 请求',
    },
    'sb-diag-summary-tag': {
        "en": 'Enter an HTTP or HTTPS address. The request leaves through the selected gateway; use the CLI for other commands.',
        "zh-CN": '输入 HTTP 或 HTTPS 地址。请求经过所选网关发出；运行其他命令请使用 CLI。',
    },
    'sb-gw-rtt-sub': {
        "en": 'Use Refresh connectivity below',
        "zh-CN": '点击下方「刷新连通性」',
    },
    'sb-gw-rtt-sub-m-label': {
        "en": 'Target HTTP request',
        "zh-CN": '目标 HTTP 请求',
    },
    'sb-gw-status-val': {
        "en": 'Not checked',
        "zh-CN": '尚未检测',
    },
    'sb-run-btn-terminal-title': {
        "en": 'Request result',
        "zh-CN": '请求结果',
    },
    'sb-status-badge': {
        "en": 'Idle and ready',
        "zh-CN": '空闲就绪',
    },
    'sb-template-select-label': {
        "en": 'Gateway to use:',
        "zh-CN": '指定网关出海:',
    },
    'section-access-docker-host-label': {
        "en": 'Container name inside Docker *:',
        "zh-CN": 'Docker 容器内部名称 *:',
    },
    'section-access-ssh-label': {
        "en": 'Host IP or internal name *:',
        "zh-CN": '主机 IP 或内网域名 *:',
    },
    'selectSetupGateway': {
        "en": 'Local proxy',
        "zh-CN": '本机代理',
    },
    'selectSetupGateway-2': {
        "en": 'Save the changes to this gateway',
        "zh-CN": '保存对此网关的修改',
    },
    'selectSetupGateway-3': {
        "en": 'Save a new gateway',
        "zh-CN": '保存新网关',
    },
    'setup-compare': {
        "en": 'Repeat the same GET with the system curl',
        "zh-CN": '用系统 curl 复测同一 GET',
    },
    'setup-compare-summary': {
        "en": 'Configure a proxy for a remote machine or container',
        "zh-CN": '为远程机器或容器配置代理',
    },
    'setup-controls-option': {
        "en": 'Add a gateway',
        "zh-CN": '新增网关',
    },
    'setup-default': {
        "en": 'Set as the default gateway',
        "zh-CN": '设为默认网关',
    },
    'setup-host-label': {
        "en": 'Proxy address',
        "zh-CN": '代理地址',
    },
    'setup-name-label': {
        "en": 'Gateway name',
        "zh-CN": '网关名称',
    },
    'setup-port-label': {
        "en": 'Port',
        "zh-CN": '端口',
    },
    'setup-reload': {
        "en": 'Read the configuration again',
        "zh-CN": '重新读取配置',
    },
    'setup-result': {
        "en": 'Reading the gateway configuration…',
        "zh-CN": '正在读取网关配置…',
    },
    'setup-save': {
        "en": 'Save the gateway',
        "zh-CN": '保存新网关',
    },
    'setup-selection-label': {
        "en": 'Action',
        "zh-CN": '选择操作',
    },
    'setup-test': {
        "en": 'Send a proxy request',
        "zh-CN": '发送代理请求',
    },
    'setup-title': {
        "en": 'Connect your HTTP proxy',
        "zh-CN": '连接你的 HTTP 代理',
    },
    'setup-title-p': {
        "en": 'Enter the host and HTTP or mixed port of a proxy that is already running. The console sends the requests from the machine it runs on, so use 127.0.0.1 for a proxy on the same machine.',
        "zh-CN": '填写已运行的 HTTP 或 mixed 代理监听地址。控制台从运行它的机器发送请求，本机代理请填写 127.0.0.1。',
    },
    'showBusinessMetrics': {
        "en": 'No result yet',
        "zh-CN": '尚无结果',
    },
    'showBusinessMetrics-10': {
        "en": 'The request did not complete',
        "zh-CN": '请求未完成',
    },
    'showBusinessMetrics-2': {
        "en": 'connected',
        "zh-CN": '已连接',
    },
    'showBusinessMetrics-3': {
        "en": 'the connection failed',
        "zh-CN": '连接失败',
    },
    'showBusinessMetrics-4': {
        "en": 'no final response received',
        "zh-CN": '未收到最终响应',
    },
    'showBusinessMetrics-5': {
        "en": 'Save a gateway in the wizard first.',
        "zh-CN": '请在接入向导保存网关。',
    },
    'showBusinessMetrics-6': {
        "en": 'Requesting',
        "zh-CN": '请求中',
    },
    'showBusinessMetrics-7': {
        "en": 'No result for the request. Refresh and try again.',
        "zh-CN": '未收到请求结果，请刷新后重试。',
    },
    'showBusinessMetrics-8': {
        "en": 'The request succeeded',
        "zh-CN": '请求成功',
    },
    'showBusinessMetrics-9': {
        "en": 'The request did not succeed',
        "zh-CN": '请求未成功',
    },
    'showNodeResult': {
        "en": ' · internet test',
        "zh-CN": ' · 外网测试',
    },
    'status-tag-step-1': {
        "en": '● Waiting for a probe',
        "zh-CN": '● 等待探测',
    },
    'status-tag-step-1-label': {
        "en": 'Choose the outbound proxy gateway:',
        "zh-CN": '选择出网代理网关:',
    },
    'status-tag-step-2': {
        "en": '🔒 Locked',
        "zh-CN": '🔒 待解锁',
    },
    'status-tag-step-2-label': {
        "en": 'Choose the worker node:',
        "zh-CN": '选择目标业务节点:',
    },
    'status-tag-step-3': {
        "en": '🔒 Locked',
        "zh-CN": '🔒 待解锁',
    },
    'status-tag-step-4': {
        "en": '🎯 Ready to hand over',
        "zh-CN": '🎯 待交付',
    },
    'status-tag-step-4-h4': {
        "en": 'Confirm the target and the gateway before the configuration is applied.',
        "zh-CN": '请确认目标和网关，再下发代理配置。',
    },
    'step-1-result-res-msg': {
        "en": 'Click Probe to check whether the gateway port and service answer. Step 2 unlocks once the check succeeds.',
        "zh-CN": '点击【探测连通性】以验证网关端口与服务是否可用。验证成功后将自动解锁步骤 2。',
    },
    'tab-handbook-a': {
        "en": 'Project home',
        "zh-CN": '项目主页',
    },
    'tab-handbook-a-2': {
        "en": 'First run guide',
        "zh-CN": '首次使用指南',
    },
    'tab-handbook-a-3': {
        "en": 'Remote access and restoration',
        "zh-CN": '远程接入与配置恢复',
    },
    'tab-handbook-btn-copy': {
        "en": 'Copy the command',
        "zh-CN": '复制命令',
    },
    'tab-handbook-card-subdesc': {
        "en": 'First save an existing HTTP or mixed proxy gateway in the wizard and click Send a proxy request. After an HTTP 2xx, choose one of the usages below.',
        "zh-CN": '先在「接入向导」保存已有的 HTTP 或混合代理网关，点击「发送代理请求」。收到 HTTP 2xx 后，可按需要选择以下用法。',
    },
    'tab-handbook-h2': {
        "en": 'Developer handbook',
        "zh-CN": '开发者手册',
    },
    'tab-handbook-p': {
        "en": 'Open PowerShell in the extracted folder of the portable archive. The script uses the bundled Python and sets the proxy for this one curl command.',
        "zh-CN": '在便携包的解压目录打开 PowerShell。脚本使用包内 Python，为这一条 curl 命令设置代理。',
    },
    'tab-handbook-strong': {
        "en": 'One command on Windows',
        "zh-CN": 'Windows 单次命令',
    },
    'tab-sandbox-m-label': {
        "en": 'Gateway for this request',
        "zh-CN": '本次请求的网关',
    },
    'tab-topology-card-subdesc': {
        "en": 'Manage every compute device, controller and edge node of the team, with adding, editing, removing and a reachability pre-check',
        "zh-CN": '纳管团队的所有计算设备、工控机与边缘节点，支持动态增加、编辑、删除与连通预检',
    },
    'tab-topology-h2': {
        "en": '🤖 Worker node pool',
        "zh-CN": '🤖 目标业务节点池 (Worker Nodes Pool)',
    },
    'title': {
        "en": 'Net-Proxy-Tool — cross-platform console for LAN proxying and Docker network isolation (v1.5.0)',
        "zh-CN": 'Net-Proxy-Tool 通用跨平台局域网出海与 Docker 容器隔离控制中心 (v1.5.0)',
    },
    'top-clients-tbody-card-subdesc': {
        "en": 'Manage every proxy gateway, set the default gateway, test connectivity and assign gateways to many nodes',
        "zh-CN": '管理所有可用的代理网关服务器，支持自由设置默认网关、测试连通性与多对多分配',
    },
    'top-clients-tbody-h2': {
        "en": '🖥️ Gateway pool',
        "zh-CN": '🖥️ 代理工作站网关池 (Gateway Pool)',
    },
    'top-gateways-tbody-card-subdesc': {
        "en": 'Tools that honour NO_PROXY bypass the proxy for the entries in this list. Wildcards and CIDR ranges depend on the tool.',
        "zh-CN": '接受 NO_PROXY 的工具会按此列表绕过代理。域名通配和 CIDR 的支持取决于具体工具。',
    },
    'top-gateways-tbody-h2': {
        "en": '🛡️ LAN bypass list (NO_PROXY)',
        "zh-CN": '🛡️ 局域网直连白名单规则 (NO_PROXY)',
    },
    'unlockStep2': {
        "en": '● Binding to confirm',
        "zh-CN": '● 待确认绑定',
    },
    'unlockStep2-2': {
        "en": 'The service did not confirm the node binding. Load the page again.',
        "zh-CN": '服务未确认节点绑定，请重新加载。',
    },
    'unlockStep2-3': {
        "en": 'The node binding has changed. Confirm it again.',
        "zh-CN": '节点绑定已变化，请重新确认。',
    },
    'unlockStep2-4': {
        "en": 'Saved: ',
        "zh-CN": '已保存：',
    },
    'unlockStep3': {
        "en": '● Waiting for the diagnostic',
        "zh-CN": '● 等待体检',
    },
    'unlockStep4': {
        "en": '<span class="pipe-num">✓</span><span class="pipe-name">Ready to use</span>',
        "zh-CN": '<span class="pipe-num">✓</span><span class="pipe-name">开箱即用</span>',
    },
    'unlockStep4-2': {
        "en": '🎯 Hand-over complete',
        "zh-CN": '🎯 交付完成',
    },
    'unlockStep4-3': {
        "en": '🟢 Managed record · enabled',
        "zh-CN": '🟢 托管记录 · 已开启',
    },
    'unlockStep4-4': {
        "en": '⚪ Managed record · disabled',
        "zh-CN": '⚪ 托管记录 · 已关闭',
    },
    'updateNodeStatsBadge': {
        "en": '{total} nodes ({onCount} verified as enabled, {offCount} verified as restored, {total___onCount___offCount} not verified)',
        "zh-CN": '共 {total} 个节点 ({onCount} 已核验开启, {offCount} 已核验恢复, {total___onCount___offCount} 未核验)',
    },
    'updateWizardClientMeta': {
        "en": 'Not specified',
        "zh-CN": '未指定',
    },
    'updateWizardClientMeta-10': {
        "en": 'Test the same GET again',
        "zh-CN": '重新测试同一 GET',
    },
    'updateWizardClientMeta-11': {
        "en": 'Sending a read-only request from ',
        "zh-CN": '正在从 ',
    },
    'updateWizardClientMeta-12': {
        "en": ' …',
        "zh-CN": ' 发送只读请求…',
    },
    'updateWizardClientMeta-13': {
        "en": '{name} is now the global default gateway.',
        "zh-CN": '已成功将【{name}】设为全局默认网关！',
    },
    'updateWizardClientMeta-14': {
        "en": 'Could not set it: ',
        "zh-CN": '设置失败: ',
    },
    'updateWizardClientMeta-2': {
        "en": 'none',
        "zh-CN": '无',
    },
    'updateWizardClientMeta-3': {
        "en": '<span class="btn-icon">⏳</span> Probing the gateway…',
        "zh-CN": '<span class="btn-icon">⏳</span> 正在探测网关...',
    },
    'updateWizardClientMeta-4': {
        "en": 'Sending a GET request through the selected gateway…',
        "zh-CN": '正在通过所选网关发送 GET 请求…',
    },
    'updateWizardClientMeta-5': {
        "en": 'No bound node yet',
        "zh-CN": '暂无已绑定节点',
    },
    'updateWizardClientMeta-6': {
        "en": '✅ Ready',
        "zh-CN": '✅ 已就绪',
    },
    'updateWizardClientMeta-7': {
        "en": '<span class="pipe-num">✓</span><span class="pipe-name">The gateway is ready</span>',
        "zh-CN": '<span class="pipe-num">✓</span><span class="pipe-name">网关已就绪</span>',
    },
    'updateWizardClientMeta-8': {
        "en": 'The target request did not succeed',
        "zh-CN": '目标请求未成功',
    },
    'updateWizardClientMeta-9': {
        "en": 'Request error: ',
        "zh-CN": '请求异常：',
    },
    'w-meta-gw-meta-label': {
        "en": 'Tags:',
        "zh-CN": '业务标签:',
    },
    'w-meta-host-meta-label': {
        "en": 'Operating system:',
        "zh-CN": '系统架构:',
    },
    'w-meta-os-meta-label': {
        "en": 'Bound gateway:',
        "zh-CN": '绑定路由:',
    },
    'wizard-client-meta-meta-label': {
        "en": 'Node IP:',
        "zh-CN": '节点 IP:',
    },
    'wizard-compare': {
        "en": 'Repeat the same GET with the system curl',
        "zh-CN": '用系统 curl 复测同一 GET',
    },
    'wizard-compare-summary': {
        "en": 'Terminal GET command',
        "zh-CN": '终端 GET 命令',
    },
    'wizard-diag-time': {
        "en": 'Not diagnosed',
        "zh-CN": '未诊断',
    },
    'wizard-feedback-badge': {
        "en": 'Checking…',
        "zh-CN": '检测中...',
    },
    'wizard-feedback-content-li': {
        "en": 'After it is enabled, curl, wget, pip and Git in the target account can read their own proxy settings. Programs that depend on shell variables should be checked in a new terminal.',
        "zh-CN": '开启后，目标账号的 curl、wget、pip 和 Git 可读取各自的代理设置。依赖 shell 环境变量的程序请在新终端中验证。',
    },
    'wizard-feedback-content-li-2': {
        "en": 'When the managed state stops, the tool restores the configuration from the snapshot taken before it was enabled. A proxy that already existed may still apply, so repeat the request with a plain curl to check the current path.',
        "zh-CN": '停止托管时，工具按快照恢复启用前的配置。原有代理可能继续生效，可用普通 curl 复测当前路径。',
    },
    'wizard-feedback-content-li-3': {
        "en": 'The container mode runs the configuration script inside the selected container. Running it as root can change system-wide settings on the target; when the restoration conflicts, check the files on the target.',
        "zh-CN": '容器模式在所选容器内执行配置脚本。以 root 运行时可能修改目标系统级配置，遇到恢复冲突时请核对目标文件。',
    },
    'wizard-feedback-content-reference-summary': {
        "en": '🛠️ Advanced commands and code reference (for advanced developers; not needed in daily use)',
        "zh-CN": '🛠️ 高级研发命令与代码参考 (仅供高级开发者查阅，日常使用无需手动执行)',
    },
    'wizard-feedback-content-strong': {
        "en": 'Scope and restoration',
        "zh-CN": '操作范围与恢复',
    },
    'wizard-probe-command-btn-copy': {
        "en": 'Copy the command',
        "zh-CN": '复制命令',
    },
    'wizard-readonly-test': {
        "en": 'Read-only diagnosis from the node',
        "zh-CN": '从节点只读诊断',
    },
    'wizard-switch-badge': {
        "en": '⚪ Managed proxy not enabled',
        "zh-CN": '⚪ 未启用托管代理',
    },
    'wizard-target-disp-name': {
        "en": 'Not selected',
        "zh-CN": '未选择',
    },
    'wizard-target-disp-sub': {
        "en": 'The account or the container appears here once you choose a target.',
        "zh-CN": '选择目标后将在此显示账号或容器。',
    },
    '⚠️ 容器探测异常: {e}': {
        "en": '⚠️ The container probe failed: {e}',
        "zh-CN": '⚠️ 容器探测异常: {e}',
    },
    '⚠️ 物理网络通畅{banner_info}，但{auth_msg}！': {
        "en": '⚠️ The physical network answers{banner_info}, but {auth_msg}!',
        "zh-CN": '⚠️ 物理网络通畅{banner_info}，但{auth_msg}！',
    },
    '❌ 宿主机网络不可达 ({ssh_host}:{port}): {rtt_or_err}': {
        "en": '❌ The Docker host is not reachable ({ssh_host}:{port}): {rtt_or_err}',
        "zh-CN": '❌ 宿主机网络不可达 ({ssh_host}:{port}): {rtt_or_err}',
    },
    '❌ 网络连接被拒绝 ({host}:{port}): 目标主机离线或端口未映射': {
        "en": '❌ The connection was refused ({host}:{port}): the target is offline or the port is not mapped',
        "zh-CN": '❌ 网络连接被拒绝 ({host}:{port}): 目标主机离线或端口未映射',
    },
    '❌ 请提供主机 IP': {
        "en": '❌ Give the host IP',
        "zh-CN": '❌ 请提供主机 IP',
    },
    '不能删除当前正处于激活状态的默认网关，请先切换默认网关': {
        "en": 'The active default gateway cannot be deleted; switch the default gateway first',
        "zh-CN": '不能删除当前正处于激活状态的默认网关，请先切换默认网关',
    },
    '二进制响应，未显示内容': {
        "en": 'Binary response, no content shown',
        "zh-CN": '二进制响应，未显示内容',
    },
    '仅接受 URL、GET/HEAD 和 -s / -S / -L 显示选项': {
        "en": 'Only a URL, GET or HEAD and the -s / -S / -L display options are accepted',
        "zh-CN": '仅接受 URL、GET/HEAD 和 -s / -S / -L 显示选项',
    },
    '仅支持 GET 或 HEAD 请求': {
        "en": 'Only GET or HEAD requests are supported',
        "zh-CN": '仅支持 GET 或 HEAD 请求',
    },
    '仍有节点绑定此网关，请先保存这些节点的新绑定。': {
        "en": 'Nodes are still bound to this gateway; save their new binding first.',
        "zh-CN": '仍有节点绑定此网关，请先保存这些节点的新绑定。',
    },
    '代理网关删除成功': {
        "en": 'The proxy gateway was deleted',
        "zh-CN": '代理网关删除成功',
    },
    '代理网关已存在': {
        "en": 'The proxy gateway already exists',
        "zh-CN": '代理网关已存在',
    },
    '代理网关更新成功': {
        "en": 'The proxy gateway was updated',
        "zh-CN": '代理网关更新成功',
    },
    '代理网关添加成功': {
        "en": 'The proxy gateway was added',
        "zh-CN": '代理网关添加成功',
    },
    '代理请求超过总超时': {
        "en": 'The proxy request exceeded the total timeout',
        "zh-CN": '代理请求超过总超时',
    },
    '停止': {
        "en": 'stop',
        "zh-CN": '停止',
    },
    "免密未生效: {res.stderr.strip() or 'Permission denied (publickey)'}": {
        "en": "The key authentication did not work: {res.stderr.strip() or 'Permission denied (publickey)'}",
        "zh-CN": "免密未生效: {res.stderr.strip() or 'Permission denied (publickey)'}",
    },
    "初始密码错误或被拒: {res.stderr.strip() or 'Permission denied'}": {
        "en": "The first password was wrong or refused: {res.stderr.strip() or 'Permission denied'}",
        "zh-CN": "初始密码错误或被拒: {res.stderr.strip() or 'Permission denied'}",
    },
    '原节点登记和可用绑定已恢复；认证资料使用本次输入。': {
        "en": 'The original registration and its usable binding are restored; the credentials come from this input.',
        "zh-CN": '原节点登记和可用绑定已恢复；认证资料使用本次输入。',
    },
    '原身份未确认恢复，节点身份没有修改。': {
        "en": 'The restoration of the original identity was not confirmed; the identity was not changed.',
        "zh-CN": '原身份未确认恢复，节点身份没有修改。',
    },
    '启动': {
        "en": 'start',
        "zh-CN": '启动',
    },
    '实际登录账号、UID、HOME 或 shell 已变化或无法核验；未执行配置写入，原基线保留。': {
        "en": 'The real login account, UID, HOME or shell changed or cannot be verified; no configuration was written and the baseline is kept.',
        "zh-CN": '实际登录账号、UID、HOME 或 shell 已变化或无法核验；未执行配置写入，原基线保留。',
    },
    '容器执行通道未就绪': {
        "en": 'The container execution channel is not ready',
        "zh-CN": '容器执行通道未就绪',
    },
    '密码认证成功，预检已完成': {
        "en": 'The password authentication succeeded and the pre-check is complete',
        "zh-CN": '密码认证成功，预检已完成',
    },
    '尚未绑定网关': {
        "en": 'No gateway is bound yet',
        "zh-CN": '尚未绑定网关',
    },
    '巡检完成，{passed}/{len(clients)} 个节点两路 HTTP 请求成功': {
        "en": 'The check is complete: {passed}/{len(clients)} nodes answered both HTTP requests',
        "zh-CN": '巡检完成，{passed}/{len(clients)} 个节点两路 HTTP 请求成功',
    },
    '巡检期间节点绑定已变化，请重新测试。': {
        "en": 'The node binding changed during the check; test again.',
        "zh-CN": '巡检期间节点绑定已变化，请重新测试。',
    },
    '已保存的恢复基线缺少执行身份；未执行配置写入，登记保留。': {
        "en": 'The saved restoration baseline has no execution identity; no configuration was written and the record is kept.',
        "zh-CN": '已保存的恢复基线缺少执行身份；未执行配置写入，登记保留。',
    },
    '已保存的托管执行身份与当前目标不一致；未执行写入，请先恢复原身份。': {
        "en": 'The saved managed identity does not match the current target; nothing was written, restore the original identity first.',
        "zh-CN": '已保存的托管执行身份与当前目标不一致；未执行写入，请先恢复原身份。',
    },
    '已拒绝 HTTPS 降级到 HTTP': {
        "en": 'The downgrade from HTTPS to HTTP was refused',
        "zh-CN": '已拒绝 HTTPS 降级到 HTTP',
    },
    '已核对本机执行账号。': {
        "en": 'The local execution account was checked.',
        "zh-CN": '已核对本机执行账号。',
    },
    '已核验': {
        "en": 'verified',
        "zh-CN": '已核验',
    },
    '已核验完成 {}/{} 个明确选择节点的操作。': {
        "en": 'Verified {} of {} operations on the selected nodes.',
        "zh-CN": '已核验完成 {}/{} 个明确选择节点的操作。',
    },
    '已核验恢复启用前基线，原有代理仍可能生效。': {
        "en": 'The restoration to the baseline from before the enabling is verified; a proxy that already existed may still apply.',
        "zh-CN": '已核验恢复启用前基线，原有代理仍可能生效。',
    },
    '已核验托管配置开启。': {
        "en": 'The managed configuration is verified as enabled.',
        "zh-CN": '已核验托管配置开启。',
    },
    '开启前必须保存此节点的网关绑定。': {
        "en": 'The gateway binding of this node must be saved before it is enabled.',
        "zh-CN": '开启前必须保存此节点的网关绑定。',
    },
    '开启前必须选择并保存此节点的网关绑定。': {
        "en": 'The gateway binding of this node must be chosen and saved before it is enabled.',
        "zh-CN": '开启前必须选择并保存此节点的网关绑定。',
    },
    '开启前每个节点都必须保存网关绑定。': {
        "en": 'Every node must have a saved gateway binding before it is enabled.',
        "zh-CN": '开启前每个节点都必须保存网关绑定。',
    },
    '恢复未核验通过，节点登记和认证资料仍保留。': {
        "en": 'The restoration was not verified; the registration and the credentials are kept.',
        "zh-CN": '恢复未核验通过，节点登记和认证资料仍保留。',
    },
    '批量列表中的节点已移除，请刷新。': {
        "en": 'A node of the selection was removed; load the page again.',
        "zh-CN": '批量列表中的节点已移除，请刷新。',
    },
    '批量操作必须明确提交节点列表和各自版本。': {
        "en": 'A batch operation must name the nodes and their versions.',
        "zh-CN": '批量操作必须明确提交节点列表和各自版本。',
    },
    '批量节点列表包含无效或重复条目': {
        "en": 'The list of nodes holds an invalid or a repeated entry',
        "zh-CN": '批量节点列表包含无效或重复条目',
    },
    '指定网关请求：{}；节点普通请求：{}': {
        "en": 'Request through the selected gateway: {}; ordinary request of the node: {}',
        "zh-CN": '指定网关请求：{}；节点普通请求：{}',
    },
    '无响应': {
        "en": 'no response',
        "zh-CN": '无响应',
    },
    '无效的 Docker 容器名称': {
        "en": 'Invalid Docker container name',
        "zh-CN": '无效的 Docker 容器名称',
    },
    '无效的 IPv6 区域标识': {
        "en": 'Invalid IPv6 zone',
        "zh-CN": '无效的 IPv6 区域标识',
    },
    '无效的 SSH 用户名': {
        "en": 'Invalid SSH user name',
        "zh-CN": '无效的 SSH 用户名',
    },
    '无效的 SSH 认证类型': {
        "en": 'Invalid SSH authentication type',
        "zh-CN": '无效的 SSH 认证类型',
    },
    '无效的节点操作': {
        "en": 'Invalid node operation',
        "zh-CN": '无效的节点操作',
    },
    '无法完成节点操作或核验；未删除登记，恢复信息已保留。': {
        "en": 'The node operation or its verification could not be completed; the registration was not removed and the recovery information is kept.',
        "zh-CN": '无法完成节点操作或核验；未删除登记，恢复信息已保留。',
    },
    '无法执行节点探测': {
        "en": 'The node probe could not be run',
        "zh-CN": '无法执行节点探测',
    },
    '无法核对本机登录环境。': {
        "en": 'The local login environment could not be checked.',
        "zh-CN": '无法核对本机登录环境。',
    },
    '无法检查容器，请核对名称及远程账号的 Docker 权限': {
        "en": 'The container could not be inspected; check its name and the Docker permissions of the remote account',
        "zh-CN": '无法检查容器，请核对名称及远程账号的 Docker 权限',
    },
    '无法确认当前托管状态；未执行配置写入，原基线保留。': {
        "en": 'The current managed state cannot be confirmed; no configuration was written and the baseline is kept.',
        "zh-CN": '无法确认当前托管状态；未执行配置写入，原基线保留。',
    },
    '无法读取节点基线；尚未执行配置写入。': {
        "en": 'The node baseline cannot be read; no configuration was written yet.',
        "zh-CN": '无法读取节点基线；尚未执行配置写入。',
    },
    '旧节点曾按本机地址推断执行位置；请编辑节点并明确选择本机或 SSH，再进行写入。': {
        "en": 'The old node inferred its execution place from a local address; edit it, choose local or SSH explicitly and only then write.',
        "zh-CN": '旧节点曾按本机地址推断执行位置；请编辑节点并明确选择本机或 SSH，再进行写入。',
    },
    '旧配置没有可用恢复快照；请先核对基线。': {
        "en": 'The old configuration has no usable restoration snapshot; check the baseline first.',
        "zh-CN": '旧配置没有可用恢复快照；请先核对基线。',
    },
    "未找到ID为 '{gid}' 的网关": {
        "en": "No gateway with the id '{gid}' was found",
        "zh-CN": "未找到ID为 '{gid}' 的网关",
    },
    "未找到ID为 '{node_id}' 的节点": {
        "en": "No node with the id '{node_id}' was found",
        "zh-CN": "未找到ID为 '{node_id}' 的节点",
    },
    '未找到系统 curl，请使用首页的内置代理请求测试': {
        "en": 'No system curl was found; use the built-in proxy request test on the first page',
        "zh-CN": '未找到系统 curl，请使用首页的内置代理请求测试',
    },
    '未找到网关，请先在首页保存 HTTP 代理网关。': {
        "en": 'No gateway was found; save an HTTP proxy gateway on the first page.',
        "zh-CN": '未找到网关，请先在首页保存 HTTP 代理网关。',
    },
    '未收到 HTTP 响应': {
        "en": 'No HTTP response received',
        "zh-CN": '未收到 HTTP 响应',
    },
    '未核验': {
        "en": 'not verified',
        "zh-CN": '未核验',
    },
    '本机模式仅接受控制台所在机器的地址。': {
        "en": 'The local mode only accepts the address of the machine that runs the console.',
        "zh-CN": '本机模式仅接受控制台所在机器的地址。',
    },
    '本机模式使用控制台账号，不进行 SSH 登录；Windows 请使用单命令代理。': {
        "en": 'The local mode uses the console account and does not log in over SSH; on Windows use the one-command proxy.',
        "zh-CN": '本机模式使用控制台账号，不进行 SSH 登录；Windows 请使用单命令代理。',
    },
    '本机观测网关只监听回环地址，远程节点无法访问；请为远程节点选择可达的网关。': {
        "en": 'The local observation gateway listens on the loopback interface only, so a remote node cannot reach it; choose a reachable gateway for the remote node.',
        "zh-CN": '本机观测网关只监听回环地址，远程节点无法访问；请为远程节点选择可达的网关。',
    },
    '本机观测网关已{}': {
        "en": 'The local observation gateway has been {}',
        "zh-CN": '本机观测网关已{}',
    },
    '核验未确认，登记保留': {
        "en": 'The verification was not confirmed; the record is kept',
        "zh-CN": '核验未确认，登记保留',
    },
    '此执行上下文由其它节点持有；未覆盖其配置。': {
        "en": 'Another node holds this execution context; its configuration was not overwritten.',
        "zh-CN": '此执行上下文由其它节点持有；未覆盖其配置。',
    },
    '此接口只接受 no_proxy': {
        "en": 'This endpoint only accepts no_proxy',
        "zh-CN": '此接口只接受 no_proxy',
    },
    '此控制台需要访问令牌。请打开控制台日志中打印的访问链接，': {
        "en": 'This console requires an access token. Open the access link printed in the console log, ',
        "zh-CN": '此控制台需要访问令牌。请打开控制台日志中打印的访问链接，',
    },
    '此旧记录此前按本机执行。请先明确保存为本机模式并完成恢复，再改为 SSH 身份。': {
        "en": 'This old record was executed locally. Save it explicitly as the local mode and complete the restoration before moving it to an SSH identity.',
        "zh-CN": '此旧记录此前按本机执行。请先明确保存为本机模式并完成恢复，再改为 SSH 身份。',
    },
    '此面板仅接受 HTTP(S) URL 或 curl GET 请求；其他业务命令请使用 CLI': {
        "en": 'This panel only accepts an HTTP(S) URL or a curl GET request; use the CLI for other commands',
        "zh-CN": '此面板仅接受 HTTP(S) URL 或 curl GET 请求；其他业务命令请使用 CLI',
    },
    '测试期间节点绑定已变化，请重新测试。': {
        "en": 'The node binding changed during the test; test again.',
        "zh-CN": '测试期间节点绑定已变化，请重新测试。',
    },
    '目标出现重定向循环': {
        "en": 'The target produced a redirect loop',
        "zh-CN": '目标出现重定向循环',
    },
    '目标容器已停止': {
        "en": 'The target container has stopped',
        "zh-CN": '目标容器已停止',
    },
    '目标必须是无凭据的 HTTP 或 HTTPS URL': {
        "en": 'The target must be an HTTP or HTTPS URL without credentials',
        "zh-CN": '目标必须是无凭据的 HTTP 或 HTTPS URL',
    },
    '目标端口必须在 1 至 65535 之间': {
        "en": 'The target port must be between 1 and 65535',
        "zh-CN": '目标端口必须在 1 至 65535 之间',
    },
    '目标配置存在人工修改；请保留修改并核对快照。': {
        "en": 'The target configuration was edited by hand; keep the change and check the snapshot.',
        "zh-CN": '目标配置存在人工修改；请保留修改并核对快照。',
    },
    '直连列表应为以逗号分隔的主机、IP 或网段': {
        "en": 'The bypass list must be comma separated hosts, IP addresses or ranges',
        "zh-CN": '直连列表应为以逗号分隔的主机、IP 或网段',
    },
    '确认旧本机执行位置时，请先保留原地址与账号字段。': {
        "en": 'When you confirm the old local execution place, keep the original address and account fields first.',
        "zh-CN": '确认旧本机执行位置时，请先保留原地址与账号字段。',
    },
    '绑定的网关不存在，请重新选择并保存。': {
        "en": 'The bound gateway does not exist; choose it again and save it.',
        "zh-CN": '绑定的网关不存在，请重新选择并保存。',
    },
    '缺少启用前基线或可核验的旧快照；未写入配置，无法宣称已恢复，登记保留。': {
        "en": 'The baseline from before the enabling or a verifiable old snapshot is missing; no configuration was written, so the restoration cannot be claimed and the record is kept.',
        "zh-CN": '缺少启用前基线或可核验的旧快照；未写入配置，无法宣称已恢复，登记保留。',
    },
    "网关ID '{gid}' 已存在": {
        "en": "The gateway id '{gid}' already exists",
        "zh-CN": "网关ID '{gid}' 已存在",
    },
    '网关ID不能为空': {
        "en": 'The gateway id cannot be empty',
        "zh-CN": '网关ID不能为空',
    },
    '网关不存在': {
        "en": 'The gateway does not exist',
        "zh-CN": '网关不存在',
    },
    '网关名称和IP不能为空': {
        "en": 'The gateway name and IP cannot be empty',
        "zh-CN": '网关名称和IP不能为空',
    },
    '节点 ID 已存在，请更换。': {
        "en": 'The node id already exists; choose another one.',
        "zh-CN": '节点 ID 已存在，请更换。',
    },
    '节点不存在': {
        "en": 'The node does not exist',
        "zh-CN": '节点不存在',
    },
    '节点名称和主机地址不能为空': {
        "en": 'The node name and the host address cannot be empty',
        "zh-CN": '节点名称和主机地址不能为空',
    },
    '节点地址或身份已更改；请重新输入该目标的密码，不能复用原节点凭据': {
        "en": 'The address or the identity of the node changed; enter the password of that target again, the credentials of the old node are not reused',
        "zh-CN": '节点地址或身份已更改；请重新输入该目标的密码，不能复用原节点凭据',
    },
    '节点托管状态未知；尚未执行配置写入，登记保留。': {
        "en": 'The managed state of the node is unknown; no configuration was written and the record is kept.',
        "zh-CN": '节点托管状态未知；尚未执行配置写入，登记保留。',
    },
    '节点执行超时': {
        "en": 'The node execution timed out',
        "zh-CN": '节点执行超时',
    },
    '节点操作已核验': {
        "en": 'The node operation is verified',
        "zh-CN": '节点操作已核验',
    },
    '节点操作未完成，登记保留。': {
        "en": 'The node operation did not complete; the record is kept.',
        "zh-CN": '节点操作未完成，登记保留。',
    },
    '节点登记已保存': {
        "en": 'The node registration is saved',
        "zh-CN": '节点登记已保存',
    },
    '节点登记已保存，尚未开启代理。': {
        "en": 'The node registration is saved; the proxy is not enabled yet.',
        "zh-CN": '节点登记已保存，尚未开启代理。',
    },
    '节点登记已更新': {
        "en": 'The node registration was updated',
        "zh-CN": '节点登记已更新',
    },
    '节点登记已更新。': {
        "en": 'The node registration was updated.',
        "zh-CN": '节点登记已更新。',
    },
    '节点登记已移除，认证资料已删除': {
        "en": 'The node registration was removed and the credentials were deleted',
        "zh-CN": '节点登记已移除，认证资料已删除',
    },
    '节点登记已移除，认证资料已删除；仅保留加回所需的非敏感登记信息。': {
        "en": 'The node registration was removed and the credentials were deleted; only the non-sensitive registration needed to add it back is kept.',
        "zh-CN": '节点登记已移除，认证资料已删除；仅保留加回所需的非敏感登记信息。',
    },
    '节点绑定已变化，请刷新并重新保存所选网关。': {
        "en": 'The node binding changed; load the page again and save the selected gateway.',
        "zh-CN": '节点绑定已变化，请刷新并重新保存所选网关。',
    },
    '节点绑定版本已变化，请刷新后重试。': {
        "en": 'The binding version of the node changed; load the page again and try once more.',
        "zh-CN": '节点绑定版本已变化，请刷新后重试。',
    },
    '节点记录已变化或缺少版本，请刷新后重试。': {
        "en": 'The node record changed or has no version; load the page again and try once more.',
        "zh-CN": '节点记录已变化或缺少版本，请刷新后重试。',
    },
    '节点配置操作未完成；保留登记与快照供恢复。': {
        "en": 'The configuration operation did not complete; the registration and the snapshot are kept for the recovery.',
        "zh-CN": '节点配置操作未完成；保留登记与快照供恢复。',
    },
    '该执行账号/容器已由节点 {} 登记，请编辑现有节点。': {
        "en": 'That execution account or container is already registered by node {}; edit the existing node.',
        "zh-CN": '该执行账号/容器已由节点 {} 登记，请编辑现有节点。',
    },
    '该执行身份已经登记，原记录、绑定和状态均已保留；修改请使用编辑。': {
        "en": 'That execution identity is already registered; the original record, binding and state are kept. Use edit to change it.',
        "zh-CN": '该执行身份已经登记，原记录、绑定和状态均已保留；修改请使用编辑。',
    },
    '请为当前身份重新输入密码；已删除节点的凭据不会恢复。': {
        "en": 'Enter the password again for the current identity; the credentials of a removed node are not restored.',
        "zh-CN": '请为当前身份重新输入密码；已删除节点的凭据不会恢复。',
    },
    '请使用 HTTP 或 mixed 代理监听端口': {
        "en": 'Use an HTTP or mixed proxy listening port',
        "zh-CN": '请使用 HTTP 或 mixed 代理监听端口',
    },
    '请使用无凭据的 HTTP 代理入口': {
        "en": 'Use an HTTP proxy entry point without credentials',
        "zh-CN": '请使用无凭据的 HTTP 代理入口',
    },
    '请先保存节点绑定的网关。': {
        "en": 'Save the gateway bound to the node first.',
        "zh-CN": '请先保存节点绑定的网关。',
    },
    '请先添加 HTTP 代理网关': {
        "en": 'Add an HTTP proxy gateway first',
        "zh-CN": '请先添加 HTTP 代理网关',
    },
    '请先选择并保存节点绑定的网关。': {
        "en": 'Choose and save the gateway bound to the node first.',
        "zh-CN": '请先选择并保存节点绑定的网关。',
    },
    '请提供 target_url 或请求文本中的一个': {
        "en": 'Give either target_url or the request text',
        "zh-CN": '请提供 target_url 或请求文本中的一个',
    },
    '请求中不支持 shell 插值或换行，请提供完整的单行 URL': {
        "en": 'Shell interpolation and line breaks are not supported in the request; give a complete URL on one line',
        "zh-CN": '请求中不支持 shell 插值或换行，请提供完整的单行 URL',
    },
    '请求体包含无效 JSON': {
        "en": 'The request body contains invalid JSON',
        "zh-CN": '请求体包含无效 JSON',
    },
    '请求体必须是 JSON 对象': {
        "en": 'The request body must be a JSON object',
        "zh-CN": '请求体必须是 JSON 对象',
    },
    '请求体必须是 UTF-8 JSON': {
        "en": 'The request body must be UTF-8 JSON',
        "zh-CN": '请求体必须是 UTF-8 JSON',
    },
    '请求体过大': {
        "en": 'The request body is too large',
        "zh-CN": '请求体过大',
    },
    '请求失败': {
        "en": 'The request failed',
        "zh-CN": '请求失败',
    },
    '请求必须包含一个 URL': {
        "en": 'The request must contain one URL',
        "zh-CN": '请求必须包含一个 URL',
    },
    '请求必须是 JSON 对象': {
        "en": 'The request must be a JSON object',
        "zh-CN": '请求必须是 JSON 对象',
    },
    '请求必须是 URL 或 curl GET 文本': {
        "en": 'The request must be a URL or a curl GET text',
        "zh-CN": '请求必须是 URL 或 curl GET 文本',
    },
    '请输入无空格和控制字符的 HTTP(S) URL': {
        "en": 'Enter an HTTP(S) URL without spaces or control characters',
        "zh-CN": '请输入无空格和控制字符的 HTTP(S) URL',
    },
    '请输入有效的代理主机名或 IP 地址': {
        "en": 'Enter a valid proxy host name or IP address',
        "zh-CN": '请输入有效的代理主机名或 IP 地址',
    },
    '请选择 SSH、Docker 宿主机或明确的本机执行模式。': {
        "en": 'Choose SSH, a Docker host or an explicit local execution mode.',
        "zh-CN": '请选择 SSH、Docker 宿主机或明确的本机执行模式。',
    },
    '请选择密钥或密码认证。': {
        "en": 'Choose key or password authentication.',
        "zh-CN": '请选择密钥或密码认证。',
    },
    '配置保存成功': {
        "en": 'The configuration is saved',
        "zh-CN": '配置保存成功',
    },
    '配置脚本已结束，但独立登录核验尚未确认结果；登记与恢复基线已保留。': {
        "en": 'The configuration script ended, but the independent login check has not confirmed the result; the registration and the recovery baseline are kept.',
        "zh-CN": '配置脚本已结束，但独立登录核验尚未确认结果；登记与恢复基线已保留。',
    },
    '重定向超过 5 次': {
        "en": 'More than five redirects',
        "zh-CN": '重定向超过 5 次',
    },
    '🟢 宿主机已连通 ({rtt_or_err}ms)，且 Docker 容器【{container_name}】正在健康运行中！': {
        "en": '🟢 The Docker host answers ({rtt_or_err}ms) and the container {container_name} is running healthily!',
        "zh-CN": '🟢 宿主机已连通 ({rtt_or_err}ms)，且 Docker 容器【{container_name}】正在健康运行中！',
    },
    '🟢 深度预检完全通过！TCP ({rtt_ms}ms) + SSH协议握手{banner_info} + {auth_msg}': {
        "en": '🟢 The deep pre-check passed completely! TCP ({rtt_ms}ms) + SSH handshake{banner_info} + {auth_msg}',
        "zh-CN": '🟢 深度预检完全通过！TCP ({rtt_ms}ms) + SSH协议握手{banner_info} + {auth_msg}',
    },
}


def normalize_language(value):
    """Return the supported language for a request, or the default."""
    text = str(value or "").strip().lower()
    if not text:
        return DEFAULT_LANGUAGE
    if text.startswith("zh"):
        return "zh-CN"
    if text.startswith("en"):
        return "en"
    return DEFAULT_LANGUAGE


def message(key, language):
    """Return one message in the requested language, or the key itself."""
    entry = MESSAGES.get(key)
    if not entry:
        return key
    return entry.get(normalize_language(language), entry[DEFAULT_LANGUAGE])


def localize(value, language):
    """Localize a message that the server sends to the browser."""
    if not isinstance(value, str) or not value:
        return value
    entry = MESSAGES.get(value)
    if not entry:
        return value
    return entry.get(normalize_language(language), entry[DEFAULT_LANGUAGE])


def catalogue_script():
    """The catalogue as a JavaScript file for the browser."""
    payload = json.dumps(MESSAGES, ensure_ascii=False, sort_keys=True)
    return "window.NPT_MESSAGES = " + payload + ";\n"


def placeholders(key):
    """The parameter names one message expects."""
    entry = MESSAGES.get(key) or {}
    return sorted(set(PLACEHOLDER.findall(entry.get("en", ""))))
