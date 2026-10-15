@echo off
setlocal

title Aegis Guard Simulation Tests

cd /d "%~dp0"

set "SINGLE_TIMESTEPS=%~1"
set "SWARM_SIZE=%~2"
set "MONTE_CARLO_RUNS=%~3"
set "SWARM_TIMESTEPS=%~4"

if "%SINGLE_TIMESTEPS%"=="" set "SINGLE_TIMESTEPS=3"
if "%SWARM_SIZE%"=="" set "SWARM_SIZE=100"
if "%MONTE_CARLO_RUNS%"=="" set "MONTE_CARLO_RUNS=5"
if "%SWARM_TIMESTEPS%"=="" set "SWARM_TIMESTEPS=6"

echo.
echo ========================================================
echo    Aegis Guard Simulation Tests
echo ========================================================
echo.
echo Single simulation timesteps: %SINGLE_TIMESTEPS%
echo Swarm size:                  %SWARM_SIZE%
echo Monte Carlo runs:            %MONTE_CARLO_RUNS%
echo Swarm timesteps:             %SWARM_TIMESTEPS%
echo.
echo Results will be saved under:
echo   outputs\simulation-tests
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0scripts\run-simulation-tests.ps1" ^
  -SingleTimesteps %SINGLE_TIMESTEPS% ^
  -SwarmSize %SWARM_SIZE% ^
  -MonteCarloRuns %MONTE_CARLO_RUNS% ^
  -SwarmTimesteps %SWARM_TIMESTEPS%

set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
  echo Simulation tests finished successfully.
) else (
  echo Simulation tests failed with exit code %EXIT_CODE%.
)
echo.
echo Press any key to close this window.
pause >nul

exit /b %EXIT_CODE%
