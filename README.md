# Assignment - Workflow App

A minimal, runnable workflow demo application:
- Backend: FastAPI (in-memory) with create/get/add-node/run endpoints
- Frontend: Vite + React + TypeScript UI to create workflows, add nodes, run, and view the simulated result

## Requirements
- Python 3.11+ (3.10/3.11 recommended)
- Node.js 18+ and npm
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

### 1) Backend (port 8000)
```bash
# From repo root
python3 -m venv .venv
source .venv/bin/activate  # zsh
pip install -r server/requirements.txt

# Start (dev with reload)
uvicorn server.main:app --reload --port 8000
# Or production-like (no reload)
# uvicorn server.main:app --port 8000
```

### 2) Frontend (port 3000)
```bash
cd client
npm install
npm run dev
# Open http://localhost:3000/
```

### 3) End-to-End Verification
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
```

## API Reference
- POST `/workflows` → `{ id, name }`
- GET `/workflows/{id}` → `{ id, name, nodes[] }`
- POST `/workflows/{id}/nodes` → `{ message, node_id }`
- POST `/workflows/{id}/run` → `{ final_output }`

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
- Frontend blank page or startup error:
  - Ensure `client/index.html` exists with `<div id="root"></div>` and entry script `/src/main.tsx`
  - Ensure `client/src/main.tsx` renders `<App />` to `#root`
  - Run `npm install` again if dependencies changed
- Backend not responding:
  - Confirm Uvicorn is running on port 8000
  - Terminal should show FastAPI app started and routes registered
- CORS issues:
  - Check `server/main.py` CORS settings include `http://localhost:3000`

## License
For assignment use only.
