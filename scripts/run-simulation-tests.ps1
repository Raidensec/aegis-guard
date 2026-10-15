param(
    [int]$SingleTimesteps = 3,
    [int]$SwarmSize = 100,
    [int]$MonteCarloRuns = 5,
    [int]$SwarmTimesteps = 6,
    [string]$BaseUrl = "http://localhost:8600",
    [int]$PollSeconds = 5,
    [int]$MaxWaitMinutes = 45
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutDir = Join-Path $RepoRoot "outputs\simulation-tests\$RunStamp"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "[*] $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Save-Json {
    param(
        [Parameter(Mandatory=$true)] $Object,
        [Parameter(Mandatory=$true)] [string]$FileName
    )

    $path = Join-Path $OutDir $FileName
    $Object | ConvertTo-Json -Depth 80 | Set-Content -Path $path -Encoding UTF8
    return $path
}

function Invoke-JsonRequest {
    param(
        [Parameter(Mandatory=$true)] [string]$Method,
        [Parameter(Mandatory=$true)] [string]$Url,
        [int]$TimeoutSec = 120
    )

    return Invoke-RestMethod -Method $Method -Uri $Url -TimeoutSec $TimeoutSec
}

function Get-PropertyValue {
    param(
        [Parameter(Mandatory=$true)] $Object,
        [Parameter(Mandatory=$true)] [string[]]$Names
    )

    foreach ($name in $Names) {
        if ($null -ne $Object.PSObject.Properties[$name]) {
            return $Object.$name
        }
    }
    return $null
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Blue
Write-Host "   Aegis Guard Simulation Tests" -ForegroundColor Blue
Write-Host "========================================================" -ForegroundColor Blue
Write-Host "Base URL: $BaseUrl"
Write-Host "Output:   $OutDir"
Write-Host "Monitor:  http://localhost:5050/simulation-monitor"

Write-Step "Checking correlation engine health"
$health = Invoke-JsonRequest -Method GET -Url "$BaseUrl/health" -TimeoutSec 20
Save-Json -Object $health -FileName "00-health.json" | Out-Null
Write-Ok "Correlation engine responded"

Write-Step "Running single attack/campaign simulation"
$singleUrl = "$BaseUrl/simulate?timesteps=$SingleTimesteps"
Write-Host "POST $singleUrl"
$singleStarted = Get-Date
$single = Invoke-JsonRequest -Method POST -Url $singleUrl -TimeoutSec 1800
$singlePath = Save-Json -Object $single -FileName "01-single-simulation.json"
$singleDuration = [math]::Round(((Get-Date) - $singleStarted).TotalSeconds, 1)
Write-Ok "Single simulation completed in $singleDuration seconds"
Write-Host "Saved: $singlePath"

Write-Step "Starting swarm simulation"
$swarmStartUrl = "$BaseUrl/simulate/swarm/start?swarm_size=$SwarmSize&monte_carlo_runs=$MonteCarloRuns&timesteps=$SwarmTimesteps"
Write-Host "POST $swarmStartUrl"
$swarmStart = Invoke-JsonRequest -Method POST -Url $swarmStartUrl -TimeoutSec 120
$swarmStartPath = Save-Json -Object $swarmStart -FileName "02-swarm-start.json"
$swarmId = Get-PropertyValue -Object $swarmStart -Names @("swarm_id", "swarmId", "id", "simulation_id", "task_id")

if ([string]::IsNullOrWhiteSpace($swarmId)) {
    Write-Host "Swarm start response:" -ForegroundColor Yellow
    $swarmStart | ConvertTo-Json -Depth 20
    throw "Could not find swarm_id in swarm start response. Saved: $swarmStartPath"
}

Write-Ok "Swarm started: $swarmId"
Write-Host "Saved: $swarmStartPath"

Write-Step "Polling swarm status"
$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
$statusHistory = @()
$lastStatus = $null

while ((Get-Date) -lt $deadline) {
    $statusUrl = "$BaseUrl/simulate/swarm/$swarmId/status"
    try {
        $status = Invoke-JsonRequest -Method GET -Url $statusUrl -TimeoutSec 30
    } catch {
        $status = [pscustomobject]@{
            status = "poll_error"
            error = $_.Exception.Message
        }
    }

    $statusHistory += $status
    $lastStatus = Get-PropertyValue -Object $status -Names @("status")
    if ([string]::IsNullOrWhiteSpace($lastStatus)) {
        $lastStatus = "unknown"
    }

    $batch = Get-PropertyValue -Object $status -Names @("current_batch")
    $total = Get-PropertyValue -Object $status -Names @("total_batches")
    $runs = Get-PropertyValue -Object $status -Names @("total_agent_runs")

    $progressText = "status=$lastStatus"
    if ($null -ne $batch -and $null -ne $total) {
        $progressText += " batch=$batch/$total"
    }
    if ($null -ne $runs) {
        $progressText += " agent_runs=$runs"
    }
    Write-Host "  $progressText"

    if ($lastStatus -in @("complete", "completed", "done", "failed")) {
        break
    }

    Start-Sleep -Seconds $PollSeconds
}

$historyPath = Save-Json -Object $statusHistory -FileName "03-swarm-status-history.json"
Write-Host "Saved: $historyPath"

if ($lastStatus -notin @("complete", "completed", "done")) {
    throw "Swarm did not complete within $MaxWaitMinutes minutes. Last status: $lastStatus"
}

Write-Step "Fetching swarm result"
$resultUrl = "$BaseUrl/simulate/swarm/$swarmId/result"
Write-Host "GET $resultUrl"
$swarmResult = Invoke-JsonRequest -Method GET -Url $resultUrl -TimeoutSec 120
$resultPath = Save-Json -Object $swarmResult -FileName "04-swarm-result.json"
Write-Ok "Swarm result fetched"
Write-Host "Saved: $resultPath"

$summary = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    base_url = $BaseUrl
    output_dir = $OutDir
    single_timesteps = $SingleTimesteps
    single_duration_seconds = $singleDuration
    swarm_id = $swarmId
    swarm_size = $SwarmSize
    monte_carlo_runs = $MonteCarloRuns
    swarm_timesteps = $SwarmTimesteps
    final_swarm_status = $lastStatus
    files = @{
        health = "00-health.json"
        single = "01-single-simulation.json"
        swarm_start = "02-swarm-start.json"
        swarm_status_history = "03-swarm-status-history.json"
        swarm_result = "04-swarm-result.json"
    }
}

$summaryPath = Save-Json -Object $summary -FileName "summary.json"
Write-Step "Summary"
$summary | ConvertTo-Json -Depth 10
Write-Ok "All simulation tests completed"
Write-Host "Summary saved: $summaryPath"
