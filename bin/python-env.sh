# Sourced by Bash wrappers via their real location.
npt_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
npt_python="$npt_root/runtime/bin/python3"
if [[ ! -x "$npt_python" ]]; then npt_python=python3; fi
