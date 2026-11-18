# POSIX shell functions used by the downloadable session and container helpers.
npt_proxy_on() {
    if [ "${__npt_session_active-}" != 1 ]; then
        for __npt_key in HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY no_proxy; do
            eval "__npt_had_$__npt_key=\${${__npt_key}+yes}"
            eval "__npt_old_$__npt_key=\${${__npt_key}-}"
            if export -p | grep -Eq "^(export |declare -x )${__npt_key}(=|$)"; then
                eval "__npt_export_$__npt_key=yes"
            else
                eval "__npt_export_$__npt_key=no"
            fi
        done
    fi
    __npt_session_active=1
    export HTTP_PROXY=@PROXY@ HTTPS_PROXY=@PROXY@ http_proxy=@PROXY@ https_proxy=@PROXY@
    export NO_PROXY=@BYPASS@ no_proxy=@BYPASS@
    unset __npt_key
}
npt_proxy_off() {
    [ "${__npt_session_active-}" = 1 ] || return 0
    for __npt_key in HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY no_proxy; do
        eval "__npt_had=\${__npt_had_${__npt_key}-}"
        eval "__npt_export=\${__npt_export_${__npt_key}-}"
        unset "$__npt_key"
        if [ "$__npt_had" = yes ]; then
            eval "${__npt_key}=\${__npt_old_${__npt_key}}"
            if [ "$__npt_export" = yes ]; then export "$__npt_key"; fi
        fi
        unset "__npt_had_$__npt_key" "__npt_old_$__npt_key" "__npt_export_$__npt_key"
    done
    unset __npt_had __npt_export __npt_key __npt_session_active
}
