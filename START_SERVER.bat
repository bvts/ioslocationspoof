@echo off
title LocationControl Companion Server
echo ========================================================
echo       LocationControl PC Companion Server
echo ========================================================
echo.
echo Your PC IP Address is: 192.168.1.93
echo In the iPhone app, set Companion API URL to:
echo     http://192.168.1.93:8765
echo.
echo Make sure your iPhone is connected via USB and unlocked.
echo.
echo Starting server on http://0.0.0.0:8765 ...
echo ========================================================
cd /d "%~dp0pc-controller"
python -m locationctl serve
pause
