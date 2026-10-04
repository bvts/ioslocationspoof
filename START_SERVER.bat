@echo off
title LocationControl Companion Server
echo Starting LocationControl PC Companion Server...
echo.
cd /d "%~dp0pc-controller"
python -m locationctl serve
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================================
    echo Server exited with an error.
    echo If Python is missing dependencies, run:
    echo     pip install -r requirements.txt
    echo ========================================================
)
pause
