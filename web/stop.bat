@echo off
rem net-proxy-tool: Stop standalone web console (Windows)
echo 正在停止 net-proxy-tool Web 控制台进程...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8899" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo 已终止端口 8899 占用进程 PID: %%a
)
echo Web 控制台已停止。
