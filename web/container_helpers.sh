#!/bin/sh
# Explicit installation inside the selected container. Use --uninstall to remove it.
set -eu
umask 077
state=/etc/net-proxy-tool-console-helpers
profile=/etc/profile.d/net-proxy-switch.sh
wrapper=/usr/local/bin/with-proxy
case ${1:-install} in install|--uninstall) ;; *) echo 'Expected install or --uninstall.' >&2; exit 2;; esac
if [ -e "$state" ] || [ -L "$state" ]; then
    if [ -L "$state" ] || [ ! -f "$state/owned" ]; then
        echo "Cannot verify ownership of $state." >&2; exit 1
    fi
    for name in profile wrapper; do
        case $name in profile) file=$profile;; wrapper) file=$wrapper;; esac
        if [ -L "$file" ] || ! cmp -s "$file" "$state/$name"; then
            echo "Helper differs from the installed copy: $file" >&2; exit 1
        fi
    done
    if [ "${1:-install}" = --uninstall ]; then
        rm -- "$profile" "$wrapper" "$state/profile" "$state/wrapper" "$state/owned"
        rmdir -- "$state"
        exit 0
    fi
    echo 'Helpers already installed. For a new gateway, uninstall then install again.'
    exit 0
fi
[ "${1:-install}" != --uninstall ] || exit 0
for file in "$profile" "$wrapper"; do
    if [ -e "$file" ] || [ -L "$file" ]; then
        echo "Existing file preserved: $file" >&2; exit 1
    fi
done
mkdir -- "$state"
profile_created=0
wrapper_created=0
cleanup() {
    if [ "$wrapper_created" = 1 ]; then rm -f -- "$wrapper"; fi
    if [ "$profile_created" = 1 ]; then rm -f -- "$profile"; fi
    rm -f -- "$state/profile" "$state/wrapper" "$state/owned"
    rmdir -- "$state"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
cat > "$state/profile" <<'NPT_PROFILE'
@FUNCTIONS@
alias proxy-on=npt_proxy_on
alias proxy-off=npt_proxy_off
alias proxy-status='printf "%s\n" "Session switch active: ${__npt_session_active:-0}"'
NPT_PROFILE
cat > "$state/wrapper" <<'NPT_WRAPPER'
#!/bin/sh
export HTTP_PROXY=@PROXY@ HTTPS_PROXY=@PROXY@ http_proxy=@PROXY@ https_proxy=@PROXY@
export NO_PROXY=@BYPASS@ no_proxy=@BYPASS@
exec "$@"
NPT_WRAPPER
# Noclobber reserves each path before writing it. Keep independent copies for removal checks.
(set -C; : > "$profile")
profile_created=1
cat "$state/profile" > "$profile"
chmod 644 "$profile"
(set -C; : > "$wrapper")
wrapper_created=1
cat "$state/wrapper" > "$wrapper"
chmod 755 "$wrapper"
: > "$state/owned"
trap - EXIT HUP INT TERM
echo "Helpers installed. Open a new login shell or source $profile."
