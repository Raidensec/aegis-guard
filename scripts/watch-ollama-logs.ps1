param(
    [string]$ContainerName = "ollama",
    [string]$OutputRoot = "outputs\ollama-logs",
    [string]$Since = "10m"
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$outputDir = Join-Path $projectRoot $OutputRoot
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $outputDir "ollama-$timestamp.log"

Write-Host "Aegis Guard Ollama live log watcher" -ForegroundColor Cyan
Write-Host "Container: $ContainerName"
Write-Host "Saving to : $logFile"
Write-Host "Press Ctrl+C to stop following logs." -ForegroundColor Yellow
Write-Host ""

$container = docker ps --filter "name=^/$ContainerName$" --format "{{.Names}}"
if (-not $container) {
    throw "Container '$ContainerName' is not running. Start Aegis Guard first, then run this file again."
}

docker logs --since $Since --timestamps --follow $ContainerName 2>&1 |
    Tee-Object -FilePath $logFile -Append
