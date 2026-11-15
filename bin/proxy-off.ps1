# net-proxy-tool: Windows PowerShell session proxy deactivator
# 调用方式: . .\bin\proxy-off.ps1

Remove-Item env:http_proxy -ErrorAction SilentlyContinue
Remove-Item env:https_proxy -ErrorAction SilentlyContinue
Remove-Item env:HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item env:HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item env:all_proxy -ErrorAction SilentlyContinue
Remove-Item env:ALL_PROXY -ErrorAction SilentlyContinue
Remove-Item env:no_proxy -ErrorAction SilentlyContinue
Remove-Item env:NO_PROXY -ErrorAction SilentlyContinue

Write-Host "🛑 [net-proxy-tool] Windows PowerShell 会话代理已注销，环境恢复纯净状态" -ForegroundColor Yellow
