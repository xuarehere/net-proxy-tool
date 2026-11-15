@echo off
rem net-proxy-tool: Windows CMD Ephemeral Proxy Runner
if "%~1"=="" (
    echo net-proxy-tool: Windows CMD 按需代理沙箱执行器
    echo 用法: bin\with-proxy.cmd ^<命令^> [参数...]
    echo 示例: bin\with-proxy.cmd curl.exe -I https://www.google.com
    exit /b 1
)

set SCRIPT_DIR=%~dp0
python "%SCRIPT_DIR%..\with_proxy.py" %*
exit /b %ERRORLEVEL%
