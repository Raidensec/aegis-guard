param(
    [switch]$NoBrowser,
    [int]$DockerTimeoutSeconds = 240,
    [int]$HealthTimeoutSeconds = 600
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile = Join-Path $Root ".env"
$SiemCompose = Join-Path $Root "docker-compose\phase1-siem-core-windows.yml"
$AiCompose = Join-Path $Root "docker-compose\ai-services.yml"
$DashboardApp = Join-Path $Root "dashboard\app.py"
$WazuhThreatHuntingPatch = Join-Path $Root "scripts\patch-wazuh-threat-hunting.ps1"
$DashboardUrl = "http://localhost:5050"
$DashboardOut = "C:\tmp\ai-soc-dashboard.out.log"
$DashboardErr = "C:\tmp\ai-soc-dashboard.err.log"
$env:COMPOSE_IGNORE_ORPHANS = "True"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "[*] $Message" -ForegroundColor Cyan
}

function Write-Ok($Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn($Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Test-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-HttpOk($Url, $TimeoutSec = 5) {
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Wait-DockerEngine {
    Write-Step "Checking Docker engine"

    if (-not (Test-Command "docker")) {
        throw "Docker CLI was not found in PATH. Install Docker Desktop first."
    }

    $deadline = (Get-Date).AddSeconds($DockerTimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        try {
            docker version *> $null
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "Docker engine is ready"
                return
            }
        } catch {
            # Keep waiting.
        }

        $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        $isRunning = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
        if (-not $isRunning -and (Test-Path $dockerDesktop)) {
            Write-Warn "Docker Desktop is not running; starting it now..."
            Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
        }

        Start-Sleep -Seconds 5
    }

    throw "Docker engine did not become ready within $DockerTimeoutSeconds seconds."
}

function Invoke-ComposeUp($ComposeFile, $Label) {
    Write-Step "Starting $Label"

    if (-not (Test-Path $ComposeFile)) {
        throw "Compose file not found: $ComposeFile"
    }

    if (-not (Test-Path $EnvFile)) {
        throw ".env not found at $EnvFile. Run deploy-ai-soc.ps1 once or create .env from .env.example."
    }

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $composeOutput = & docker compose --env-file $EnvFile -f $ComposeFile up -d 2>&1
    $composeExitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference

    if ($composeExitCode -ne 0) {
        $composeOutput | ForEach-Object { Write-Host $_ -ForegroundColor Red }
        throw "docker compose failed for $Label"
    }

    Write-Ok "$Label started"
}

function Get-ContainerHealth($Name) {
    try {
        $status = docker inspect --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}no-health{{end}}' $Name 2>$null
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($status)) {
            return "missing|missing"
        }
        return $status.Trim()
    } catch {
        return "missing|missing"
    }
}

function Wait-HealthyContainers {
    param([string[]]$Containers)

    Write-Step "Waiting for containers to become healthy"
    $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        $notReady = @()

        foreach ($container in $Containers) {
            $parts = (Get-ContainerHealth $container).Split("|")
            $state = $parts[0]
            $health = $parts[1]

            if ($state -ne "running") {
                $notReady += "${container}:${state}/${health}"
            } elseif ($health -ne "healthy" -and $health -ne "no-health") {
                $notReady += "${container}:${state}/${health}"
            }
        }

        if ($notReady.Count -eq 0) {
            Write-Ok "All target containers are running and healthy"
            return
        }

        Write-Host ("Waiting: " + ($notReady -join ", ")) -ForegroundColor DarkYellow
        Start-Sleep -Seconds 10
    }

    Write-Warn "Some containers did not report healthy before timeout."
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

function Ensure-PythonDashboardDeps {
    Write-Step "Checking dashboard Python dependencies"

    if (-not (Test-Command "python")) {
        throw "Python was not found in PATH. Install Python 3.10+ and rerun START-AI-SOC.bat."
    }

    python -c "import flask, requests" *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Dashboard Python dependencies are available"
        return
    }

    Write-Warn "Installing dashboard Python dependencies..."
    python -m pip install --quiet flask requests
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Flask/Requests for the dashboard."
    }
    Write-Ok "Dashboard dependencies installed"
}

function Start-Dashboard {
    Write-Step "Starting Aegis Guard dashboard"

    if (Test-HttpOk $DashboardUrl 3) {
        Write-Ok "Dashboard is already running at $DashboardUrl"
        return
    }

    Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
        Where-Object { $_.CommandLine -like "*dashboard/app.py*" } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }

    New-Item -ItemType Directory -Force -Path "C:\tmp" *> $null
    Remove-Item -LiteralPath $DashboardOut, $DashboardErr -ErrorAction SilentlyContinue

    Start-Process `
        -FilePath "python" `
        -ArgumentList "dashboard/app.py" `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $DashboardOut `
        -RedirectStandardError $DashboardErr

    for ($i = 0; $i -lt 20; $i++) {
        if (Test-HttpOk $DashboardUrl 2) {
            Write-Ok "Dashboard is ready at $DashboardUrl"
            return
        }
        Start-Sleep -Seconds 1
    }

    Write-Warn "Dashboard did not answer on $DashboardUrl. Check $DashboardErr"
}

function Invoke-SmokeChecks {
    Write-Step "Running quick smoke checks"

    $checks = [ordered]@{
        "Aegis Guard Dashboard"      = "http://localhost:5050/"
        "Dashboard Incidents"   = "http://localhost:5050/api/incidents/active"
        "Alert Triage"          = "http://localhost:8100/health"
        "RAG Service"           = "http://localhost:8300/health"
        "Feedback Service"      = "http://localhost:8400/health"
        "ML Inference"          = "http://localhost:8500/health"
        "Correlation Engine"    = "http://localhost:8600/health"
        "Rule Generator"        = "http://localhost:8700/health"
        "Response Orchestrator" = "http://localhost:8800/health"
        "Wazuh Integration"     = "http://localhost:8002/health"
        "Ollama"                = "http://localhost:11434/api/tags"
        "Juice Shop Lab Target" = "http://localhost:3002"
    }

    foreach ($name in $checks.Keys) {
        if (Test-HttpOk $checks[$name] 8) {
            Write-Ok "$name reachable"
        } else {
            Write-Warn "$name not reachable yet: $($checks[$name])"
        }
    }

    $indexer = & curl.exe -k -sS -u "admin:CHANGE_ME_INDEXER_PASSWORD" --max-time 8 "https://localhost:9200/_cluster/health" 2>$null
    if ($LASTEXITCODE -eq 0 -and $indexer -match '"status"\s*:\s*"(green|yellow)"') {
        Write-Ok "Wazuh Indexer reachable"
    } else {
        Write-Warn "Wazuh Indexer not reachable yet"
    }
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Blue
Write-Host "   Aegis Guard One-Click Startup" -ForegroundColor Blue
Write-Host "========================================================" -ForegroundColor Blue

try {
    Set-Location $Root

    Wait-DockerEngine

    Invoke-ComposeUp $SiemCompose "Wazuh SIEM core"
    Invoke-ComposeUp $AiCompose "Aegis Guard services"

    $containers = @(
        "wazuh-indexer",
        "wazuh-manager",
        "wazuh-dashboard",
        "ai-soc-postgres",
        "ollama",
        "chromadb",
        "ml-inference",
        "alert-triage",
        "rag-service",
        "feedback-service",
        "wazuh-integration",
        "correlation-engine",
        "rule-generator",
        "response-orchestrator",
        "ai-soc-juice-shop"
    )
    Wait-HealthyContainers $containers

    Write-Step "Installing Aegis Guard action in Wazuh Threat Hunting"
    & $WazuhThreatHuntingPatch
    Write-Ok "Threat Hunting Ollama action is ready"

    Ensure-PythonDashboardDeps
    Start-Dashboard
    Invoke-SmokeChecks

    Write-Host ""
    Write-Host "Ready." -ForegroundColor Green
    Write-Host "  Aegis Guard GUI:        $DashboardUrl" -ForegroundColor Cyan
    Write-Host "  Juice Shop Lab:    http://localhost:3002" -ForegroundColor Cyan
    Write-Host "  Wazuh GUI:         https://localhost" -ForegroundColor Cyan
    Write-Host "  Incidents API:     http://localhost:8600/incidents" -ForegroundColor Cyan
    Write-Host "  Correlation Docs:  http://localhost:8600/docs" -ForegroundColor Cyan

    if (-not $NoBrowser) {
        Start-Process $DashboardUrl
    }
} catch {
    Write-Host ""
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Useful diagnostics:" -ForegroundColor Yellow
    Write-Host "  docker ps"
    Write-Host "  docker logs alert-triage --tail 100"
    Write-Host "  docker logs correlation-engine --tail 100"
    Write-Host "  Get-Content C:\tmp\ai-soc-dashboard.err.log -Tail 80"
    exit 1
}
