#!/bin/sh
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec "$root/net-proxy-tool" "$@"
