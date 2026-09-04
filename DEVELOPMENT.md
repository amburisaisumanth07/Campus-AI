# CampusAI — Development Guide

CampusAI is an AI-powered student knowledge system for college rules, academic regulations, examination policies, attendance guidelines, and course requirements.

---

## 1. Prerequisites

Before starting the development environment, ensure the following tools are installed:

- **Docker Desktop** (with Docker Engine & Docker Compose support)
- **Python 3.11+** (virtual environment located at `./venv`)
- **Node.js 18+** & **npm**
- **PowerShell 5.1+** (Windows 10/11)

---

## 2. One-Command Startup

To automatically start all infrastructure, backend services, and the frontend web app, run:

```powershell
.\start.ps1
```

### What `start.ps1` does automatically:
1. Verifies Docker CLI availability.
2. Checks Docker Engine daemon status via `docker info`:
   - If Docker Desktop is stopped, `start.ps1` automatically locates and launches `Docker Desktop.exe` on Windows and polls until the Docker Engine is active (up to a 120-second timeout).
3. Starts containerized services via `docker compose up -d`.
4. Waits for **PostgreSQL** (`localhost:5432`) to become healthy using `pg_isready`.
5. Waits for **ChromaDB** (`http://localhost:8001/api/v2/heartbeat`) to respond.
6. Verifies the Python virtual environment (`.\venv\Scripts\python.exe`).
7. Starts the **FastAPI** backend (`.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000`) in the background.
8. Polls `http://localhost:8000/health/` until FastAPI responds successfully.
9. Starts the **Vite + React** frontend (`npm run dev` in `frontend/`) in the background.
10. Polls `http://localhost:5173` until Vite is ready.
11. Opens `http://localhost:5173` in your default web browser and leaves the PowerShell terminal free.

---

## 3. Architecture & Service Ports

| Service | Technology | Port / Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Docker Engine** | Docker Desktop | System Daemon | Container virtualization runtime for database engines |
| **PostgreSQL** | Docker (`postgres:16-alpine`) | `localhost:5432` | Relational database (users, documents, conversations, messages, feedback) |
| **ChromaDB** | Docker (`chromadb/chroma:1.5.9`) | `http://localhost:8001` | Vector database for 768-dim semantic document chunk retrieval |
| **FastAPI Backend** | Python + Uvicorn | `http://localhost:8000` | REST API, auth (JWT), RAG pipeline, doc processing |
| **React Frontend** | React 18 + Vite + TypeScript | `http://localhost:5173` | Student portal, chat assistant interface, admin document manager |

---

## 4. Checking Service Status

To inspect the health and status of all CampusAI services at any time, run:

```powershell
.\status.ps1
```

Example output:
```text
===================================================
            CampusAI Service Status                
===================================================
Docker:       Ready
PostgreSQL:   Ready
ChromaDB:     Ready
FastAPI:      http://localhost:8000
Frontend:     http://localhost:5173
===================================================
```

---

## 5. Stopping the Development Environment

### Stop Application Servers (FastAPI & Vite only):
Leaves PostgreSQL and ChromaDB running so you keep database state:

```powershell
.\stop.ps1
```

### Stop Everything (including Docker containers):
Stops FastAPI, Vite, and containerized services (database volumes remain safe and intact):

```powershell
.\stop.ps1 -Docker
```

> **Note:** `stop.ps1` will never destroy your persistent database data volumes.

---

## 6. Running Tests

### Automated Full Test Suite (with Docker validation):
```powershell
.\scripts\run-tests.ps1
```

### Backend Unit Tests:
```powershell
.\venv\Scripts\python.exe -m pytest backend/tests/unit
```

### Backend API & Integration Tests:
```powershell
.\venv\Scripts\python.exe -m pytest backend/tests/api backend/tests/integration
```

### Frontend Tests (Vitest):
```powershell
cd frontend
npm test -- --run
```

---

## 7. Common Troubleshooting

### 1. Docker Desktop Not Installed
- **Symptom:** `start.ps1` reports `[ERROR] Docker CLI is not installed or not found in system PATH`.
- **Solution:** Install Docker Desktop from [Docker official website](https://www.docker.com/products/docker-desktop) and ensure it is on PATH.

### 2. Python Virtual Environment Missing
- **Symptom:** `start.ps1` reports `Python virtual environment not found at '.\venv'`.
- **Solution:** Run:
  ```powershell
  python -m venv venv
  .\venv\Scripts\pip install -r backend\requirements.txt
  ```

### 3. Frontend Dependencies Missing
- **Symptom:** Vite fails to start.
- **Solution:** Run:
  ```powershell
  cd frontend
  npm install
  ```

### 4. Database Migration Updates
- **Symptom:** Database tables missing or schema out of date.
- **Solution:** Run:
  ```powershell
  .\venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
  ```
