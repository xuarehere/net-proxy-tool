"""Read-only account baselines, collected in a separate, real login shell.

No proxy value, configuration body or shell output is returned. Fingerprints are
used for equality only; a restored baseline may intentionally still use a proxy.
The injected runner is the same saved-identity transport as provisioning.
"""
import secrets
import shlex


PROXY_KEYS = ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
              'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY')


_PROBE = r'''
unset HISTFILE
if [ -n "${BASH_VERSION-}" ]; then set +o history; fi
set -eu
tag=__TAG__
selected=__SELECTED__
emit() { printf '%s\t%s\t%s\n' "$tag" "$1" "$2"; }
hex() { od -An -tx1 | tr -d ' \n'; }
digest() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then shasum -a 256 | awk '{print $1}'
    else return 1; fi
}
metadata() {
    stat -c '%a:%u:%g' "$1" 2>/dev/null || stat -f '%Lp:%u:%g' "$1"
}
record() {
    r_key=$1 r_path=$2
    r_hex=$(printf '%s' "$r_path" | hex)
    if [ -L "$r_path" ]; then emit "$r_key" "$r_hex|unsupported"; return; fi
    if [ ! -e "$r_path" ]; then emit "$r_key" "$r_hex|absent"; return; fi
    if [ ! -f "$r_path" ] || [ ! -r "$r_path" ]; then emit "$r_key" "$r_hex|unreadable"; return; fi
    r_hash=$(digest < "$r_path") || exit 1
    emit "$r_key" "$r_hex|present|$(metadata "$r_path")|$r_hash"
}
emit uid "$(id -u)"
emit user "$(id -un | hex)"
emit home "$(printf '%s' "$HOME" | hex)"
emit shell "$(printf '%s' "$NPT_BASELINE_SHELL" | hex)"
for key in http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY no_proxy NO_PROXY; do
    eval 'present=${'"$key"'+yes}'
    if [ "$present" != yes ]; then emit "env.$key" absent; continue; fi
    eval 'value=${'"$key"'}'
    hash=$(printf '%s' "$value" | digest)
    endpoint=${value#*://}; endpoint=${endpoint##*@}; endpoint=${endpoint%%/*}
    matches=false
    if [ -n "$selected" ] && [ "$endpoint" = "$selected" ]; then matches=true; fi
    emit "env.$key" "present|$hash|$matches"
done
curl_file="$HOME/.curlrc"
if [ -n "${CURL_HOME-}" ] && [ -r "$CURL_HOME/.curlrc" ]; then curl_file="$CURL_HOME/.curlrc"
elif [ -n "${XDG_CONFIG_HOME-}" ] && [ -r "$XDG_CONFIG_HOME/curlrc" ]; then curl_file="$XDG_CONFIG_HOME/curlrc"; fi
case "$curl_file" in /*) ;; *) curl_file="$(pwd)/$curl_file" ;; esac
record curl "$curl_file"
for file in "$HOME/.curlrc" "$HOME/.wgetrc" "$HOME/.gitconfig" "$HOME/.config/pip/pip.conf" \
    "$HOME/.net-proxy-switch.sh" "$HOME/.bashrc" "$HOME/.profile" "$HOME/.bash_profile" "$HOME/.bash_login"; do record file "$file"; done
case "$NPT_BASELINE_SHELL" in */zsh) record file "${ZDOTDIR:-$HOME}/.zprofile" ;; esac
if [ "$(id -u)" = 0 ]; then
    for file in /etc/pip.conf /etc/gitconfig; do record file "$file"; done
    if [ -d /etc/apt/apt.conf.d ]; then record file /etc/apt/apt.conf.d/99net-proxy; fi
fi
state="$HOME/.local/state/net-proxy-tool"
emit state_exists "$([ -d "$state" ] && echo true || echo false)"
if [ -L "$state" ]; then emit unsafe_state true; exit 0; fi
if [ -d "$state" ]; then emit state_metadata "$(metadata "$state")"; fi
for name in owner-uid owner-node-id snapshot-id; do record statefile "$state/$name"; done
if [ -f "$state/owner-uid" ]; then emit owner_uid "$(cat "$state/owner-uid")"; fi
if [ -f "$state/snapshot-id" ]; then emit snapshot_id "$(cat "$state/snapshot-id")"; fi
if [ -f "$state/owner-node-id" ]; then emit owner_node_id "$(cat "$state/owner-node-id")"; fi
if [ -d "$state/lock" ]; then emit locked true; fi
for key in curlrc curl-active wgetrc pip git env .bashrc .profile .bash_profile .bash_login zprofile system-curl system-pip system-git apt; do
    dir="$state/$key"
    [ -d "$dir" ] || continue
    emit "statedir.$key" "$(metadata "$dir")"
    for name in path original absent applied next; do record staterecord "$dir/$name"; done
    if [ ! -f "$dir/path" ]; then
        for marker in applied original absent next; do
            if [ -e "$dir/$marker" ]; then emit incomplete "$key"; break; fi
        done
        continue
    fi
    file=$(cat "$dir/path")
    case "$file" in /*) ;; *) emit incomplete "$key"; continue ;; esac
    record current "$file"
    if [ -f "$dir/original" ] && [ -f "$dir/absent" ]; then emit incomplete "$key"; continue; fi
    if [ -f "$dir/original" ]; then
        record "original.$key" "$dir/original"
        emit "path.$key" "$(printf '%s' "$file" | hex)"
    elif [ -f "$dir/absent" ]; then
        emit "absent.$key" "$(printf '%s' "$file" | hex)"
    else
        if [ -f "$dir/applied" ] || [ -f "$dir/next" ]; then emit incomplete "$key"; fi
        continue
    fi
    if [ -f "$dir/applied" ]; then
        if cmp -s "$file" "$dir/applied" && [ "$(metadata "$file")" = "$(metadata "$dir/applied")" ]; then emit applied "$key"
        else emit conflict "$key"; fi
    else emit prepared "$key"; fi
done
emit complete true
'''


def _script(tag, gateway, extra_paths=()):
    endpoint = ''
    if gateway and gateway.get('host') and gateway.get('port'):
        host = str(gateway['host'])
        endpoint = ('[' + host + ']' if ':' in host else host) + ':' + str(int(gateway['port']))
    inner = _PROBE.replace('__TAG__', shlex.quote(tag)).replace('__SELECTED__', shlex.quote(endpoint))
    extra = '\n'.join('record file ' + shlex.quote(path) for path in extra_paths)
    inner = inner.replace('emit complete true', extra + '\nemit complete true')
    return wrap_login_script(inner)


def wrap_login_script(script):
    """Use the same account startup context for inspection and mutation."""
    # No config is sourced by the wrapper itself. The account's actual login
    # shell loads its normal startup files, including system profile.d.
    # Run the fixed POSIX operation after startup, in /bin/sh: zsh's default
    # NOMATCH and array semantics must not change the restoration algorithm.
    operation = 'unset HISTFILE\nexec /bin/sh -c ' + shlex.quote(script)
    return r'''unset HISTFILE
HISTFILE=/dev/null
export HISTFILE
uid=$(id -u)
shell=''
if command -v getent >/dev/null 2>&1; then shell=$(getent passwd "$uid" | awk -F: '{print $7; exit}'); fi
if [ -z "$shell" ]; then shell=$(awk -F: -v uid="$uid" '$3 == uid {print $7; exit}' /etc/passwd); fi
if [ -z "$shell" ] && command -v dscl >/dev/null 2>&1; then
    shell=$(dscl . -read "/Users/$(id -un)" UserShell | awk '{print $2}')
fi
case "$shell" in */bash|*/sh|*/dash|*/ash|*/zsh|*/ksh) ;; *) exit 78 ;; esac
NPT_BASELINE_SHELL=$shell
export NPT_BASELINE_SHELL
exec "$shell" -lic ''' + shlex.quote(operation) + '\n'


def _decode(value):
    return bytes.fromhex(value).decode('utf-8', 'replace')


def _file(value):
    parts = value.split('|')
    result = {'path': _decode(parts[0]), 'status': parts[1]}
    if parts[1] == 'present':
        mode, uid, gid = parts[2].split(':')
        if len(parts[3]) != 64 or any(c not in '0123456789abcdef' for c in parts[3]):
            raise ValueError('missing file fingerprint')
        result.update(mode=mode, uid=int(uid), gid=int(gid), fingerprint=parts[3])
    return result


def capture_node_baseline(target, runner, gateway=None, *, _extra_paths=()):
    """Capture a fresh login context, never treating missing output as success."""
    tag = 'NPT_BASELINE_' + secrets.token_hex(12)
    try:
        result = runner(target, _script(tag, gateway, _extra_paths), timeout=20)
        if result.returncode:
            return {'ok': False, 'error': 'login_probe_failed', 'returncode': result.returncode,
                    'managed': {'state': 'unknown'}}
        rows = []
        for line in result.stdout.splitlines():
            parts = line.split('\t', 2)
            if len(parts) == 3 and parts[0] == tag:
                rows.append((parts[1], parts[2]))
        values = dict(rows)
        if values.get('complete') != 'true':
            raise ValueError('incomplete')
        identity = {'uid': int(values['uid']), 'user': _decode(values['user']),
                    'home': _decode(values['home']), 'shell': _decode(values['shell'])}
        env = {}
        for key in PROXY_KEYS:
            parts = values['env.' + key].split('|')
            env[key] = {'present': parts[0] == 'present'}
            if env[key]['present']:
                if len(parts[1]) != 64 or any(c not in '0123456789abcdef' for c in parts[1]):
                    raise ValueError('missing environment fingerprint')
                env[key].update(fingerprint=parts[1], matches_selected_gateway=parts[2] == 'true')
        files = {_file(value)['path']: _file(value) for key, value in rows if key in ('file', 'current')}
        curl = _file(values['curl'])
        files[curl['path']] = curl
        restoration = {}
        for key, value in rows:
            if key.startswith('original.'):
                item = _file(value)
                item['path'] = _decode(values['path.' + key.partition('.')[2]])
                restoration[item['path']] = item
            elif key.startswith('absent.'):
                path = _decode(value)
                restoration[path] = {'path': path, 'status': 'absent'}
        state = 'disabled'
        if values.get('unsafe_state') or values.get('locked') or 'incomplete' in values:
            state = 'unknown'
        elif 'conflict' in values:
            state = 'conflict'
        elif 'prepared' in values:
            state = 'partial'
        elif 'applied' in values:
            state = 'enabled'
        owner = values.get('owner_uid')
        if owner and int(owner) != identity['uid']:
            state = 'conflict'
        return {'ok': True, 'version': 1, 'execution_identity': identity,
                'login': {'context': 'fresh_login_shell', 'proxy_variables': env, 'curl': curl},
                'files': files,
                'state_baseline': {'exists': values.get('state_exists') == 'true',
                                   'metadata': values.get('state_metadata'),
                                   'files': {_file(v)['path']: _file(v) for k, v in rows if k == 'statefile'},
                                   'records': {_file(v)['path']: _file(v) for k, v in rows if k == 'staterecord'},
                                   'directories': {k: v for k, v in rows if k.startswith('statedir.')}},
                'managed': {'state': state, 'owner_uid': int(owner) if owner else None,
                            'snapshot_id': values.get('snapshot_id'),
                            'owner_node_id': values.get('owner_node_id'),
                            'restoration_manifest': restoration}}
    except Exception:
        # Transport diagnostics belong to the existing authentication layer.
        # Shell stderr can contain operator secrets, so never return it here.
        return {'ok': False, 'error': 'login_probe_unavailable', 'managed': {'state': 'unknown'}}


def inspect_node_state(target, runner, gateway=None):
    return capture_node_baseline(target, runner, gateway)


def verify_node_baseline(target, baseline, runner, gateway=None):
    """Compare observations; HTTP reachability never proves restoration."""
    old_managed = (baseline or {}).get('managed', {})
    previous_active = old_managed.get('state') in ('enabled', 'partial', 'conflict')
    expected = old_managed.get('restoration_manifest', {}) if previous_active else (baseline or {}).get('files', {})
    observation = capture_node_baseline(target, runner, gateway, _extra_paths=tuple(expected))
    unknown = {'verified': False, 'status': 'unknown', 'verification_scope': 'unavailable',
               'checks': {}, 'observation': observation}
    if not baseline or not baseline.get('ok') or not observation.get('ok'):
        return unknown
    if not expected:
        return unknown
    checks = {'identity': baseline['execution_identity'] == observation['execution_identity'],
              'managed_files': all(observation['files'].get(path) == expected_file
                                   for path, expected_file in expected.items()),
              'managed_disabled': observation['managed']['state'] == 'disabled'}
    scope = 'managed_files_only' if previous_active else 'login_and_managed_files'
    if not previous_active:
        def comparable_env(value):
            return {key: {k: v for k, v in item.items() if k != 'matches_selected_gateway'}
                    for key, item in value['login']['proxy_variables'].items()}
        checks['proxy_environment'] = comparable_env(baseline) == comparable_env(observation)
        checks['curl_configuration'] = baseline['login']['curl'] == observation['login']['curl']
        checks['state_metadata'] = baseline.get('state_baseline') == observation.get('state_baseline')
    verified = all(checks.values())
    return {'verified': verified, 'status': 'restored' if verified else 'changed',
            'verification_scope': scope, 'checks': checks, 'observation': observation}
