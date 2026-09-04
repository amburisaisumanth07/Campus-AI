# ==============================================================================
# CampusAI - Service Status Inspector
# ==============================================================================
# Usage:
#   .\status.ps1
# ==============================================================================

$ErrorActionPreference = 'Continue'

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "            CampusAI Service Status                " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

function Test-HttpEndpoint {
    param(
        [string]$Url,
        [int]$TimeoutSec = 2
    )
    $candidateUrls = @()
    if ($Url -match "localhost") {
        $candidateUrls += $Url.Replace("localhost", "127.0.0.1")
        $candidateUrls += $Url
    } else {
        $candidateUrls += $Url
        if ($Url -match "127\.0\.0\.1") {
            $candidateUrls += $Url.Replace("127.0.0.1", "localhost")
        }
    }

    foreach ($target in $candidateUrls) {
        try {
            $response = Invoke-WebRequest -Uri $target -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
            if ($response -and $response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return $true
            }
        } catch {
            if ($_.Exception.Response) {
                $statusCode = [int]$_.Exception.Response.StatusCode
                if ($statusCode -ge 200 -and $statusCode -lt 400) {
                    return $true
                }
            }
        }
    }
    return $false
}

function Test-DockerDaemon {
    $null = cmd.exe /c "docker info >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
}

# 1. Docker Daemon
$dockerStatus = "NOT RUNNING"
$dockerColor = "Red"
if (Get-Command "docker" -ErrorAction SilentlyContinue) {
    if (Test-DockerDaemon) {
        $dockerStatus = "Ready"
        $dockerColor = "Green"
    }
}

# 2. PostgreSQL
$pgStatus = "NOT RUNNING"
$pgColor = "Red"
if ($dockerStatus -eq "Ready") {
    $null = cmd.exe /c "docker compose exec -T db pg_isready -U campus_user -d campus_db >nul 2>&1"
    if ($LASTEXITCODE -eq 0) {
        $pgStatus = "Ready"
        $pgColor = "Green"
    }
}

# 3. ChromaDB
$chromaStatus = "NOT RUNNING"
$chromaColor = "Red"
if (Test-HttpEndpoint -Url "http://127.0.0.1:8001/api/v2/heartbeat" -TimeoutSec 2) {
    $chromaStatus = "Ready"
    $chromaColor = "Green"
}

# 4. FastAPI Backend
$fastapiStatus = "NOT RUNNING"
$fastapiColor = "Red"
if (Test-HttpEndpoint -Url "http://127.0.0.1:8000/health/" -TimeoutSec 2) {
    $fastapiStatus = "Ready (http://localhost:8000)"
    $fastapiColor = "Green"
}

# 5. Vite Frontend
$frontendStatus = "NOT RUNNING"
$frontendColor = "Red"
if (Test-HttpEndpoint -Url "http://127.0.0.1:5173" -TimeoutSec 2) {
    $frontendStatus = "Ready (http://localhost:5173)"
    $frontendColor = "Green"
}

Write-Host ("Docker:       " + $dockerStatus) -ForegroundColor $dockerColor
Write-Host ("PostgreSQL:   " + $pgStatus) -ForegroundColor $pgColor
Write-Host ("ChromaDB:     " + $chromaStatus) -ForegroundColor $chromaColor
Write-Host ("FastAPI:      " + $fastapiStatus) -ForegroundColor $fastapiColor
Write-Host ("Frontend:     " + $frontendStatus) -ForegroundColor $frontendColor
Write-Host "===================================================`n" -ForegroundColor Cyan

exit 0
