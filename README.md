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

### Core Workflow Endpoints
- **POST** `/workflows` → `{ id, name }`
- **GET** `/workflows/{id}` → `{ id, name, nodes[] }`
- **POST** `/workflows/{id}/nodes` → `{ message, node_id }`
- **GET** `/workflows/{id}/runs` → `{ runs: [Job] }`

### DAG Workflow Endpoints (NEW)
- **POST** `/workflows/{id}/edges` → `{ message, edge_id }` *(connect nodes with cycle detection)*
- **GET** `/workflows/{id}/edges` → `{ edges: [Edge] }` *(list all edges)*

### Async Execution (NEW)
- **POST** `/workflows/{id}/run` → `{ job_id, message }` *(async execution)*
- **GET** `/jobs/{job_id}` → `{ id, workflow_id, status, started_at, finished_at?, final_output?, error_message? }`

### File Operations (NEW)
- **POST** `/files` (multipart/form-data) → `{ file_id, filename, message }`

### Supported Node Types
1. **extract_text**: Extract text from uploaded PDF files
   - Config: `{ file_id: string }`
2. **generative_ai**: Process text using OpenAI models
   - Config: `{ model: string, prompt: string, temperature?: number, max_tokens?: number, top_p?: number }`
   - Supported models: `gpt-4.1-mini`, `gpt-4o`, `gpt-5`
3. **formatter**: Apply text transformation rules
   - Config: `{ rules: string[] }`
   - Available rules: `lowercase`, `uppercase`, `full_to_half`, `half_to_full`
4. **agent** (NEW): AI Agent with bounded execution and tool access
   - Config: `{ objective: string, tools: string[], budgets: object, max_concurrent?: number, timeout_seconds?: number, max_retries?: number, max_iterations?: number, formatting_rules?: string[] }`
   - Available tools: `llm_call`, `formatter`
   - Budgets: `{ execution_time: number }` (seconds)
   - Policy limits: max_concurrent ≤ 10, timeout_seconds ≤ 30, max_retries ≤ 3

### Job Status Flow
```
Pending → Running → Succeeded/Failed
```

## DAG Workflows (NEW)

### Features
- **Directed Acyclic Graph (DAG)**: Connect nodes with edges to create complex workflows
- **Cycle Detection**: Automatic validation prevents circular dependencies
- **Topological Scheduling**: Nodes execute in dependency order with maximum parallelism
- **AND-join Semantics**: Downstream nodes wait for ALL upstream dependencies to complete
- **Parallel Execution**: Independent nodes run concurrently within batches

### Edge Configuration
```json
{
  "from_node_id": "node-1",
  "to_node_id": "node-2",
  "from_port": "output",
  "to_port": "input",
  "condition": null
}
```

### Execution Model
1. **Validation**: Cycle detection ensures DAG property
2. **Scheduling**: Topological sort creates execution batches
3. **Parallel Execution**: Nodes within each batch run concurrently
4. **Input Aggregation**: Multi-input nodes receive concatenated upstream outputs
5. **Deterministic Order**: Alphabetical sorting ensures reproducible results

### Example: Diamond Pattern
```
    A (start)
   / \
  B   C (parallel)
   \ /
    D (waits for both B and C)
```

### Concurrency Limits
- Max 2 running jobs per workflow
- Max 20 jobs in queue (FIFO)
- Returns HTTP 429 when queue is full

### File Upload Constraints
- **Format**: PDF files only
- **Size**: Maximum 10MB
- **Validation**: MIME type and PDF header verification
- **Security**: No encrypted/password-protected PDFs

### Environment Variables
Set these environment variables for full functionality:
```bash
# Required for LLM functionality
LLM_API_KEY=your_openai_api_key_here
LLM_API_BASE=https://api.openai.com/v1  # Optional, defaults to OpenAI

# Database (auto-configured in development)
DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db
```

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
