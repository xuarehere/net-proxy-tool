@echo off
rem Run a project script with the bundled runtime or a verified Python 3.
setlocal
if exist "%~dp0runtime\python.exe" goto bundled
py -3 -c "import sys; sys.exit(sys.version_info[:2] < (3,8))" >nul 2>&1
if not errorlevel 1 goto pylauncher
python -c "import sys; sys.exit(sys.version_info[:2] < (3,8))" >nul 2>&1
if not errorlevel 1 goto python
echo Python 3.8+ is required for the source ZIP. 1>&2
echo Download the Windows portable ZIP from GitHub Releases, or install Python and retry. 1>&2
exit /b 1
:bundled
"%~dp0runtime\python.exe" %*
exit /b %errorlevel%
:pylauncher
py -3 %*
exit /b %errorlevel%
:python
python %*
exit /b %errorlevel%
