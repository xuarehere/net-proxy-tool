@echo off
rem net-proxy-tool: Start standalone web console (Windows)
cd /d "%~dp0"
echo ==================================================
echo  正在启动 net-proxy-tool 独立 Web 控制台 (Windows)...
echo ==================================================
start "NetProxyTool-WebConsole" python server.py
timeout /t 2 >nul
echo.
echo 浏览器正在打开: http://localhost:8899
start http://localhost:8899
