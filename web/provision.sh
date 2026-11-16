# Embedded into the script sent to the selected POSIX node.
set -eu
umask 077
state="$HOME/.local/state/net-proxy-tool"
if [ "$action" = off ] && [ ! -d "$state" ]; then
    if [ -e "$HOME/.net-proxy-switch.sh" ]; then
        echo "Legacy proxy settings have no backup. Review the v1.3 settings on this node before removing them." >&2
        exit 1
    fi
    exit 0
fi
mkdir -p "$state"
mkdir "$state/lock" || { echo "Another switch is in progress ($state/lock)." >&2; exit 1; }
trap 'rmdir "$state/lock"' EXIT

# Each snapshot belongs to one exact path. Never restore over an operator edit.
manage() {
    key=$1 file=$2 kind=$3
    dir="$state/$key"
    if [ "$action" = off ] && [ ! -d "$dir" ]; then return; fi
    if [ -L "$file" ] || { [ -e "$file" ] && [ ! -f "$file" ]; }; then
        echo "Refusing to replace non-regular file: $file" >&2; exit 1
    fi
    if [ -e "$dir/applied" ] && ! cmp -s "$file" "$dir/applied"; then
        echo "Edited since activation: $file. Original snapshot: $dir" >&2; exit 1
    fi
    if [ "$action" = off ]; then
        if [ -f "$dir/original" ]; then cp -p "$dir/original" "$file"; else rm -f "$file"; fi
        rm -f "$dir/original" "$dir/applied" "$dir/absent" "$dir/next"
        rmdir "$dir"
        return
    fi
    mkdir -p "$dir" "$(dirname "$file")"
    if [ ! -e "$dir/original" ] && [ ! -e "$dir/absent" ]; then
        if [ -f "$file" ]; then cp -p "$file" "$dir/original"; else : > "$dir/absent"; fi
    fi
    next="$dir/next"
    if [ -f "$dir/original" ]; then cp -p "$dir/original" "$next"; else : > "$next"; fi
    case "$kind" in
        curl) printf '\nproxy = "%s"\nnoproxy = "%s"\n' "$proxy" "$bypass" >> "$next" ;;
        wget) printf '\nhttp_proxy = %s\nhttps_proxy = %s\n' "$proxy" "$proxy" >> "$next" ;;
        apt) printf '\nAcquire::http::Proxy "%s";\nAcquire::https::Proxy "%s";\n' "$proxy" "$proxy" >> "$next" ;;
        git) git config --file "$next" --replace-all http.proxy "$proxy"
             git config --file "$next" --replace-all https.proxy "$proxy" ;;
        pip) awk -v proxy="$proxy" '
             /^[[:space:]]*\[/ {
                 section=tolower($0)
                 global=(section ~ /^[[:space:]]*\[global\][[:space:]]*$/)
                 if (global) { print; print "proxy = " proxy; found=1; next }
             }
             global && /^[[:space:]]*[Pp][Rr][Oo][Xx][Yy][[:space:]]*[:=]/ {next}
             {print}
             END {if (!found) print "\n[global]\nproxy = " proxy}
             ' "$next" > "$dir/pip.tmp"
             cat "$dir/pip.tmp" > "$next"; rm -f "$dir/pip.tmp" ;;
        env) printf 'export HTTP_PROXY="%s" HTTPS_PROXY="%s" http_proxy="%s" https_proxy="%s"\nexport NO_PROXY="%s" no_proxy="%s"\n' "$proxy" "$proxy" "$proxy" "$proxy" "$bypass" "$bypass" > "$next" ;;
        profile) { printf '%s\n' '[ -r "$HOME/.net-proxy-switch.sh" ] && . "$HOME/.net-proxy-switch.sh"'
                   if [ -f "$dir/original" ]; then cat "$dir/original"; fi; } > "$next" ;;
    esac
    cp -p "$next" "$file"
    mv "$next" "$dir/applied"
}

manage curlrc "$HOME/.curlrc" curl
manage wgetrc "$HOME/.wgetrc" wget
manage pip "$HOME/.config/pip/pip.conf" pip
if command -v git >/dev/null 2>&1; then manage git "$HOME/.gitconfig" git; fi
manage env "$HOME/.net-proxy-switch.sh" env
for name in .bashrc .profile .bash_profile; do
    if [ -f "$HOME/$name" ] || [ -d "$state/$name" ]; then manage "$name" "$HOME/$name" profile; fi
done
if [ "$(id -u)" = 0 ]; then
    manage system-curl /etc/curlrc curl
    manage system-pip /etc/pip.conf pip
    if command -v git >/dev/null 2>&1; then manage system-git /etc/gitconfig git; fi
    if [ -d /etc/apt/apt.conf.d ]; then manage apt /etc/apt/apt.conf.d/99net-proxy apt; fi
fi
