# ==============================================================================
# CampusAI - Local Development Environment Shutdown Script
# ==============================================================================
# Usage:
#   .\stop.ps1          # Stops FastAPI & Vite (leaves Docker containers running)
#   .\stop.ps1 -Docker  # Stops FastAPI, Vite, AND Docker Compose services
# ==============================================================================

param (
    [switch]$Docker
)

$ErrorActionPreference = 'Continue'

# 1. Resolve & switch to project root directory
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "         CampusAI Shutdown Manager                 " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$pidFile = Join-Path $ProjectRoot ".campusai_dev.json"

# Helper to terminate a process and its child tree safely
function Stop-ProcessTree {
    param(
        [int]$PidToStop,
        [string]$ProcessName
    )
    if ($PidToStop -gt 0) {
        $proc = Get-Process -Id $PidToStop -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  -> Stopping $ProcessName (PID: $PidToStop)..." -ForegroundColor Gray
            taskkill /PID $PidToStop /T /F 2>&1 | Out-Null
            Write-Host "     $ProcessName stopped." -ForegroundColor Green
            return
        }
    }
}

# Helper to stop processes listening on specific local ports (8000 for FastAPI, 5173 for Vite)
function Stop-PortListener {
    param(
        [int]$Port,
        [string]$ServiceName
    )
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($connections) {
            foreach ($conn in $connections) {
                $ownerPid = $conn.OwningProcess
                if ($ownerPid -gt 0 -and $ownerPid -ne $PID) {
                    $ownerProc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
                    if ($ownerProc -and ($ownerProc.ProcessName -match "python|node|uvicorn|npm")) {
                        Write-Host "  -> Stopping $ServiceName on port $Port (PID: $ownerPid)..." -ForegroundColor Gray
                        taskkill /PID $ownerPid /T /F 2>&1 | Out-Null
                        Write-Host "     $ServiceName on port $Port stopped." -ForegroundColor Green
                    }
                }
            }
        }
    } catch {}
}

# 1. Stop tracked PIDs from .campusai_dev.json
if (Test-Path $pidFile) {
    try {
        $pidContent = Get-Content -Path $pidFile -Raw | ConvertFrom-Json
        if ($pidContent.backend_pid) {
            Stop-ProcessTree -PidToStop $pidContent.backend_pid -ProcessName "FastAPI Backend"
        }
        if ($pidContent.frontend_pid) {
            Stop-ProcessTree -PidToStop $pidContent.frontend_pid -ProcessName "Vite Frontend"
        }
    } catch {}
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
}

# 2. Ensure ports 8000 and 5173 are freed if any orphan python/node process is still listening
Stop-PortListener -Port 8000 -ServiceName "FastAPI Backend"
Stop-PortListener -Port 5173 -ServiceName "Vite Frontend"

Write-Host "`n[OK] Development server processes (FastAPI & Vite) stopped." -ForegroundColor Green

# 3. Handle Docker option
if ($Docker) {
    Write-Host "`nStopping Docker Compose containers (PostgreSQL & ChromaDB)..." -ForegroundColor Cyan
    docker compose stop
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  -> Docker Compose services stopped (data preserved in volumes)." -ForegroundColor Green
    } else {
        Write-Host "  -> Warning: Docker compose stop returned non-zero code." -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[NOTE] Docker containers remain running for database persistence." -ForegroundColor Gray
    Write-Host "       To also stop Docker services, run: .\stop.ps1 -Docker" -ForegroundColor Gray
}

Write-Host "`n===================================================" -ForegroundColor Cyan
Write-Host "CampusAI development shutdown complete." -ForegroundColor Green
Write-Host "===================================================`n" -ForegroundColor Cyan

exit 0
