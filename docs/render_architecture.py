"""Regenerate the Chinese and English diagrams with Python's standard library."""

from pathlib import Path
from xml.sax.saxutils import escape

ASSETS = Path(__file__).resolve().parent / "assets"
LABELS = {
    "zh": (
        "代理控制与请求路径", "本地管理", "浏览器", "Web 控制台", "选择网关、测试连通性",
        "应用配置", "CLI / Python SDK", "为应用设置代理环境变量", "SSH / Docker", "配置指定节点或容器",
        "网络请求", "应用进程", "已有代理", "目标服务",
        "实线箭头表示请求经过的路径。虚线表示控制台或命令行配置应用的路径。",
    ),
    "en": (
        "Proxy control and request paths", "Local control", "Browser", "Web console", "Select and test a gateway",
        "Configuration", "CLI / Python SDK", "Set proxy variables for an app", "SSH / Docker", "Configure a node or container",
        "Traffic", "Application", "Existing proxy", "Destination",
        "Solid arrows show network traffic. Dashed arrows show how the console or CLI configures applications.",
    ),
}


def diagram(lang, strings):
    (title, control, browser, console, configure, settings, runner, runner_detail,
     remote, remote_detail, traffic, app, proxy, target, description) = map(escape, strings)

    def label(x, y, value, style, align="start"):
        return f'<text x="{x}" y="{y}" class="{style}" text-anchor="{align}">{value}</text>'

    def box(x, y, width, height, color):
        return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="14" fill="{color}"/>'

    def arrow(path, kind):
        return f'<path d="{path}" class="{kind}" marker-end="url(#{kind})"/>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" lang="{lang}" viewBox="0 0 720 476" role="img" aria-labelledby="title description">
  <title id="title">{title}</title><desc id="description">{description}</desc>
  <defs>
    <marker id="control" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7Z" fill="#496568"/></marker>
    <marker id="traffic" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7Z" fill="#17645b"/></marker>
  </defs>
  <style>
    text {{font-family:system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;fill:#163d40}}
    .title {{font-size:32px;font-weight:700}} .section {{font-size:17px;font-weight:650;fill:#476566}}
    .node {{font-size:22px;font-weight:650}} .detail {{font-size:16px;fill:#39595c}}
    .highlight {{font-size:22px;font-weight:700;fill:#fff}}
    .control,.traffic {{fill:none;stroke-width:2.4}} .control {{stroke:#496568;stroke-dasharray:5 4}} .traffic {{stroke:#17645b}}
  </style>
  <rect width="720" height="476" rx="20" fill="#f8faf7"/>
  {label(32, 53, title, "title")}
  {label(32, 94, control, "section")}
  {box(32, 109, 246, 67, "#e6eeeb")}
  {label(155, 150, browser, "node", "middle")}
  {arrow("M284 142H337", "control")}
  {box(348, 109, 340, 67, "#d7eae7")}
  {label(518, 138, console, "node", "middle")}
  {label(518, 160, configure, "detail", "middle")}
  <path d="M518 178V205H189" class="control"/>
  {arrow("M189 204V234", "control")}
  {arrow("M518 204V234", "control")}
  {label(32, 222, settings, "section")}
  {box(32, 241, 313, 76, "#e6eeeb")}
  {box(364, 241, 324, 76, "#e6eeeb")}
  {label(188, 273, runner, "node", "middle")}
  {label(188, 298, runner_detail, "detail", "middle")}
  {label(526, 273, remote, "node", "middle")}
  {label(526, 298, remote_detail, "detail", "middle")}
  <path d="M526 319V342H116" class="control"/>
  <path d="M188 319V342" class="control"/>
  {arrow("M116 342V379", "control")}
  {label(32, 364, traffic, "section")}
  {box(32, 390, 170, 56, "#d7eae7")}
  {box(264, 390, 190, 56, "#17645b")}
  {box(516, 390, 172, 56, "#d7eae7")}
  {label(117, 426, app, "node", "middle")}
  {label(359, 426, proxy, "highlight", "middle")}
  {label(602, 426, target, "node", "middle")}
  {arrow("M209 418H251", "traffic")}
  {arrow("M461 418H503", "traffic")}
</svg>
'''


if __name__ == "__main__":
    for language, labels in LABELS.items():
        (ASSETS / f"architecture.{language}.svg").write_text(diagram(language, labels), encoding="utf-8")
