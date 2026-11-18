# Embedded into the script sent to the selected POSIX node.
set -eu
umask 077
state="$HOME/.local/state/net-proxy-tool"
case "$HOME" in /*) ;; *) echo 'A non-empty absolute HOME is required.' >&2; exit 1 ;; esac
if [ ! -e "$state/env/applied" ] && {
    grep -qs '^export HTTP_PROXY=' "$HOME/.net-proxy-switch.sh" ||
    grep -qs '^# --- NET-PROXY-TOOL-START ---$' "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile" /etc/bash.bashrc /etc/profile;
}; then
    has_snapshot=false
    for snapshot in "$state"/*/original "$state"/*/absent; do
        if [ -f "$snapshot" ]; then has_snapshot=true; break; fi
    done
    if [ "$action" != on ] && [ "$has_snapshot" = false ]; then
        echo "Legacy v1.3 proxy settings have no managed snapshot. Nothing was changed. Explicitly enable once to preserve the current files as a restoration baseline, or restore manually from your own backups." >&2
        exit 1
    fi
    if [ "$action" = on ]; then
        echo "Legacy v1.3 settings detected. The requested activation will preserve current managed files as the restoration baseline. Disabling restores that baseline, including any existing proxy settings; it does not promise a direct connection."
    fi
fi
if [ "$action" = off ] && [ ! -d "$state" ]; then
    exit 0
fi
mkdir -p "$state"
mkdir "$state/lock" || { echo "Another switch is in progress ($state/lock)." >&2; exit 1; }
trap 'rmdir "$state/lock"' EXIT

# Snapshot paths stay bound to the execution account and the original HOME.
uid=$(id -u)
if [ -f "$state/owner-uid" ] && [ "$(cat "$state/owner-uid")" != "$uid" ]; then
    echo "This snapshot belongs to another execution UID. Use the original account to restore it." >&2
    exit 1
fi

# Curl stops at the first readable configuration in this search order.
curl_file="$HOME/.curlrc"
if [ -n "${CURL_HOME-}" ] && [ -r "$CURL_HOME/.curlrc" ]; then curl_file="$CURL_HOME/.curlrc"
elif [ -n "${XDG_CONFIG_HOME-}" ] && [ -r "$XDG_CONFIG_HOME/curlrc" ]; then curl_file="$XDG_CONFIG_HOME/curlrc"; fi
case "$curl_file" in /*) ;; *) curl_file="$(pwd)/$curl_file" ;; esac
if [ -f "$state/curl-active/path" ]; then
    saved_curl_file=$(cat "$state/curl-active/path")
    if [ "$action" = on ] && [ "$saved_curl_file" != "$curl_file" ]; then
        echo "Curl configuration context changed. Restore the previous activation before switching again." >&2
        exit 1
    fi
    curl_file="$saved_curl_file"
fi

# Each snapshot belongs to one exact path. Never restore over an operator edit.
manage() {
    key=$1 file=$2 kind=$3
    dir="$state/$key"
    if [ "$action" = off ] && [ ! -d "$dir" ]; then return; fi
    if [ -f "$dir/path" ] && [ "$(cat "$dir/path")" != "$file" ]; then
        echo "Snapshot path changed: $file. Restore using the original context." >&2; exit 1
    fi
    if [ -L "$file" ] || { [ -e "$file" ] && [ ! -f "$file" ]; }; then
        echo "Refusing to replace non-regular file: $file" >&2; exit 1
    fi
    if [ -f "$dir/original" ] && [ -f "$dir/absent" ]; then
        echo "Conflicting snapshot records: $dir. Review them before restoring." >&2; exit 1
    fi
    if [ -e "$dir/applied" ]; then
        if [ ! -f "$dir/original" ] && [ ! -f "$dir/absent" ]; then
            echo "Missing restoration baseline: $dir. No overwrite is authorized." >&2; exit 1
        fi
        if ! cmp -s "$file" "$dir/applied" && ! { [ -f "$dir/next" ] && cmp -s "$file" "$dir/next"; }; then
            echo "Edited since activation: $file. Original snapshot: $dir" >&2; exit 1
        fi
    elif { [ -f "$dir/original" ] && ! cmp -s "$file" "$dir/original"; } ||
         { [ -f "$dir/absent" ] && [ -e "$file" ]; }; then
        # A failed preparation can leave snapshots without applied files. Do not
        # mistake a subsequent operator edit for something that we may overwrite.
        if ! { [ -f "$dir/next" ] && cmp -s "$file" "$dir/next"; }; then
            echo "Edited since snapshot preparation: $file. Original snapshot: $dir" >&2; exit 1
        fi
    fi
    if [ "$stage" = check ] && [ "$action" = on ] && [ "$kind" = profile ] && [ -f "$file" ]; then
        # Only complete, exact legacy blocks can be replaced in the applied copy.
        # Reject unmatched/nested markers before any managed file is written.
        if ! awk '
            /^# --- NET-PROXY-TOOL-START ---$/ {if (inside) exit 1; inside=1}
            /^# --- NET-PROXY-TOOL-END ---$/ {if (!inside) exit 1; inside=0}
            END {if (inside) exit 1}
            ' "$file"; then
            echo "Incomplete legacy proxy block: $file. No managed files were changed; review the markers first." >&2
            exit 1
        fi
    fi
    if [ "$stage" = check ]; then return; fi
    if [ "$action" = off ]; then
        # An interrupted snapshot with neither baseline record cannot authorize deletion.
        if [ ! -f "$dir/original" ] && [ ! -f "$dir/absent" ]; then return; fi
        if [ "$stage" = prepare ]; then
            if [ -f "$dir/original" ]; then cp -p "$dir/original" "$dir/restore"; fi
            return
        fi
        if [ -f "$dir/original" ]; then cp -p "$dir/restore" "$file"; else rm -f "$file"; fi
        rm -f "$dir/original" "$dir/applied" "$dir/absent" "$dir/next" "$dir/restore" "$dir/pip.tmp" "$dir/path"
        rmdir "$dir"
        return
    fi
    if [ "$stage" = apply ]; then
        mkdir -p "$(dirname "$file")"
        cp -p "$dir/next" "$file"
        mv "$dir/next" "$dir/applied"
        return
    fi
    mkdir -p "$dir"
    printf '%s\n' "$file" > "$dir/path"
    printf '%s\n' "$uid" > "$state/owner-uid"
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
                   if [ -f "$dir/original" ]; then
                       awk '
                           /^# --- NET-PROXY-TOOL-START ---$/ {inside=1; next}
                           /^# --- NET-PROXY-TOOL-END ---$/ {inside=0; next}
                           !inside {print}
                           ' "$dir/original"
                   fi; } > "$next" ;;
    esac
}

# Every next file must be generated successfully before the first target write.
for stage in check prepare apply; do
    manage curlrc "$HOME/.curlrc" curl
    if [ "$curl_file" != "$HOME/.curlrc" ]; then manage curl-active "$curl_file" curl; fi
    manage wgetrc "$HOME/.wgetrc" wget
    manage pip "$HOME/.config/pip/pip.conf" pip
    if command -v git >/dev/null 2>&1 || [ "$action" = off ]; then manage git "$HOME/.gitconfig" git; fi
    manage env "$HOME/.net-proxy-switch.sh" env
    for name in .bashrc .profile .bash_profile; do
        if [ -f "$HOME/$name" ] || [ -d "$state/$name" ]; then manage "$name" "$HOME/$name" profile; fi
    done
    if [ "$(id -u)" = 0 ]; then
        # Standard curl does not read /etc/curlrc. Only restore/update an old managed snapshot.
        if [ -d "$state/system-curl" ]; then manage system-curl /etc/curlrc curl; fi
        manage system-pip /etc/pip.conf pip
        if command -v git >/dev/null 2>&1 || [ "$action" = off ]; then manage system-git /etc/gitconfig git; fi
        if [ -d /etc/apt/apt.conf.d ]; then manage apt /etc/apt/apt.conf.d/99net-proxy apt; fi
    fi
done
