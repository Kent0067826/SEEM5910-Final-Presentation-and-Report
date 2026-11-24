@echo off
rem DoorFlow live: double-click to start. Needs Python 3 and g++ (how to install: see the top of live.py).
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 live.py %*
  goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
  python live.py %*
  goto end
)
echo Python 3 was not found. Install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH"), then double-click this file again.
:end
pause
