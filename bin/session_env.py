"""Render the selected gateway for shell integrations without parsing config in shell."""
import json
from pathlib import Path
import shlex
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sdk.config import load_config, proxy_environment, resolve_gateway


def main():
    cfg = load_config()
    values = proxy_environment(cfg, *resolve_gateway(cfg))
    if sys.argv[1:] == ["--json"]:
        print(json.dumps(values, ensure_ascii=True))
    else:
        for key, value in values.items():
            print(f"export {key}={shlex.quote(value)}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
