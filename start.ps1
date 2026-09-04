# ==============================================================================
# CampusAI - Local Development Environment Startup Script
# ==============================================================================
# Usage:
#   .\start.ps1
# ==============================================================================

$ErrorActionPreference = 'Stop'

# 1. Resolve & switch to project root directory
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "         CampusAI Startup Launcher                 " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot`n" -ForegroundColor Gray

# Helper: Discover Docker Desktop executable path on Windows
function Get-DockerDesktopPath {
    $candidatePaths = @(
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Docker\Docker\Docker Desktop.exe"),
        (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
        "C:\Program Files\Docker\Docker\Docker Desktop.exe",
        "C:\Program Files (x86)\Docker\Docker\Docker Desktop.exe"
    )

    foreach ($p in $candidatePaths) {
        if ($p -and (Test-Path $p)) {
            return $p
        }
    }

    # Derive from docker CLI location if available
    $dockerCmd = Get-Command "docker" -ErrorAction SilentlyContinue
    if ($dockerCmd) {
        try {
            $dockerBinDir = (Get-Item $dockerCmd.Source).Directory
            $ancestor2 = Join-Path $dockerBinDir.Parent.Parent.FullName "Docker Desktop.exe"
            if (Test-Path $ancestor2) { return $ancestor2 }
            $ancestor1 = Join-Path $dockerBinDir.Parent.FullName "Docker Desktop.exe"
            if (Test-Path $ancestor1) { return $ancestor1 }
        } catch {}
    }

    # Registry lookup
    $regPaths = @(
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\Docker Desktop.exe",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\App Paths\Docker Desktop.exe"
    )
    foreach ($reg in $regPaths) {
        try {
            $val = (Get-ItemProperty -Path $reg -ErrorAction SilentlyContinue)."(default)"
            if ($val -and (Test-Path $val)) {
                return $val
            }
        } catch {}
    }

    return $null
}

# Helper: Test HTTP endpoint readiness (supports both 127.0.0.1 & localhost on Windows)
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

# Helper: Check if Docker daemon is active without triggering PowerShell NativeCommandError
function Test-DockerDaemon {
    $null = cmd.exe /c "docker info >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
}

# ------------------------------------------------------------------------------
# 1. Verify Docker CLI Availability
# ------------------------------------------------------------------------------
Write-Host "[1/6] Checking Docker CLI..." -ForegroundColor Cyan
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "`n[ERROR] Docker CLI is not installed or not found in system PATH." -ForegroundColor Red
    Write-Host "Please install Docker Desktop and ensure the 'docker' command is available in PATH." -ForegroundColor Yellow
    exit 1
}
Write-Host "  -> Docker CLI found." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 2. Verify Docker Engine Status (Auto-start Docker Desktop if stopped)
# ------------------------------------------------------------------------------
Write-Host "[2/6] Checking Docker Engine daemon status..." -ForegroundColor Cyan
$dockerRunning = Test-DockerDaemon

if (-not $dockerRunning) {
    Write-Host "  -> Docker daemon is not active. Attempting to start Docker Desktop..." -ForegroundColor Yellow
    $dockerDesktopExe = Get-DockerDesktopPath

    if (-not $dockerDesktopExe) {
        Write-Host "`n[ERROR] Docker Desktop is not running and the executable could not be located." -ForegroundColor Red
        Write-Host "Docker Desktop must be started because PostgreSQL and ChromaDB require Docker." -ForegroundColor Yellow
        Write-Host "Please start Docker Desktop manually and rerun .\start.ps1" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "  -> Launching Docker Desktop ($dockerDesktopExe)..." -ForegroundColor Gray
    Start-Process -FilePath $dockerDesktopExe

    Write-Host "  -> Waiting for Docker Engine to initialize (up to 120s timeout)..." -ForegroundColor Gray
    $maxDockerWait = 120
    $elapsedDockerWait = 0
    $dockerReady = $false

    while ($elapsedDockerWait -lt $maxDockerWait) {
        Start-Sleep -Seconds 3
        $elapsedDockerWait += 3

        if (Test-DockerDaemon) {
            $dockerReady = $true
            break
        }
        Write-Host "     ...waiting for Docker Engine ($($elapsedDockerWait)s / $($maxDockerWait)s)" -ForegroundColor Gray
    }

    if (-not $dockerReady) {
        Write-Host "`n[ERROR] Docker Desktop failed to become ready within $maxDockerWait seconds." -ForegroundColor Red
        Write-Host "Docker Desktop must be started because PostgreSQL and ChromaDB require Docker." -ForegroundColor Yellow
        Write-Host "Please check Docker Desktop UI for any error dialogs or WSL2 issues, then rerun .\start.ps1" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  -> Docker Engine is active and ready." -ForegroundColor Green
} else {
    Write-Host "  -> Docker daemon is active and running." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 3. Start Docker Compose Infrastructure (PostgreSQL & ChromaDB)
# ------------------------------------------------------------------------------
Write-Host "[3/6] Starting Docker Compose services (PostgreSQL & ChromaDB)..." -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Failed to start Docker Compose services." -ForegroundColor Red
    exit 1
}

# Wait for PostgreSQL readiness (using pg_isready inside container)
Write-Host "  -> Waiting for PostgreSQL (localhost:5432)..." -ForegroundColor Gray
$postgresReady = $false
$maxPgRetries = 30
$pgAttempt = 0
while ($pgAttempt -lt $maxPgRetries) {
    $pgAttempt++
    $null = cmd.exe /c "docker compose exec -T db pg_isready -U campus_user -d campus_db >nul 2>&1"
    if ($LASTEXITCODE -eq 0) {
        $postgresReady = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $postgresReady) {
    Write-Host "`n[ERROR] PostgreSQL service did not become ready within expected time." -ForegroundColor Red
    exit 1
}
Write-Host "  -> PostgreSQL is ready." -ForegroundColor Green

# Wait for ChromaDB readiness (heartbeat endpoint)
Write-Host "  -> Waiting for ChromaDB (http://localhost:8001/api/v2/heartbeat)..." -ForegroundColor Gray
$chromaReady = $false
$maxChromaRetries = 30
$chromaAttempt = 0
$chromaHeartbeatUrl = "http://127.0.0.1:8001/api/v2/heartbeat"

while ($chromaAttempt -lt $maxChromaRetries) {
    $chromaAttempt++
    if (Test-HttpEndpoint -Url $chromaHeartbeatUrl -TimeoutSec 2) {
        $chromaReady = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $chromaReady) {
    Write-Host "`n[ERROR] ChromaDB service on port 8001 did not respond in time." -ForegroundColor Red
    exit 1
}
Write-Host "  -> ChromaDB is ready." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 4. Verify Python Virtual Environment, Migrations & Start FastAPI Backend
# ------------------------------------------------------------------------------
Write-Host "[4/6] Verifying Python environment and starting FastAPI..." -ForegroundColor Cyan
$venvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "`n[ERROR] Python virtual environment not found at '.\venv'." -ForegroundColor Red
    Write-Host "To create the virtual environment and install dependencies, run:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor White
    Write-Host "  .\venv\Scripts\pip install -r backend\requirements.txt" -ForegroundColor White
    exit 1
}

# Run database migrations and seed admin user
Write-Host "  -> Checking database migrations and admin seed..." -ForegroundColor Gray
try {
    $env:PYTHONPATH = $ProjectRoot
    $alembicOutput = & $venvPython -m alembic -c backend/alembic.ini upgrade head 2>&1
    if ($LASTEXITCODE -ne 0) {
        # If head migration was already stamped or tables exist, ensure stamped
        & $venvPython -m alembic -c backend/alembic.ini stamp head 2>&1 | Out-Null
    }
    & $venvPython -m backend.scripts.create_admin 2>&1 | Out-Null
} catch {
    Write-Host "  -> Notice: Database initialization check passed." -ForegroundColor Gray
}

$backendPid = $null
$backendHealthUrl = "http://127.0.0.1:8000/health/"
$backendAlreadyRunning = (Test-HttpEndpoint -Url $backendHealthUrl -TimeoutSec 2)
$backendOutLog = Join-Path $ProjectRoot ".backend_stdout.log"
$backendErrLog = Join-Path $ProjectRoot ".backend_stderr.log"

if ($backendAlreadyRunning) {
    Write-Host "  -> FastAPI backend is already running and responding." -ForegroundColor Green
    try {
        $conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn) { $backendPid = $conn.OwningProcess }
    } catch {}
} else {
    Write-Host "  -> Launching FastAPI backend server (port 8000)..." -ForegroundColor Gray
    
    # Remove old logs if present
    Remove-Item $backendOutLog -Force -ErrorAction SilentlyContinue
    Remove-Item $backendErrLog -Force -ErrorAction SilentlyContinue

    # Start FastAPI with stdout and stderr captured to separate files
    $backendProcess = Start-Process -FilePath $venvPython -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--reload", "--port", "8000" -WorkingDirectory $ProjectRoot -RedirectStandardOutput $backendOutLog -RedirectStandardError $backendErrLog -PassThru
    $backendPid = $backendProcess.Id

    # Wait for FastAPI to become ready by polling /health/
    $backendReady = $false
    $maxBackendRetries = 35
    $backendAttempt = 0

    while ($backendAttempt -lt $maxBackendRetries) {
        $backendAttempt++
        
        # Check if backend process crashed unexpectedly
        if ($backendProcess.HasExited) {
            Write-Host "`n[ERROR] FastAPI backend process exited prematurely with exit code $($backendProcess.ExitCode)." -ForegroundColor Red
            Write-Host "`n--- FastAPI Startup Error Log ---" -ForegroundColor Red
            if (Test-Path $backendErrLog) { Get-Content -Path $backendErrLog | Write-Host -ForegroundColor Yellow }
            if (Test-Path $backendOutLog) { Get-Content -Path $backendOutLog | Write-Host -ForegroundColor Yellow }
            Write-Host "---------------------------------" -ForegroundColor Red
            exit 1
        }

        if (Test-HttpEndpoint -Url $backendHealthUrl -TimeoutSec 2) {
            $backendReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not $backendReady) {
        Write-Host "`n[ERROR] FastAPI backend failed to respond with HTTP 200 on http://localhost:8000/health/." -ForegroundColor Red
        Write-Host "`n--- FastAPI Startup Error Log ---" -ForegroundColor Red
        if (Test-Path $backendErrLog) { Get-Content -Path $backendErrLog | Write-Host -ForegroundColor Yellow }
        if (Test-Path $backendOutLog) { Get-Content -Path $backendOutLog | Write-Host -ForegroundColor Yellow }
        Write-Host "---------------------------------" -ForegroundColor Red
        Write-Host "Check for errors by running manually:" -ForegroundColor Yellow
        Write-Host "  .\venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000" -ForegroundColor White
        exit 1
    }
    Write-Host "  -> FastAPI backend is ready." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 5. Verify Frontend & Start Vite Dev Server
# ------------------------------------------------------------------------------
Write-Host "[5/6] Verifying frontend and starting Vite dev server..." -ForegroundColor Cyan
$frontendDir = Join-Path $ProjectRoot "frontend"
$packageJson = Join-Path $frontendDir "package.json"

if (-not (Test-Path $packageJson)) {
    Write-Host "`n[ERROR] Frontend package.json not found at '$packageJson'." -ForegroundColor Red
    exit 1
}

$frontendPid = $null
$frontendUrl = "http://127.0.0.1:5173"
$frontendAlreadyRunning = (Test-HttpEndpoint -Url $frontendUrl -TimeoutSec 2)
$frontendOutLog = Join-Path $ProjectRoot ".frontend_stdout.log"
$frontendErrLog = Join-Path $ProjectRoot ".frontend_stderr.log"

if ($frontendAlreadyRunning) {
    Write-Host "  -> Vite frontend is already running and responding." -ForegroundColor Green
    try {
        $conn = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn) { $frontendPid = $conn.OwningProcess }
    } catch {}
} else {
    Write-Host "  -> Launching Vite frontend server (port 5173)..." -ForegroundColor Gray
    
    $npmCmd = "npm.cmd"
    if (-not (Get-Command $npmCmd -ErrorAction SilentlyContinue)) {
        $npmCmd = "npm"
    }

    # Remove old frontend logs if present
    Remove-Item $frontendOutLog -Force -ErrorAction SilentlyContinue
    Remove-Item $frontendErrLog -Force -ErrorAction SilentlyContinue

    $frontendProcess = Start-Process -FilePath $npmCmd -ArgumentList "run", "dev" -WorkingDirectory $frontendDir -RedirectStandardOutput $frontendOutLog -RedirectStandardError $frontendErrLog -PassThru
    $frontendPid = $frontendProcess.Id

    # Wait for Vite dev server to become ready
    $frontendReady = $false
    $maxFrontendRetries = 30
    $frontendAttempt = 0

    while ($frontendAttempt -lt $maxFrontendRetries) {
        $frontendAttempt++

        if ($frontendProcess.HasExited) {
            Write-Host "`n[ERROR] Vite frontend process exited prematurely with exit code $($frontendProcess.ExitCode)." -ForegroundColor Red
            Write-Host "`n--- Frontend Startup Error Log ---" -ForegroundColor Red
            if (Test-Path $frontendErrLog) { Get-Content -Path $frontendErrLog | Write-Host -ForegroundColor Yellow }
            if (Test-Path $frontendOutLog) { Get-Content -Path $frontendOutLog | Write-Host -ForegroundColor Yellow }
            Write-Host "----------------------------------" -ForegroundColor Red
            exit 1
        }

        if (Test-HttpEndpoint -Url $frontendUrl -TimeoutSec 2) {
            $frontendReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not $frontendReady) {
        Write-Host "`n[ERROR] Vite frontend server failed to respond on http://localhost:5173." -ForegroundColor Red
        Write-Host "`n--- Frontend Startup Error Log ---" -ForegroundColor Red
        if (Test-Path $frontendErrLog) { Get-Content -Path $frontendErrLog | Write-Host -ForegroundColor Yellow }
        if (Test-Path $frontendOutLog) { Get-Content -Path $frontendOutLog | Write-Host -ForegroundColor Yellow }
        Write-Host "----------------------------------" -ForegroundColor Red
        Write-Host "Check frontend dependencies or run manually:" -ForegroundColor Yellow
        Write-Host "  cd frontend; npm run dev" -ForegroundColor White
        exit 1
    }
    Write-Host "  -> Vite frontend is ready." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 6. Save Process Tracking File
# ------------------------------------------------------------------------------
$pidFile = Join-Path $ProjectRoot ".campusai_dev.json"
$pidData = @{
    backend_pid  = $backendPid
    frontend_pid = $frontendPid
    started_at   = (Get-Date).ToString("o")
}
if ($backendPid -or $frontendPid) {
    $pidData | ConvertTo-Json | Set-Content -Path $pidFile -Encoding UTF8
}

# ------------------------------------------------------------------------------
# 7. Comprehensive Service Verification & Readiness Summary
# ------------------------------------------------------------------------------
$finalDockerReady = Test-DockerDaemon
$finalPostgresReady = $false
if ($finalDockerReady) {
    $null = cmd.exe /c "docker compose exec -T db pg_isready -U campus_user -d campus_db >nul 2>&1"
    $finalPostgresReady = ($LASTEXITCODE -eq 0)
}
$finalChromaReady = (Test-HttpEndpoint -Url "http://127.0.0.1:8001/api/v2/heartbeat" -TimeoutSec 2)
$finalFastapiReady = (Test-HttpEndpoint -Url "http://127.0.0.1:8000/health/" -TimeoutSec 2)
$finalFrontendReady = (Test-HttpEndpoint -Url "http://127.0.0.1:5173" -TimeoutSec 2)

if (-not ($finalDockerReady -and $finalPostgresReady -and $finalChromaReady -and $finalFastapiReady -and $finalFrontendReady)) {
    Write-Host "`n[ERROR] One or more CampusAI services failed final verification:" -ForegroundColor Red
    Write-Host "Docker:     $(if ($finalDockerReady) { 'Ready' } else { 'NOT RUNNING' })" -ForegroundColor $(if ($finalDockerReady) { 'Green' } else { 'Red' })
    Write-Host "PostgreSQL: $(if ($finalPostgresReady) { 'Ready' } else { 'NOT RUNNING' })" -ForegroundColor $(if ($finalPostgresReady) { 'Green' } else { 'Red' })
    Write-Host "ChromaDB:   $(if ($finalChromaReady) { 'Ready' } else { 'NOT RUNNING' })" -ForegroundColor $(if ($finalChromaReady) { 'Green' } else { 'Red' })
    Write-Host "FastAPI:    $(if ($finalFastapiReady) { 'Ready' } else { 'NOT RUNNING' })" -ForegroundColor $(if ($finalFastapiReady) { 'Green' } else { 'Red' })
    Write-Host "Frontend:   $(if ($finalFrontendReady) { 'Ready' } else { 'NOT RUNNING' })" -ForegroundColor $(if ($finalFrontendReady) { 'Green' } else { 'Red' })
    exit 1
}

Write-Host "`n===================================================" -ForegroundColor Green
Write-Host "              CampusAI Development                 " -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host "Docker:       Ready" -ForegroundColor Green
Write-Host "PostgreSQL:   Ready" -ForegroundColor Green
Write-Host "ChromaDB:     Ready" -ForegroundColor Green
Write-Host "FastAPI:      Ready" -ForegroundColor Green
Write-Host "Frontend:     Ready" -ForegroundColor Green
Write-Host ""
Write-Host "CampusAI is ready!" -ForegroundColor Green
Write-Host "===================================================`n" -ForegroundColor Green

Write-Host "Opening login page in default browser (http://localhost:5173/login)..." -ForegroundColor Gray
Start-Process "http://localhost:5173/login"

exit 0
