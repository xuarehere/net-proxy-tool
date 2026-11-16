#!/usr/bin/env bash
set -eu
root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
dest="$HOME/.local/bin"
mkdir -p "$dest"
for entry in with-proxy docker-proxy with-proxy-docker proxy-on proxy-off; do
    wrapper=$(mktemp "$dest/.net-proxy-tool.XXXXXXXX")
    action=exec
    case $entry in proxy-on|proxy-off) action=source ;; esac
    {
        printf '%s\n' '#!/usr/bin/env bash'
        printf '%s %q "$@"\n' "$action" "$root/bin/$entry"
    } > "$wrapper"
    chmod 755 "$wrapper"
    mv -f "$wrapper" "$dest/$entry"
done
printf 'Installed in %s. Add it to PATH. Use "source proxy-on" and "source proxy-off" in Bash.\n' "$dest"
