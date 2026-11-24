"""Print the console configuration with passwords, tokens and node baselines removed.

Uses the same path resolution as the console (NET_PROXY_CONFIG first), and the
same redaction as the /api/config endpoint.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sdk.config import config_path, load_config  # noqa: E402
from web.server import node_public_state, public_data  # noqa: E402


def redacted_view(cfg):
    return public_data(dict(cfg, clients=[node_public_state(node) for node in cfg.get("clients", [])]))


def main():
    try:
        cfg = load_config()
    except ValueError as exc:
        print("redacted_config: {}".format(exc), file=sys.stderr)
        return 1
    print("# " + str(config_path()))
    print(json.dumps(redacted_view(cfg), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
