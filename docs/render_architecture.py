"""Regenerate the two SVGs with the Python standard library."""

from pathlib import Path
from xml.sax.saxutils import escape

ASSETS = Path(__file__).resolve().parent / "assets"
LABELS = {
    "zh": {
        "title": "控制台如何配置节点，应用如何发出请求",
        "desc": "虚线为管理路径。CLI 或 SDK 也能独立配置本机任务。实线为应用通过已有 HTTP 代理访问目标服务的路径。",
        "control": "配置与管理", "traffic": "应用请求",
        "entry": "入口", "work": "执行任务的位置", "egress": "网络出口",
        "cli": "CLI / Python SDK / MCP 服务器", "optional": "可独立使用", "browser": "浏览器",
        "access": "本机访问或 SSH 隧道", "console": "Web 控制台", "config": "网关配置、诊断与节点管理",
        "run": "启动任务", "local": "本机任务", "child": "本机应用 / 子进程",
        "linux": "Linux 节点", "ssh": "SSH 直连目标账号", "process": "该账号运行的应用进程",
        "host": "Docker 宿主机", "docker": "目标容器", "inside": "容器内的应用进程",
        "gateway": "HTTP 代理网关", "own": "由用户提供或工具内置本机网关", "service": "目标服务",
        "target": "HTTP / HTTPS",
    },
    "en": {
        "title": "How applications reach their destination",
        "desc": "Dashed lines show configuration paths. The CLI or SDK can configure a local task independently. Solid lines trace requests from apps through an existing HTTP proxy.",
        "control": "Configuration", "traffic": "Application traffic",
        "entry": "Entry points", "work": "Where tasks run", "egress": "Network",
        "cli": "CLI / Python SDK / MCP server", "optional": "Optional standalone entry", "browser": "Browser",
        "access": "Local URL or SSH tunnel", "console": "Web console", "config": "Gateways and diagnostics",
        "run": "Run task", "local": "Local task", "child": "Local app / child process",
        "linux": "Linux node", "ssh": "SSH to the target account", "process": "App running as that user",
        "host": "Docker host", "docker": "Target container", "inside": "App in the container",
        "gateway": "HTTP proxy", "own": "Provided by the user or the built-in local gateway",
        "service": "Destination", "target": "HTTP / HTTPS",
    },
}


def diagram(lang, labels):
    svg = []

    def rect(x, y, w, h, fill, stroke="none"):
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}"/>')

    def label(x, y, key, style):
        value = escape(labels.get(key, key))
        svg.append(f'<text x="{x}" y="{y}" class="{style}">{value}</text>')

    def path(d, style, end=False):
        marker = f' marker-end="url(#{style}-end)"' if end else ""
        svg.append(f'<path d="{d}" class="{style}"{marker}/>')

    svg.append(f'''<svg xmlns="http://www.w3.org/2000/svg" lang="{lang}" viewBox="0 0 1112 650" role="img" aria-labelledby="title desc">
<title id="title">{escape(labels["title"])}</title><desc id="desc">{escape(labels["desc"])}</desc>
<defs>
  <marker id="ctrl-end" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7Z" fill="#566883"/></marker>
  <marker id="flow-end" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7Z" fill="#137568"/></marker>
</defs>
<style>
  text {{font-family:system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;fill:#163d40}}
  .title {{font-size:34px;font-weight:700}} .section {{font-size:20px;font-weight:650;fill:#446361}}
  .node {{font-size:25px;font-weight:660}} .detail {{font-size:17px;fill:#40585b}}
  .route {{font-size:16px;font-weight:600;fill:#455971}} .light {{font-size:25px;font-weight:700;fill:white}}
  .subtle {{font-size:18px;fill:#dcf3ed}} .legend {{font-size:18px;fill:#3d565c}}
  .ctrl,.flow {{fill:none;stroke-linejoin:round;stroke-linecap:round;stroke-width:2.6}}
  .ctrl {{stroke:#566883;stroke-dasharray:5 5}} .flow {{stroke:#137568;stroke-width:3}}
</style>''')
    rect(0, 0, 1112, 650, "#f8faf7")
    label(32, 57, "title", "title")
    path("M33 95h44", "ctrl", True)
    label(91, 101, "control", "legend")
    path("M262 95h44", "flow", True)
    label(320, 101, "traffic", "legend")
    svg.append('<path d="M32 128h1048" stroke="#cfddda"/>')
    for x, key in ((32, "entry"), (408, "work"), (857, "egress")):
        label(x, 168, key, "section")

    # Control host. The CLI has a direct path independent of the browser/console.
    rect(32, 193, 263, 86, "#e8eaf1")
    label(50, 228, "cli", "node")
    label(50, 255, "optional", "detail")
    path("M297 222H397", "ctrl", True)
    rect(32, 315, 263, 80, "#e8eaf1")
    label(50, 349, "browser", "node")
    label(50, 376, "access", "detail")
    path("M160 398v40", "ctrl", True)
    rect(32, 449, 263, 93, "#e8eaf1")
    label(50, 488, "console", "node")
    label(50, 517, "config", "detail")

    # The console controls a task, an SSH account or a Docker host over SSH.
    path("M297 493H316V260H397", "ctrl", True)
    label(328, 252, "run", "route")
    path("M316 359H397", "ctrl", True)
    label(338, 349, "SSH", "route")
    path("M316 493H397", "ctrl", True)
    label(338, 483, "SSH", "route")
    rect(408, 193, 329, 86, "#e1eeea")
    label(428, 228, "local", "node")
    label(428, 255, "child", "detail")
    rect(408, 309, 329, 108, "#e1eeea")
    label(428, 344, "linux", "node")
    label(428, 372, "ssh", "detail")
    label(428, 397, "process", "detail")

    # Nested box denotes a container inside the remote Docker host.
    rect(408, 448, 329, 173, "#eef4ef", "#96aea6")
    label(428, 483, "host", "node")
    path("M442 494v24", "ctrl", True)
    label(462, 512, "docker exec", "route")
    rect(427, 526, 291, 78, "#d9e9e2")
    label(445, 558, "docker", "node")
    label(445, 585, "inside", "detail")

    # Only application traffic leaves for the HTTP proxy.
    path("M739 235H794V561H720", "flow")
    path("M739 361H846", "flow", True)
    svg.append('<circle cx="794" cy="361" r="4.5" fill="#137568"/>')
    rect(857, 312, 223, 97, "#146258")
    label(877, 354, "gateway", "light")
    label(877, 383, "own", "subtle")
    path("M966 412v74", "flow", True)
    rect(857, 498, 223, 95, "#d9eae4")
    label(877, 538, "service", "node")
    label(877, 566, "target", "detail")

    svg.append("</svg>")
    return "\n".join(svg) + "\n"


if __name__ == "__main__":
    for language, labels in LABELS.items():
        (ASSETS / f"architecture.{language}.svg").write_text(diagram(language, labels), encoding="utf-8")
