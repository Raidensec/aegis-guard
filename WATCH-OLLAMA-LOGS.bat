@echo off
setlocal
title Aegis Guard Ollama Live Logs
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0scripts\watch-ollama-logs.ps1"

set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
  echo Ollama log watcher finished.
) else (
  echo Ollama log watcher failed with exit code %EXIT_CODE%.
)
echo.
pause
exit /b %EXIT_CODE%
