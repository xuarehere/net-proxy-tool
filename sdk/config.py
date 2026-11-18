"""Shared on-disk configuration and gateway selection for every entry point."""
import ipaddress
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
VERSION = "1.4.2"
DEFAULT_TEST_URL = "https://www.google.com/"
NO_PROXY = "localhost,127.0.0.1,::1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,*.local"
# Both tables shipped in v1.4.1: generated settings used the site name as
# description, while config.example.json contained translated descriptions.
# Compare the complete table before upgrading, including user-edited metadata.
_LEGACY_SITES = {
    "Google": ("https://www.google.com", "全球互联网基础连通", "基础服务"),
    "GitHub": ("https://github.com", "源码拉取与托管", "研发必备"),
    "Raw GitHub": ("https://raw.githubusercontent.com", "脚本与发行包直连", "研发必备"),
    "HuggingFace": ("https://huggingface.co", "开源 AI 模型权重下载", "AI/大模型"),
    "PyPI": ("https://pypi.org", "Python 官方包索引与依赖", "包管理"),
    "OpenAI API": ("https://api.openai.com", "大语言模型 API 接口", "AI/大模型"),
    "YouTube": ("https://www.youtube.com", "高吞吐流媒体/视音频数据", "多媒体"),
}

TARGETS = {
    "Google": DEFAULT_TEST_URL,
    "Claude": "https://claude.ai/",
    "ChatGPT": "https://chatgpt.com/",
    "YouTube": "https://www.youtube.com/",
    "Gemini": "https://gemini.google.com/",
    **{name: spec[0] for name, spec in _LEGACY_SITES.items() if name not in ("Google", "YouTube")},
}


def diagnostic_defaults(saved=None):
    targets = {name: {"url": url, "desc": name, "category": "HTTPS"} for name, url in TARGETS.items()}
    if saved is None:
        return targets
    old_example = {name: {"url": url, "desc": desc, "category": category}
                   for name, (url, desc, category) in _LEGACY_SITES.items()}
    old_generated = {name: {"url": data["url"], "desc": name, "category": "HTTPS"}
                     for name, data in old_example.items()}
    if saved != old_example and saved != old_generated:
        return saved
    for name, data in saved.items():
        targets[name] = dict(data, url=TARGETS[name])
    return targets


def config_path():
    override = os.environ.get("NET_PROXY_CONFIG")
    if override:
        return Path(override).expanduser().resolve()
    legacy = ROOT / "config.json"
    if legacy.is_file():
        return legacy
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "net-proxy-tool" / "config.json"


def data_dir():
    return config_path().parent / "data"


def atomic_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".net-proxy-", delete=False) as stream:
        name = stream.name
        try:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            stream.close()
            os.unlink(name)
            raise
    try:
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _validated(cfg):
    if not isinstance(cfg, dict):
        raise ValueError("expected a JSON object")
    for key in ("gateways", "clients"):
        if not isinstance(cfg.get(key, []), list) or any(not isinstance(v, dict) for v in cfg.get(key, [])):
            raise ValueError(f"{key} must be an array of objects")
    port = int(cfg.get("web_port", 8899))
    if not 0 < port < 65536:
        raise ValueError("web_port must be between 1 and 65535")
    return cfg


def load_config():
    path = config_path()
    cfg = {"version": VERSION, "active_gateway_id": "", "gateways": [], "clients": [],
           "web_port": 8899, "no_proxy": NO_PROXY,
           "diagnostic_targets": diagnostic_defaults()}
    try:
        with path.open(encoding="utf-8-sig") as stream:
            stored = _validated(json.load(stream))
            cfg.update(stored)
            if "diagnostic_targets" in stored:
                cfg["diagnostic_targets"] = diagnostic_defaults(stored["diagnostic_targets"])
    except FileNotFoundError:
        return cfg
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError(f"Cannot read {path}: {exc}. Repair the JSON file and retry.") from exc
    if not cfg["gateways"] and cfg.get("proxy_host"):
        cfg["gateways"] = [{"id": "legacy", "name": "Legacy gateway", "host": cfg["proxy_host"],
                            "port": int(cfg.get("proxy_port", 7890)), "protocol": "http", "is_default": True}]
        cfg["active_gateway_id"] = "legacy"
    return cfg


def save_config(cfg):
    atomic_json(config_path(), _validated(cfg))


def resolve_gateway_info(cfg, gateway_id=None):
    gateways = cfg.get("gateways", [])
    wanted = gateway_id or cfg.get("active_gateway_id")
    for gateway in gateways:
        if gateway.get("id") == wanted:
            return gateway
    if gateway_id:
        return {}
    return next((g for g in gateways if g.get("is_default")), gateways[0] if gateways else {})


def resolve_gateway(cfg, gateway=None):
    override = gateway or os.environ.get("NET_PROXY_GATEWAY")
    info = resolve_gateway_info(cfg, override)
    if info:
        host, port = info["host"], int(info["port"])
    elif override:
        try:
            ipaddress.IPv6Address(override)
        except ValueError:
            address = urlsplit("//" + override)
            if address.username or address.password or address.path or address.query or address.fragment:
                raise ValueError("Expected a gateway ID or host:port")
            host, port = address.hostname, address.port if address.port is not None else 7890
        else:
            host, port = override, 7890
    else:
        raise ValueError("Add a gateway in the Web console or pass --gateway HOST:PORT.")
    if not host or not re.fullmatch(r"[\w.:%-]+", str(host)) or not 0 < port < 65536:
        raise ValueError("Invalid gateway host or port")
    return host, port


def proxy_environment(cfg, host, port):
    address = f"[{host}]" if ":" in host else host
    url = f"http://{address}:{port}"
    values = {"http_proxy": url, "https_proxy": url, "all_proxy": url,
              "no_proxy": cfg.get("no_proxy", NO_PROXY)}
    return dict(values, **{key.upper(): value for key, value in values.items()})
