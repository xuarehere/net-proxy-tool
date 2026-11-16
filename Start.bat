@echo off
setlocal
call "%~dp0runtime-select.cmd" "%~dp0launcher.py" %*
set "rc=%errorlevel%"
if not "%rc%"=="0" pause
exit /b %rc%
