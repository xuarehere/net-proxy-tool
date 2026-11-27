"""Regenerate the English and Chinese architecture SVGs using the Python standard library."""

from pathlib import Path
from xml.sax.saxutils import escape

ASSETS = Path(__file__).resolve().parent / "assets"

LABELS = {
    "en": {
        "title": "net-proxy-tool v1.5.0 — Where Control & Traffic Travel",
        "desc": "Dashed lines show configuration, orchestration and read-only MCP diagnostics. Solid teal lines trace isolated application traffic through an HTTP proxy to its destination.",
        "legend_ctrl": "Control / Config / Read-only MCP",
        "legend_flow": "Proxied HTTP(S) Traffic",
        "legend_verify": "Baseline Snapshot & Restore Check",
        "col1": "1. ENTRY POINTS",
        "col2": "2. SCOPED EXECUTION BOUNDARY",
        "col3": "3. GATEWAY & EGRESS",
        "col4": "4. TARGETS",
        "browser_t": "Operator Browser",
        "browser_s": "127.0.0.1 URL or SSH tunnel",
        "console_t": "Web Console",
        "console_b": "WRITE",
        "console_s": "web/server.py · Gateways, probes, nodes",
        "cli_t": "CLI & Python SDK",
        "cli_b": "SCOPED",
        "cli_s": "with-proxy · with ProxySession():",
        "mcp_t": "Agent MCP Server",
        "mcp_b": "READ-ONLY",
        "mcp_s": "net_proxy_mcp.py · 6 diagnostic tools",
        "mcp_s2": "Kiro / IDE Agents · Never writes config.json",
        "route_ssh": "SSH",
        "route_docker": "docker exec",
        "route_inspect": "inspect=True",
        "local_t": "Local Sandbox Process",
        "local_s": "Parent environment stays untouched",
        "local_p1": "• HTTP_PROXY / NO_PROXY scoped to child or block",
        "local_p2": "• Process tree killed cleanly on timeout",
        "linux_t": "Linux Node (Target Account)",
        "linux_s": "Managed files snapshotted before edit",
        "linux_p1": "• Snapshots in ~/.local/state/net-proxy-tool/",
        "linux_p2": "• Restored & verified in fresh login shell",
        "host_t": "Docker Host",
        "host_s": "Runs docker exec only on selected container",
        "docker_t": "Target Container",
        "docker_s": "Isolated env · Sibling containers untouched",
        "obs_t": "Observation Gateway",
        "obs_b": "LOOPBACK",
        "obs_s1": "127.0.0.1 · Ports 80/443 · Max 64 tunnels",
        "obs_s2": "Logs contacted hosts only (zero bodies)",
        "gw_t": "HTTP Proxy Gateway",
        "gw_s1": "Existing proxy or local observation gateway",
        "gw_p1": "Stages: TCP → CONNECT → TLS → HTTP",
        "gw_p2": "Failing hop, redirects & peer IP evidence",
        "cmp_t": "Two-Path Node Verification",
        "cmp_s": "Explicit proxy vs plain curl side-by-side",
        "dest_t": "HTTPS Targets",
        "dest_s": "Allowed destinations",
        "foot_1": "Runtime: Python 3.8+ standard library only (0 external deps)",
        "foot_2": "Secrets: Console never prints or returns SSH passwords via API",
        "foot_3": "Reversible: Off-switch restores mode, content & file absence",
    },
    "zh": {
        "title": "net-proxy-tool v1.5.0 — 控制流与代理流量全景架构",
        "desc": "虚线表示管理配置、节点编排与只读 MCP 诊断；实线表示隔离后的应用流量经 HTTP 代理网关到达目标服务。",
        "legend_ctrl": "管理下发 / 只读 MCP 控制流",
        "legend_flow": "隔离后的 HTTP(S) 代理流量",
        "legend_verify": "基线快照与干净登录态复核",
        "col1": "1. 接入与控制入口",
        "col2": "2. 零污染执行隔离边界",
        "col3": "3. 代理网关与对比探测",
        "col4": "4. 目标服务",
        "browser_t": "操作者浏览器",
        "browser_s": "本机回环地址或 SSH 端口转发",
        "console_t": "Web 控制台",
        "console_b": "唯一写入口",
        "console_s": "web/server.py · 网关、探针与节点管理",
        "cli_t": "CLI 与 Python SDK",
        "cli_b": "局部作用域",
        "cli_s": "with-proxy · with ProxySession():",
        "mcp_t": "MCP 编程代理接口",
        "mcp_b": "只读诊断",
        "mcp_s": "net_proxy_mcp.py · 6 项只读诊断工具",
        "mcp_s2": "供 Kiro / Agent 调用 · 严禁写入配置",
        "route_ssh": "SSH",
        "route_docker": "docker exec",
        "route_inspect": "inspect=True",
        "local_t": "本机沙箱子进程",
        "local_s": "父进程与系统代理设置保持零改动",
        "local_p1": "• HTTP_PROXY / NO_PROXY 仅限子进程或代码块",
        "local_p2": "• 超时或退出后完整终止进程树并清理现场",
        "linux_t": "Linux 远程节点 (指定账号)",
        "linux_s": "写入配置前先捕获文件与权限快照",
        "linux_p1": "• 快照存于 ~/.local/state/net-proxy-tool/",
        "linux_p2": "• 关闭后在新开 login shell 逐项核验恢复",
        "host_t": "Docker 宿主机",
        "host_s": "经宿主机穿透，仅操作指定的目标容器",
        "docker_t": "目标业务容器",
        "docker_s": "容器内独立生效 · 同宿其它容器零污染",
        "obs_t": "本机观测网关",
        "obs_b": "仅监听回环",
        "obs_s1": "127.0.0.1 · 仅 80/443 端口 · 最多 64 隧道",
        "obs_s2": "仅记录访问主机名，不留存请求响应正文",
        "gw_t": "HTTP 代理网关",
        "gw_s1": "用户已有代理（或内置观测网关）",
        "gw_p1": "逐跳诊断：TCP → CONNECT → TLS → HTTP",
        "gw_p2": "标出失败站点、跳转链路与应答对端 IP",
        "cmp_t": "节点池双路径对照",
        "cmp_s": "并发对照「显式代理」与「普通 curl」出网",
        "dest_t": "目标 HTTPS 服务",
        "dest_s": "业务访问站点",
        "foot_1": "零第三方依赖：核心与运行态纯 Python 3.8+ 标准库实现",
        "foot_2": "凭据保护：SSH 密码等敏感字段绝不返回 API 或写入日志",
        "foot_3": "可逆清理：关闭开关后完整恢复文件内容、权限与缺失状态",
    },
}


def diagram(lang, t):
    parts = []

    def add(raw):
        parts.append(raw)

    def esc(key):
        return escape(t[key])

    # Canvas 1380 x 770 with spacious column gutters & card padding
    add(f'''<svg xmlns="http://www.w3.org/2000/svg" lang="{lang}" viewBox="0 0 1380 770" width="1380" height="770" role="img" aria-labelledby="arch-title arch-desc">
<title id="arch-title">{esc("title")}</title>
<desc id="arch-desc">{esc("desc")}</desc>
<defs>
  <linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#f8fafc"/>
    <stop offset="100%" stop-color="#f1f5f9"/>
  </linearGradient>
  <linearGradient id="hero-grad" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#0f5149"/>
    <stop offset="100%" stop-color="#136a5f"/>
  </linearGradient>
  <linearGradient id="dest-grad" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" stop-color="#ecfdf5"/>
    <stop offset="100%" stop-color="#d1fae5"/>
  </linearGradient>
  <filter id="card-shadow" x="-4%" y="-6%" width="108%" height="116%">
    <feDropShadow dx="0" dy="3" stdDeviation="6" flood-color="#0f172a" flood-opacity="0.06"/>
  </filter>
  <marker id="ctrl-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
    <path d="M1,1 L7,4 L1,7 Z" fill="#4f46e5"/>
  </marker>
  <marker id="flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
    <path d="M1,1 L7,4 L1,7 Z" fill="#0f766e"/>
  </marker>
  <marker id="obs-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
    <path d="M1,1 L6,3.5 L1,6 Z" fill="#d97706"/>
  </marker>
</defs>
<style>
  text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }}
  .title {{ font-size: 24px; font-weight: 800; fill: #0f172a; letter-spacing: -0.3px; }}
  .subtitle {{ font-size: 13.5px; font-weight: 400; fill: #475569; }}
  .col-hdr {{ font-size: 12px; font-weight: 700; fill: #475569; letter-spacing: 0.7px; }}
  .legend-txt {{ font-size: 12.5px; font-weight: 600; fill: #334155; }}
  .card-title {{ font-size: 15px; font-weight: 700; fill: #0f172a; }}
  .card-sub {{ font-size: 12px; font-weight: 500; fill: #475569; }}
  .card-bullet {{ font-size: 11.5px; font-weight: 450; fill: #334155; }}
  .hero-title {{ font-size: 16px; font-weight: 700; fill: #ffffff; }}
  .hero-sub {{ font-size: 12px; font-weight: 500; fill: #ccfbf1; }}
  .hero-bullet {{ font-size: 11.5px; font-weight: 500; fill: #ecfdf5; }}
  .badge-txt {{ font-size: 10.5px; font-weight: 700; letter-spacing: 0.4px; }}
  .route-lbl {{ font-size: 11px; font-weight: 700; fill: #4338ca; }}
  .foot-txt {{ font-size: 11.5px; font-weight: 500; fill: #475569; }}
  .ctrl-line {{ fill: none; stroke: #4f46e5; stroke-width: 2; stroke-dasharray: 5 4; stroke-linecap: round; stroke-linejoin: round; }}
  .flow-line {{ fill: none; stroke: #0f766e; stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round; }}
  .obs-line {{ fill: none; stroke: #d97706; stroke-width: 2; stroke-dasharray: 4 3; stroke-linecap: round; stroke-linejoin: round; }}
</style>''')

    # Background + outer border
    add('<rect x="0" y="0" width="1380" height="770" rx="16" fill="url(#bg-grad)"/>')
    add('<rect x="1" y="1" width="1378" height="768" rx="15" fill="none" stroke="#cbd5e1" stroke-width="1.5"/>')

    # Header section
    add(f'<text x="36" y="42" class="title">{esc("title")}</text>')
    add(f'<text x="36" y="66" class="subtitle">{esc("desc")}</text>')

    # Legend pills row
    add('<rect x="36" y="82" width="790" height="32" rx="8" fill="#ffffff" stroke="#e2e8f0"/>')
    add('<path d="M52 98h30" class="ctrl-line" marker-end="url(#ctrl-arrow)"/>')
    add(f'<text x="90" y="102" class="legend-txt">{esc("legend_ctrl")}</text>')
    add('<path d="M318 98h30" class="flow-line" marker-end="url(#flow-arrow)"/>')
    add(f'<text x="356" y="102" class="legend-txt">{esc("legend_flow")}</text>')
    add('<rect x="556" y="90" width="14" height="14" rx="3" fill="#fef3c7" stroke="#d97706" stroke-width="1.5"/>')
    add(f'<text x="578" y="102" class="legend-txt">{esc("legend_verify")}</text>')

    # Column zone frames:
    # Col1: 36..340 (w=304), Gutter 340..428 (88px!), Col2: 428..812 (w=384), Gutter 812..866 (54px), Col3: 866..1186 (w=320), Col4: 1216..1344 (w=128)
    zones = [
        (36, 130, 304, 560, "#ffffff", "#cbd5e1", "col1"),
        (428, 130, 384, 560, "#f8fafc", "#cbd5e1", "col2"),
        (866, 130, 320, 560, "#ffffff", "#cbd5e1", "col3"),
        (1214, 130, 130, 560, "none", "none", "col4"),
    ]
    for x, y, w, h, fill, stroke, hdr in zones:
        if fill != "none":
            add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-opacity="0.7" fill-opacity="0.65"/>')
        add(f'<text x="{x + 14}" y="152" class="col-hdr">{esc(hdr)}</text>')

    # ---------------- COLUMN 1: ENTRY POINTS (cards x=50, w=276 -> x..326) ----------------
    # 1) Operator Browser
    add('<g filter="url(#card-shadow)">')
    add('<rect x="50" y="170" width="276" height="72" rx="10" fill="#ffffff" stroke="#cbd5e1"/>')
    add('<circle cx="72" cy="196" r="12" fill="#e0e7ff"/>')
    add('<text x="72" y="201" text-anchor="middle" font-size="13" fill="#4338ca" font-weight="700">UI</text>')
    add(f'<text x="94" y="198" class="card-title">{esc("browser_t")}</text>')
    add(f'<text x="94" y="220" class="card-sub">{esc("browser_s")}</text>')
    add('</g>')

    # Browser -> Web Console arrow
    add('<path d="M188 242v28" class="ctrl-line" marker-end="url(#ctrl-arrow)"/>')

    # 2) Web Console
    add('<g filter="url(#card-shadow)">')
    add('<rect x="50" y="276" width="276" height="106" rx="10" fill="#eef2ff" stroke="#818cf8" stroke-width="1.5"/>')
    add(f'<text x="64" y="302" class="card-title">{esc("console_t")}</text>')
    add('<rect x="242" y="286" width="72" height="20" rx="10" fill="#4f46e5"/>')
    add(f'<text x="278" y="300" text-anchor="middle" class="badge-txt" fill="#ffffff">{esc("console_b")}</text>')
    add(f'<text x="64" y="328" class="card-sub">{esc("console_s")}</text>')
    add('<text x="64" y="358" class="card-bullet">web/local_gateway.py · diagnostics.py</text>')
    add('</g>')

    # 3) CLI & Python SDK
    add('<g filter="url(#card-shadow)">')
    add('<rect x="50" y="408" width="276" height="104" rx="10" fill="#ffffff" stroke="#cbd5e1"/>')
    add(f'<text x="64" y="434" class="card-title">{esc("cli_t")}</text>')
    add('<rect x="242" y="418" width="72" height="20" rx="10" fill="#0f766e" fill-opacity="0.14"/>')
    add(f'<text x="278" y="432" text-anchor="middle" class="badge-txt" fill="#0f766e">{esc("cli_b")}</text>')
    add(f'<text x="64" y="460" class="card-sub">{esc("cli_s")}</text>')
    add('<text x="64" y="488" class="card-bullet">with_proxy.py · sdk/proxy_session.py</text>')
    add('</g>')

    # 4) MCP Server
    add('<g filter="url(#card-shadow)">')
    add('<rect x="50" y="538" width="276" height="122" rx="10" fill="#f8fafc" stroke="#94a3b8" stroke-dasharray="4 2"/>')
    add(f'<text x="64" y="564" class="card-title">{esc("mcp_t")}</text>')
    add('<rect x="238" y="548" width="76" height="20" rx="10" fill="#fef3c7" stroke="#d97706"/>')
    add(f'<text x="276" y="562" text-anchor="middle" class="badge-txt" fill="#92400e">{esc("mcp_b")}</text>')
    add(f'<text x="64" y="590" class="card-sub">{esc("mcp_s")}</text>')
    add(f'<text x="64" y="618" class="card-bullet">{esc("mcp_s2")}</text>')
    add('<text x="64" y="638" class="card-bullet">list_gateways · check_* · run_with_proxy</text>')
    add('</g>')

    # ---------------- COLUMN 2: SCOPED EXECUTION (cards x=446, w=348 -> x..794) ----------------
    # Box A: Local Sandbox Process (y: 170..314)
    add('<g filter="url(#card-shadow)">')
    add('<rect x="446" y="170" width="348" height="144" rx="10" fill="#ffffff" stroke="#0f766e" stroke-width="1.5"/>')
    add('<rect x="446" y="170" width="6" height="144" rx="3" fill="#0f766e"/>')
    add(f'<text x="466" y="196" class="card-title">{esc("local_t")}</text>')
    add(f'<text x="466" y="218" class="card-sub">{esc("local_s")}</text>')
    add('<line x1="466" y1="232" x2="778" y2="232" stroke="#e2e8f0"/>')
    add(f'<text x="466" y="256" class="card-bullet">{esc("local_p1")}</text>')
    add(f'<text x="466" y="280" class="card-bullet">{esc("local_p2")}</text>')
    add('</g>')

    # Box B: Linux Node (y: 334..478)
    add('<g filter="url(#card-shadow)">')
    add('<rect x="446" y="334" width="348" height="144" rx="10" fill="#ffffff" stroke="#d97706" stroke-width="1.5"/>')
    add('<rect x="446" y="334" width="6" height="144" rx="3" fill="#d97706"/>')
    add(f'<text x="466" y="360" class="card-title">{esc("linux_t")}</text>')
    add(f'<text x="466" y="382" class="card-sub">{esc("linux_s")}</text>')
    add('<line x1="466" y1="396" x2="778" y2="396" stroke="#e2e8f0"/>')
    add(f'<text x="466" y="420" class="card-bullet">{esc("linux_p1")}</text>')
    add(f'<text x="466" y="444" class="card-bullet">{esc("linux_p2")}</text>')
    add('</g>')

    # Box C: Docker Host & Nested Container (y: 498..672)
    add('<g filter="url(#card-shadow)">')
    add('<rect x="446" y="498" width="348" height="174" rx="10" fill="#f8fafc" stroke="#64748b" stroke-width="1.5"/>')
    add(f'<text x="464" y="524" class="card-title">{esc("host_t")}</text>')
    add(f'<text x="464" y="544" class="card-sub">{esc("host_s")}</text>')
    add('<path d="M482 552v26" class="ctrl-line" marker-end="url(#ctrl-arrow)"/>')
    add('<rect x="494" y="554" width="84" height="18" rx="9" fill="#e0e7ff"/>')
    add(f'<text x="536" y="567" text-anchor="middle" class="route-lbl">{esc("route_docker")}</text>')
    add('<rect x="462" y="582" width="316" height="74" rx="8" fill="#ecfdf5" stroke="#0f766e" stroke-width="1.4"/>')
    add(f'<text x="476" y="608" class="card-title">{esc("docker_t")}</text>')
    add(f'<text x="476" y="630" class="card-sub">{esc("docker_s")}</text>')
    add('</g>')

    # ---------------- ARROWS IN CLEAN 88px GUTTER (340..428) ----------------
    # Rail x=374: Web Console -> Local (top y=214) & Linux SSH (y=406) & Docker SSH (y=530)
    add('<path d="M326 306 H374 V214 H440" class="ctrl-line" marker-end="url(#ctrl-arrow)"/>')
    add('<path d="M326 332 H374 V406 H440" class="ctrl-line" marker-end="url(#ctrl-arrow)"/>')
    add('<path d="M374 406 V530 H440" class="ctrl-line" marker-end="url(#ctrl-arrow)"/>')
    # Rail x=360: CLI/SDK -> Local (y=248)
    add('<path d="M326 458 H360 V248 H440" class="ctrl-line" marker-end="url(#ctrl-arrow)"/>')
    # Rail x=348: MCP -> Local (y=282)
    add('<path d="M326 598 H348 V282 H440" class="ctrl-line" marker-end="url(#ctrl-arrow)"/>')

    # Clean SSH badges sitting purely in x=382..422, completely clear of all vertical rails!
    add('<rect x="380" y="382" width="44" height="18" rx="9" fill="#eef2ff" stroke="#818cf8"/>')
    add(f'<text x="402" y="395" text-anchor="middle" class="route-lbl">{esc("route_ssh")}</text>')
    add('<rect x="380" y="506" width="44" height="18" rx="9" fill="#eef2ff" stroke="#818cf8"/>')
    add(f'<text x="402" y="519" text-anchor="middle" class="route-lbl">{esc("route_ssh")}</text>')

    # ---------------- COLUMN 3: GATEWAYS & EGRESS (cards x=880, w=292 -> x..1172) ----------------
    # 1) Local Observation Gateway
    add('<g filter="url(#card-shadow)">')
    add('<rect x="880" y="170" width="292" height="122" rx="10" fill="#fffbeb" stroke="#d97706" stroke-width="1.5"/>')
    add(f'<text x="896" y="196" class="card-title">{esc("obs_t")}</text>')
    add('<rect x="1080" y="180" width="80" height="20" rx="10" fill="#fef3c7" stroke="#d97706"/>')
    add(f'<text x="1120" y="194" text-anchor="middle" class="badge-txt" fill="#92400e">{esc("obs_b")}</text>')
    add(f'<text x="896" y="224" class="card-bullet">{esc("obs_s1")}</text>')
    add(f'<text x="896" y="246" class="card-bullet">{esc("obs_s2")}</text>')
    add('<text x="896" y="274" class="card-sub">web/local_gateway.py · Try it now</text>')
    add('</g>')

    # Optional inspect=True chaining arrow -> HTTP Proxy
    add('<path d="M1026 292 V328" class="obs-line" marker-end="url(#obs-arrow)"/>')
    add('<rect x="1036" y="298" width="90" height="18" rx="9" fill="#fef3c7"/>')
    add(f'<text x="1081" y="311" text-anchor="middle" font-size="10.5" font-weight="700" fill="#92400e">{esc("route_inspect")}</text>')

    # 2) HTTP Proxy Gateway (Hero card w=292)
    add('<g filter="url(#card-shadow)">')
    add('<rect x="880" y="334" width="292" height="182" rx="12" fill="url(#hero-grad)"/>')
    add(f'<text x="898" y="364" class="hero-title">{esc("gw_t")}</text>')
    add(f'<text x="898" y="388" class="hero-sub">{esc("gw_s1")}</text>')
    add('<line x1="898" y1="406" x2="1154" y2="406" stroke="#2dd4bf" stroke-opacity="0.4"/>')
    add(f'<text x="898" y="432" class="hero-bullet">{esc("gw_p1")}</text>')
    add(f'<text x="898" y="458" class="hero-bullet">{esc("gw_p2")}</text>')
    add('<rect x="898" y="476" width="256" height="24" rx="6" fill="#042f2e" fill-opacity="0.45"/>')
    add('<text x="1026" y="492" text-anchor="middle" font-size="11" font-weight="600" fill="#99f6e4">HTTP CONNECT · 1x TLS EOF Retry</text>')
    add('</g>')

    # 3) Two-Path Node Verification card
    add('<g filter="url(#card-shadow)">')
    add('<rect x="880" y="544" width="292" height="114" rx="10" fill="#ffffff" stroke="#cbd5e1"/>')
    add(f'<text x="898" y="572" class="card-title">{esc("cmp_t")}</text>')
    add(f'<text x="898" y="596" class="card-sub">{esc("cmp_s")}</text>')
    add('<text x="898" y="624" class="card-bullet">Explicit proxy path  vs  Plain curl baseline</text>')
    add('<text x="898" y="644" class="card-bullet">web/node_probe.py · web/node_baseline.py</text>')
    add('</g>')

    # ---------------- ARROWS: EXECUTION -> HTTP PROXY (gutter 812..866, bus at x=838) ----------------
    add('<path d="M794 242 H838 V619 H778" class="flow-line"/>')
    add('<path d="M794 406 H838" class="flow-line"/>')
    add('<circle cx="838" cy="406" r="4.5" fill="#0f766e"/>')
    add('<path d="M838 425 H874" class="flow-line" marker-end="url(#flow-arrow)"/>')
    add('<path d="M838 230 H874" class="obs-line" marker-end="url(#obs-arrow)"/>')
    add('<circle cx="838" cy="242" r="4" fill="#0f766e"/>')

    # ---------------- COLUMN 4: TARGET SERVICES (x=1218, w=126) ----------------
    add('<path d="M1172 425 H1212" class="flow-line" marker-end="url(#flow-arrow)"/>')
    add('<g filter="url(#card-shadow)">')
    add('<rect x="1218" y="280" width="126" height="292" rx="12" fill="url(#dest-grad)" stroke="#0f766e" stroke-width="1.4"/>')
    add('<path d="M1263 328 a12 12 0 0 1 22 -6 a10 10 0 0 1 16 8 a9 9 0 0 1 -2 18 h-34 a10 10 0 0 1 -2 -20 z" fill="#ffffff" stroke="#0f766e" stroke-width="1.8"/>')
    add(f'<text x="1281" y="372" text-anchor="middle" class="card-title">{esc("dest_t")}</text>')
    add(f'<text x="1281" y="392" text-anchor="middle" class="card-sub">{esc("dest_s")}</text>')
    for idx, tag in enumerate(("Google", "Claude", "ChatGPT", "GitHub", "PyPI")):
        py = 414 + idx * 28
        add(f'<rect x="1237" y="{py}" width="88" height="21" rx="10" fill="#ffffff" stroke="#99f6e4"/>')
        add(f'<text x="1281" y="{py + 14}" text-anchor="middle" font-size="11" font-weight="600" fill="#0f5149">{tag}</text>')
    add('</g>')

    # ---------------- FOOTER INVARIANTS BAR ----------------
    add('<rect x="36" y="706" width="1308" height="36" rx="8" fill="#ffffff" stroke="#cbd5e1"/>')
    add(f'<text x="58" y="728" class="foot-txt">{esc("foot_1")}</text>')
    add('<line x1="472" y1="714" x2="472" y2="734" stroke="#cbd5e1"/>')
    add(f'<text x="494" y="728" class="foot-txt">{esc("foot_2")}</text>')
    add('<line x1="912" y1="714" x2="912" y2="734" stroke="#cbd5e1"/>')
    add(f'<text x="934" y="728" class="foot-txt">{esc("foot_3")}</text>')

    add("</svg>")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    for language, labels in LABELS.items():
        (ASSETS / f"architecture.{language}.svg").write_text(diagram(language, labels), encoding="utf-8")
