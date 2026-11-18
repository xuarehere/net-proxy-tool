"""Fixed, bounded curl diagnostics; never accepts a command from a request."""
import getpass
import os
from pathlib import Path
import re
import shlex
import urllib.parse


def validate_url(value):
    if not isinstance(value, str) or len(value) > 8192 or re.search(r'[\x00-\x20\x7f]', value):
        raise ValueError('目标 URL 包含空白、控制字符或过长')
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError('目标必须是无凭据的 HTTP 或 HTTPS URL')
    if parsed.port is not None and not 0 < parsed.port < 65536:
        raise ValueError('目标端口无效')
    return urllib.parse.urlunsplit(parsed._replace(fragment=''))


def curl_command(executable, url, proxy=None, timeout=20, output='/dev/null', headers='__NPT_HEADERS__'):
    command = [executable]
    if proxy:
        command += ['-q', '--proxy', proxy, '--noproxy', '']
    metrics = {'CODE': 'http_code', 'IP': 'remote_ip', 'PORT': 'remote_port', 'CONNECT': 'http_connect',
               'VERIFY': 'ssl_verify_result', 'TLS_TIME': 'time_appconnect',
               'FINAL_URL': 'url_effective', 'REDIRECT_COUNT': 'num_redirects'}
    write_out = '\n' + '\n'.join('NPT_' + name + ':%{' + value + '}' for name, value in metrics.items()) + '\n'
    protocols = '=https' if urllib.parse.urlsplit(url).scheme == 'https' else '=http,https'
    # Negating location-trusted also clears curl's follow flag; enable location afterwards.
    return command + ['--request', 'GET', '--no-location-trusted', '--location', '--max-redirs', '5',
                      '--disallow-username-in-url',
                      '--proto-redir', protocols, '--globoff', '--silent', '--show-error',
                      '--suppress-connect-headers', '--dump-header', headers,
                      '--output', output, '--write-out', write_out, '--connect-timeout', str(min(10, timeout)),
                      '--max-time', str(timeout), '--proto', '=http,https', '--url', url]


def safe_url(value):
    """Response-derived URLs never expose userinfo, query tokens, or fragments."""
    try:
        parsed = urllib.parse.urlsplit(value)
        authority = parsed.netloc.rsplit('@', 1)[-1]
        return urllib.parse.urlunsplit(parsed._replace(netloc=authority, query='', fragment=''))
    except ValueError:
        return '<invalid URL>'


def filter_headers(headers):
    kept = []
    for line in headers.splitlines():
        status = re.match(r'^HTTP/\S+\s+(\d{3})\b', line)
        if status:
            kept.append('NPT_HEADER_STATUS:' + status[1])
        elif line.lower().startswith('location:'):
            kept.append('NPT_HEADER_LOCATION:' + safe_url(line.split(':', 1)[1].strip()))
    return '\n'.join(kept) + '\n'


def remote_script(command):
    rendered = ' '.join(map(shlex.quote, command)).replace('__NPT_HEADERS__', '"$npt_tmp/headers"')
    # Only status and Location are transmitted; Set-Cookie/Authorization and other headers stay private.
    return identity_script() + """umask 077
npt_tmp=$(mktemp -d) || exit 1
trap 'rm -f "$npt_tmp/headers"; rmdir "$npt_tmp"' EXIT HUP INT TERM
""" + rendered + r"""
npt_code=$?
if [ -f "$npt_tmp/headers" ]; then
    awk '/^HTTP\// { print "NPT_HEADER_STATUS:" $2 }
         tolower($0) ~ /^location:/ {sub(/^[^:]*:[[:space:]]*/, ""); sub(/\r$/, "");
         sub(/[?#].*$/, ""); sub(/:\/\/[^\/]*@/, "://"); print "NPT_HEADER_LOCATION:" $0}' "$npt_tmp/headers"
fi
exit "$npt_code"
"""


def identity_script():
    # Only names/paths and existence are observed; no config or credential content is read.
    return """printf 'NPT_EXEC_READY\\n'
printf 'NPT_META_UID:%s\\n' "$(id -u)"
printf 'NPT_META_USER:%s\\n' "$(id -un)"
printf 'NPT_META_HOME:%s\\n' "$HOME"
printf 'NPT_META_CURL_HOME:%s\\n' "${CURL_HOME-}"
printf 'NPT_META_XDG_CONFIG_HOME:%s\\n' "${XDG_CONFIG_HOME-}"
npt_curl_config=''
if [ -n "${CURL_HOME-}" ] && [ -r "$CURL_HOME/.curlrc" ]; then npt_curl_config="$CURL_HOME/.curlrc"
elif [ -n "${XDG_CONFIG_HOME-}" ] && [ -r "$XDG_CONFIG_HOME/curlrc" ]; then npt_curl_config="$XDG_CONFIG_HOME/curlrc"
elif [ -r "$HOME/.curlrc" ]; then npt_curl_config="$HOME/.curlrc"; fi
printf 'NPT_META_CURL_CONFIG:%s\\n' "$npt_curl_config"
"""


def local_identity():
    home = os.environ.get('HOME') or str(Path.home())
    candidates = []
    if os.environ.get('CURL_HOME'):
        candidates.append(Path(os.environ['CURL_HOME']) / '.curlrc')
    if os.environ.get('XDG_CONFIG_HOME'):
        candidates.append(Path(os.environ['XDG_CONFIG_HOME']) / 'curlrc')
    candidates.append(Path(home) / '.curlrc')
    if os.name == 'nt':
        for name in ('USERPROFILE', 'APPDATA'):
            if os.environ.get(name):
                candidates.append(Path(os.environ[name]) / '.curlrc')
        candidates = [candidate for p in candidates for candidate in (p, p.with_name('_curlrc'))]
    selected = next((str(p) for p in candidates if p.is_file()), '')
    return {'uid': str(os.getuid()) if hasattr(os, 'getuid') else None, 'user': getpass.getuser(), 'home': home,
            'curl_home': os.environ.get('CURL_HOME', ''), 'xdg_config_home': os.environ.get('XDG_CONFIG_HOME', ''),
            'curl_config': selected}


def parse_output(stdout):
    values = {}
    responses = []
    for line in stdout.splitlines():
        match = re.fullmatch(r'NPT_([A-Z_]+):(.*)', line)
        if match:
            name, value = match[1], match[2][:8192]
            if name == 'HEADER_STATUS' and value.isdigit() and int(value) >= 200:
                responses.append({'code': int(value)})
            elif name == 'HEADER_LOCATION' and responses:
                responses[-1]['location'] = safe_url(value)
            else:
                values[name] = value
    def number(name):
        try:
            return int(values.get(name, ''))
        except ValueError:
            return None
    # Compatibility with old transport fixtures; actual calls use the structured fields above.
    if 'CODE' not in values:
        legacy = re.search(r'^NPT_HTTP_RESULT:(\d{3})\|([^|\r\n]*)\|([0-9.]+)$', stdout, re.MULTILINE)
        if legacy:
            values.update(CODE=legacy[1], IP=legacy[2])
    identity = {key.lower(): value for key, value in ((key[5:], value) for key, value in values.items()
                                                    if key.startswith('META_'))}
    code = number('CODE') or None
    port = number('PORT')
    return {'code': code, 'peer': {'ip': values.get('IP') or None, 'port': port if port and port > 0 else None},
            'connect_status': number('CONNECT') or None, 'ssl_verify_result': number('VERIFY'),
            'tls_time': values.get('TLS_TIME', '0'), 'responses': responses,
            'final_url': safe_url(values.get('FINAL_URL', '')), 'redirect_count': number('REDIRECT_COUNT') or 0,
            'execution_identity': identity, 'metrics_received': 'CODE' in values}


def curl_error(exit_code, connect_status=None):
    if connect_status == 407:
        return 'proxy_auth'
    if exit_code in (51, 58, 60, 77, 83, 90, 91):
        return 'tls_certificate'
    return {2: 'curl_option', 5: 'proxy_dns', 6: 'target_dns', 7: 'connection', 28: 'timeout', 35: 'tls_handshake',
            47: 'redirect_limit', 127: 'curl_missing'}.get(exit_code, 'curl' if exit_code else None)


def ssh_error(stderr):
    text = stderr.lower()
    if any(term in text for term in ('host key verification failed', 'remote host identification has changed')):
        return 'ssh_host_key', 'SSH 主机密钥未受信任或已改变；请核对既有主机信任。'
    if 'permission denied' in text or 'authentication failed' in text:
        return 'ssh_auth', '已保存的 SSH 身份认证失败。'
    if 'ssh_askpass:' in text or 'createprocessw failed' in text:
        return 'ssh_helper', '无法启动 SSH 认证助手；请检查 OpenSSH 和 Python 路径。'
    if any(term in text for term in ('connection refused', 'connection timed out', 'could not resolve', 'no route to host')):
        return 'ssh_connection', 'SSH 连接未建立；请检查目标地址、端口与网络。'
    return 'ssh_transport', 'SSH 会话未进入；请核对已保存身份及主机信任。'
