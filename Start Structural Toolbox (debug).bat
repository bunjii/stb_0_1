@echo off
chcp 65001 >nul
title Structural Toolbox (debug)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Run Install_once.bat first.
    pause
    exit /b 1
)

set "LOG=%~dp0stb_gui.log"
echo ========================================
echo  Structural Toolbox - debug mode
echo ========================================
echo  Console: this window
echo  Log file: %LOG%
echo  URL: http://127.0.0.1:8765/
echo  Close this window to stop the server.
echo ========================================
echo.

REM -u = unbuffered stdout; window stays open via cmd /k
cmd /k ""%CD%\.venv\Scripts\python.exe" -u -m stb_cli gui --log-file "%LOG%""
