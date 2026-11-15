# net-proxy-tool: Windows PowerShell session proxy activator
# 调用方式: . .\bin\proxy-on.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
$ConfigFile = Join-Path $BaseDir "config.json"

$ProxyHost = "127.0.0.1"
$ProxyPort = 7890
$NoProxy = "localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,*.local"

if (-not (Test-Path $ConfigFile)) {
    $ExampleConfigFile = Join-Path $BaseDir "config.example.json"
    if (Test-Path $ExampleConfigFile) {
        $ConfigFile = $ExampleConfigFile
    }
}

if (Test-Path $ConfigFile) {
    try {
        $json = Get-Content $ConfigFile -Raw | ConvertFrom-Json
        $ag = $json.active_gateway_id
        if ($json.gateways) {
            foreach ($g in $json.gateways) {
                if ($g.id -eq $ag) {
                    $ProxyHost = $g.host
                    $ProxyPort = $g.port
                    break
                }
            }
        }
        if ($json.no_proxy) { $NoProxy = $json.no_proxy }
    } catch {}
}

$ProxyUrl = "http://${ProxyHost}:${ProxyPort}"
$SocksUrl = "socks5://${ProxyHost}:${ProxyPort}"

$env:http_proxy = $ProxyUrl
$env:https_proxy = $ProxyUrl
$env:HTTP_PROXY = $ProxyUrl
$env:HTTPS_PROXY = $ProxyUrl
$env:all_proxy = $SocksUrl
$env:ALL_PROXY = $SocksUrl
$env:no_proxy = $NoProxy
$env:NO_PROXY = $NoProxy

Write-Host "✅ [net-proxy-tool] Windows PowerShell 会话代理已激活: $ProxyUrl" -ForegroundColor Green
