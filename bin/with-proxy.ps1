# net-proxy-tool: Windows PowerShell Ephemeral Proxy Runner
if (-not $args -or $args.Count -eq 0) {
    Write-Host "net-proxy-tool: Windows PowerShell 按需代理沙箱执行器" -ForegroundColor Yellow
    Write-Host "用法: .\bin\with-proxy.ps1 <命令> [参数...]"
    Write-Host "示例: .\bin\with-proxy.ps1 curl.exe -I https://www.google.com"
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
$PyScript = Join-Path $BaseDir "with_proxy.py"

python $PyScript @args
exit $LASTEXITCODE
