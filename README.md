# Assignment - Workflow App

A minimal, runnable workflow demo application:
- Backend: FastAPI with PostgreSQL persistence, create/get/add-node/run endpoints, and run history tracking
- Frontend: Vite + React + TypeScript UI to create workflows, add nodes, run, and view the simulated result

## Requirements
- Python 3.11+ (3.10/3.11 recommended)
- Node.js 18+ and npm
- Docker and Docker Compose (for PostgreSQL)
- macOS/Linux (zsh)

## Project Structure
```
.
├── server
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── requirements.txt
└── client
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    └── src
        ├── App.tsx
        ├── api.ts
        └── types.ts
```
Note: `client/index.html` and `client/src/main.tsx` are included by default. If they are accidentally removed, see Troubleshooting to restore them.

## Quick Start

### Development Approach
Choose your preferred development style:

**Option A: Hybrid (Recommended for PyCharm/IDE)**
- Database: Docker PostgreSQL
- Backend/Frontend: Local development with venv/npm

**Option B: Full Docker**
- Everything containerized

### Option A: Hybrid Development

#### 1) Database (PostgreSQL)
```bash
# Start PostgreSQL database
docker compose up -d postgres

# Wait for database to be healthy
docker compose ps postgres
```

#### 2) Backend (port 8000)
```bash
# From repo root
python3 -m venv .venv
source .venv/bin/activate  # zsh
pip install -r server/requirements.txt

# Apply database migrations
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m alembic upgrade head

# Start (dev with reload)
cd server
PYTHONPATH=.. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 3) Frontend (port 3000)
```bash
cd client
npm install
npm run dev
# Open http://localhost:3000/
```

### Option B: Full Docker
```bash
# Everything at once
docker compose up --build

# With database admin (optional)
docker compose --profile dev up --build
# Access pgAdmin at http://localhost:5050 (admin@workflow.local / admin)
```

### 4) End-to-End Verification
- In the UI:
  - Enter a workflow name and create
  - Click Fetch to view it (nodes initially empty)
  - Add nodes: extract_text / generative_ai / formatter
  - Click Run Workflow; a dialog shows the final output
- Using curl (optional):
```bash
# Create
curl -s http://localhost:8000/workflows -X POST -H 'Content-Type: application/json' -d '{"name":"demo"}'
# Get
curl -s http://localhost:8000/workflows/{wf_id}
# Add node
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{"node_type":"generative_ai","config":{"prompt":"Summarize"}}'
# Run
curl -s http://localhost:8000/workflows/{wf_id}/run
# View run history
curl -s http://localhost:8000/workflows/{wf_id}/runs
# Get detailed run info
curl -s http://localhost:8000/runs/{run_id}
```

## Testing

### PyCharm Setup
1. **Configure Python Interpreter**:
   - File → Settings → Project → Python Interpreter
   - Add existing environment: `.venv/bin/python`
2. **Mark Sources Root**: Right-click project root → Mark Directory as → Sources Root

### Running Tests
```bash
# Start database first
docker compose up -d postgres

# Activate virtual environment
source .venv/bin/activate

# Run tests
# Unit tests (no database required)
PYTHONPATH=. python3 -m pytest tests/unit/ -v

# Contract tests (require database)
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m pytest tests/contract/ -v

# Integration tests (require database)
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m pytest tests/integration/ -v

# All tests
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m pytest tests/ -v
```

## API Reference
- POST `/workflows` → `{ id, name }`
- GET `/workflows/{id}` → `{ id, name, nodes[] }`
- POST `/workflows/{id}/nodes` → `{ message, node_id }`
- POST `/workflows/{id}/run` → `{ final_output }`
- GET `/workflows/{id}/runs` → `{ runs: [{ id, workflow_id, status, started_at, finished_at?, final_output? }] }`
- GET `/runs/{run_id}` → `{ run: { id, workflow_id, status, ... }, steps: [{ id, node_type, status, input_text, output_text, ... }] }`

## Minimal Endpoints (Per Constitution)
These describe the minimal target API as defined by the constitution (asynchronous runs, file uploads). They may extend beyond the current in-memory demo.

- POST `/workflows` → `{ id, name }`
- GET `/workflows/{id}` → `{ id, name, nodes: Node[] }`
- POST `/workflows/{id}/nodes` → `{ message, node_id }`
- POST `/files` (multipart/form-data; file: pdf) → `{ file_id }`
- POST `/workflows/{id}/run` → `{ job_id }`
- GET `/jobs/{job_id}` → `{ status: "Pending"|"Running"|"Succeeded"|"Failed", result?: { final_output: string }, error?: string }`

Notes:
- PDF only, size-limited (e.g., 10MB), MIME validated.
- CORS enabled for local dev (`http://localhost:3000`).
- Secrets (e.g., LLM_API_KEY) are provided via environment variables.

## Minimal Data Model (Per Constitution)
SQLite (single-file) schema sufficient for persistence and async execution tracking:

- workflows
  - `id` (TEXT PK)
  - `name` (TEXT)
  - `created_at` (DATETIME)

- nodes
  - `id` (TEXT PK)
  - `workflow_id` (TEXT FK → workflows.id)
  - `node_type` (TEXT: `extract_text` | `generative_ai` | `formatter`)
  - `config_json` (TEXT)
  - `order_index` (INTEGER)

- files
  - `id` (TEXT PK)
  - `filename` (TEXT)
  - `mime_type` (TEXT)
  - `size_bytes` (INTEGER)
  - `path` (TEXT)
  - `created_at` (DATETIME)

- jobs
  - `id` (TEXT PK)
  - `workflow_id` (TEXT FK → workflows.id)
  - `status` (TEXT: `Pending` | `Running` | `Succeeded` | `Failed`)
  - `result_json` (TEXT, NULLABLE)
  - `error` (TEXT, NULLABLE)
  - `started_at` (DATETIME)
  - `finished_at` (DATETIME, NULLABLE)

## CORS & Ports
- Backend allows origin: `http://localhost:3000`
- If ports are busy, update the port and CORS origin accordingly

## Spec Generation (specify)
From repo root:
```bash
./.specify/scripts/bash/create-new-feature.sh --json '{"feature_name":"Workflow Builder sample app for assignment", "...": "..."}'
```
The script will:
- Create and checkout a new branch (e.g., `001-feature-name-workflow`)
- Initialize spec at `specs/001-feature-name-workflow/spec.md`
- Template at `.specify/templates/spec-template.md`

## Docker (dev, hot-reload/HMR)
```bash
# From repo root
docker compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```
Dev compose mounts source directories and enables hot reload (backend) and HMR (frontend).

## Static Hosting
```bash
cd client
VITE_API_BASE=https://api.example.com npm run build
# Upload client/dist to your static host
```
If `VITE_API_BASE` is not set, the frontend uses `http://localhost:8000` by default.

## Troubleshooting

### Development Issues
- **"Unresolved reference 'fastapi'" in PyCharm**:
  - Configure Python interpreter to use `.venv/bin/python`
  - Mark project root as Sources Root
  - Ensure virtual environment is activated: `source .venv/bin/activate`

- **Import errors when running tests**:
  - Use `PYTHONPATH=.` when running pytest
  - Ensure database is running: `docker compose up -d postgres`

### Application Issues
- Frontend blank page or startup error:
  - Ensure `client/index.html` exists with `<div id="root"></div>` and entry script `/src/main.tsx`
  - Ensure `client/src/main.tsx` renders `<App />` to `#root`
  - Run `npm install` again if dependencies changed
- Backend not responding:
  - Confirm Uvicorn is running on port 8000
  - Terminal should show FastAPI app started and routes registered
  - Check database connection with `docker compose ps postgres`
- CORS issues:
  - Check `server/main.py` CORS settings include `http://localhost:3000`

## License
For assignment use only.
