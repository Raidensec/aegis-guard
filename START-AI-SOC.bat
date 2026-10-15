@echo off
setlocal

title Aegis Guard One-Click Startup

cd /d "%~dp0"

echo.
echo ========================================================
echo    Aegis Guard One-Click Startup
echo ========================================================
echo.
echo This will start Docker Desktop if needed, start the
echo Wazuh + Aegis Guard services, start Juice Shop, start the dashboard, and open:
echo.
echo    http://localhost:5050
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-ai-soc-full.ps1"

echo.
echo Press any key to close this window.
pause >nul
