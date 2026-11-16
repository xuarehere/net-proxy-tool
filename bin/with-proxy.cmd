@echo off
call "%~dp0..\runtime-select.cmd" "%~dp0..\with_proxy.py" %*
exit /b %errorlevel%
