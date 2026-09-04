# ==============================================================================
# CampusAI - Development & Test Automation Script
# ==============================================================================
# Purpose:
#   This script automates setting up local Docker services (PostgreSQL & Chroma)
#   and running the backend pytest suite.
#
# Key Features:
#   1. Verifies Docker CLI & Docker Engine daemon availability.
#   2. Starts required containerized services via 'docker compose up -d'.
#   3. Performs dynamic health/readiness checks for PostgreSQL and Chroma.
#   4. Executes pytest against backend/tests with verbose output (-v -rs).
#   5. Preserves pytest exit codes (returns 0 on success, non-zero on failure).
#   6. Leaves services running for local development workflow.
#
# Usage:
#   .\scripts\run-tests.ps1
# ==============================================================================

# Ensure script halts on unhandled errors for predictable automation
$ErrorActionPreference = 'Stop'

# Step 0: Resolve Project Root Directory
# $PSScriptRoot points to the folder containing this script (scripts/)
# We resolve the parent directory so the script can be called from anywhere.
$ScriptDir = $PSScriptRoot
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $ProjectRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "       CampusAI Test Automation Launcher           " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot`n" -ForegroundColor Gray

# ------------------------------------------------------------------------------
# 1. Verify Docker CLI Availability
# ------------------------------------------------------------------------------
# Check if the 'docker' command exists in the system PATH.
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "[CHECK FAILED] Docker CLI is not installed or not found in system PATH." -ForegroundColor Red
    Write-Host "Please install Docker Desktop and ensure the 'docker' command is available." -ForegroundColor Yellow
    exit 1
}

# ------------------------------------------------------------------------------
# 2. Detect Docker Daemon Status
# ------------------------------------------------------------------------------
# Running 'docker info' verifies whether the background Docker Engine is active.
Write-Host "[1/4] Checking Docker daemon status..." -ForegroundColor Cyan
docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[CHECK FAILED] Docker daemon is not running." -ForegroundColor Red
    Write-Host "Please start Docker Desktop / Docker Engine and try running this script again." -ForegroundColor Yellow
    exit 1
}
Write-Host "  -> Docker daemon is active and responding." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 3. Ensure Docker Compose Services are Running
# ------------------------------------------------------------------------------
# Uses existing docker-compose.yml to bring up 'db' (PostgreSQL) & 'chroma' (ChromaDB)
Write-Host "[2/4] Ensuring Docker Compose services are running..." -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to start Docker Compose services." -ForegroundColor Red
    exit 1
}
Write-Host "  -> Docker Compose containers started/verified." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 4. Wait for PostgreSQL Health / Readiness
# ------------------------------------------------------------------------------
# Instead of a fixed sleep, we poll 'pg_isready' inside the 'db' container until
# PostgreSQL is ready to accept database connections.
Write-Host "[3/4] Checking PostgreSQL readiness (localhost:5432)..." -ForegroundColor Cyan
$postgresReady = $false
$maxPgRetries = 30
$pgAttempt = 0

while ($pgAttempt -lt $maxPgRetries) {
    $pgAttempt++
    # 'pg_isready' returns 0 when PostgreSQL is accepting connections
    docker compose exec -T db pg_isready -U campus_user -d campus_db 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $postgresReady = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $postgresReady) {
    Write-Host "[ERROR] PostgreSQL service did not become ready within expected time." -ForegroundColor Red
    exit 1
}
Write-Host "  -> PostgreSQL database service is healthy." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 5. Wait for Chroma HTTP Service Readiness
# ------------------------------------------------------------------------------
# Polls Chroma's HTTP heartbeat endpoint at http://localhost:8001/api/v2/heartbeat
# until Chroma responds with HTTP status 200 (OK).
Write-Host "[4/4] Checking Chroma vector database readiness (http://localhost:8001)..." -ForegroundColor Cyan
$chromaReady = $false
$maxChromaRetries = 30
$chromaAttempt = 0
$chromaHeartbeatUrl = "http://localhost:8001/api/v2/heartbeat"

while ($chromaAttempt -lt $maxChromaRetries) {
    $chromaAttempt++
    try {
        # Invoke-WebRequest sends an HTTP GET request to check service availability
        $response = Invoke-WebRequest -Uri $chromaHeartbeatUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($response -and $response.StatusCode -eq 200) {
            $chromaReady = $true
            break
        }
    } catch {
        # Suppress request exceptions during startup polling
    }
    Start-Sleep -Seconds 1
}

if (-not $chromaReady) {
    Write-Host "[ERROR] Chroma HTTP service on http://localhost:8001 did not respond in time." -ForegroundColor Red
    exit 1
}
Write-Host "  -> Chroma vector database service is ready." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 6. Execute Pytest Backend Suite
# ------------------------------------------------------------------------------
Write-Host "`nExecuting backend test suite..." -ForegroundColor Cyan
$venvPytest = Join-Path $ProjectRoot "venv\Scripts\pytest.exe"

# Fallback check if pytest executable exists inside local virtual environment
if (-not (Test-Path $venvPytest)) {
    Write-Host "[ERROR] pytest executable not found at '$venvPytest'." -ForegroundColor Red
    Write-Host "Please ensure the virtual environment is set up at .\venv." -ForegroundColor Yellow
    exit 1
}

# Execute pytest with -v (verbose) and -rs (show reason for skipped tests)
$env:PYTHONPATH = $ProjectRoot
& $venvPytest backend/tests/ -v -rs
$pytestExitCode = $LASTEXITCODE

# ------------------------------------------------------------------------------
# 7. Print Execution Summary
# ------------------------------------------------------------------------------
Write-Host "`n================ Execution Summary ================" -ForegroundColor Cyan
Write-Host "Docker:     Ready" -ForegroundColor Green
Write-Host "PostgreSQL: Ready" -ForegroundColor Green
Write-Host "Chroma:     Ready" -ForegroundColor Green

if ($pytestExitCode -eq 0) {
    Write-Host "Tests:      Passed" -ForegroundColor Green
} else {
    Write-Host "Tests:      Failed (Exit Code: $pytestExitCode)" -ForegroundColor Red
}
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Note: Docker containers remain running for active development.`n" -ForegroundColor Gray

# Preserve and exit with pytest's exit code
exit $pytestExitCode
