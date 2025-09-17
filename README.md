# Assignment - Workflow App

A comprehensive workflow automation platform with DAG (Directed Acyclic Graph) support, AI agent nodes, and real-time execution:

- **Backend**: FastAPI with PostgreSQL persistence, DAG workflows, async execution, and agent nodes
- **Frontend**: React TypeScript UI with workflow builder, node configuration, and real-time status updates
- **Features**: PDF text extraction, OpenAI integration, text formatting, bounded AI agents, cycle detection

## Requirements

### System Requirements
- Python 3.11+ (3.10/3.11 recommended)
- Node.js 18+ and npm
- Docker and Docker Compose (for PostgreSQL)
- macOS/Linux (zsh/bash)

### Optional Requirements
- OpenAI API key (for generative AI nodes)
- Git (for version control)
- IDE with Python support (PyCharm recommended)

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

# Setup and Launch Instructions

## Quick Start

### Development Approach
Choose your preferred development style:

**Option A: Hybrid (Recommended for PyCharm/IDE)**
- Database: Docker PostgreSQL
- Backend/Frontend: Local development with venv/npm

**Option B: Full Docker**
- Everything containerized

### Option A: Hybrid Development (Recommended)

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

# Tests and Instructions

## Test Structure

The project includes comprehensive test coverage across multiple layers:

- **Unit Tests** (`tests/unit/`): Fast isolated tests for individual components
- **Contract Tests** (`tests/contract/`): API endpoint validation and data contract verification
- **Integration Tests** (`tests/integration/`): End-to-end workflow testing with real components
- **Performance Tests** (`tests/performance/`): Load testing and DAG performance benchmarks

## Running Tests

### Prerequisites
```bash
# Start database (required for contract/integration tests)
docker compose up -d postgres

# Activate virtual environment
source .venv/bin/activate

# Ensure dependencies are installed
pip install -r server/requirements.txt
```

### Test Categories

#### Unit Tests (No Database Required)
```bash
PYTHONPATH=. python3 -m pytest tests/unit/ -v
```
- Tests individual services and utilities
- Fast execution (~5-10 seconds)
- No external dependencies

#### Contract Tests (Database Required)
```bash
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m pytest tests/contract/ -v
```
- Validates API endpoints and request/response contracts
- Tests data models and schema validation
- Requires running PostgreSQL instance

#### Integration Tests (Database Required)
```bash
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m pytest tests/integration/ -v
```
- End-to-end workflow execution
- DAG scheduling and parallel execution
- File upload and processing pipelines

#### Performance Tests (Database Required)
```bash
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m pytest tests/performance/ -v
```
- Large DAG performance benchmarks
- Cycle detection optimization validation
- Memory usage and execution time analysis

#### All Tests
```bash
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m pytest tests/ -v
```

### IDE Setup (PyCharm)
1. **Configure Python Interpreter**:
   - File → Settings → Project → Python Interpreter
   - Add existing environment: `.venv/bin/python`
2. **Mark Sources Root**: Right-click project root → Mark Directory as → Sources Root
3. **Test Configuration**: PyCharm will auto-detect pytest configuration

### Test Coverage
```bash
# Install coverage tool
pip install pytest-cov

# Run tests with coverage report
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m pytest tests/ --cov=server --cov-report=html

# View coverage report
open htmlcov/index.html
```

# API Endpoint Specifications

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

# Special Considerations

## Environment Variables
Set these environment variables for full functionality:
```bash
# Required for LLM functionality
LLM_API_KEY=your_openai_api_key_here
LLM_API_BASE=https://api.openai.com/v1  # Optional, defaults to OpenAI

# Database (auto-configured in development)
DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db
```

## Performance Considerations

### DAG Workflow Scalability
- **Node Limit**: Tested up to 500 nodes with acceptable performance (<2s scheduling)
- **Edge Limit**: Handles up to 1000 edges with cycle detection in <1s
- **Concurrent Execution**: Maximum 2 jobs per workflow, 20 global queue limit
- **Memory Usage**: ~50MB baseline, +2MB per 100 workflow nodes

### File Processing Limits
- **PDF Size**: Maximum 10MB per file
- **Text Extraction**: Up to 100,000 characters per PDF
- **Concurrent Uploads**: Limited to 5 simultaneous uploads
- **Storage**: Uses local filesystem (`uploads/` directory)

### LLM Integration
- **Rate Limiting**: Respects OpenAI rate limits with exponential backoff
- **Timeout**: 60-second timeout per LLM call
- **Token Limits**: Configurable per node (default: 150 tokens)
- **Error Handling**: Graceful degradation on API failures

## Security Considerations

### API Security
- **Input Validation**: All endpoints validate request schemas
- **SQL Injection**: Protected via SQLAlchemy ORM parameterized queries
- **File Upload**: MIME type validation and size limits
- **CORS**: Configured for development (localhost:3000)

### Data Privacy
- **PII Redaction**: Automatic redaction in logs (emails, phones, SSNs)
- **API Key Storage**: Environment variables only, never logged
- **Database Security**: Standard PostgreSQL security practices
- **File Access**: Local filesystem with restricted permissions

## Development Considerations

### Hot Reload & Development
- **Backend**: Uvicorn auto-reload on code changes
- **Frontend**: Vite HMR for instant UI updates
- **Database**: PostgreSQL with persistent volumes
- **Logging**: Structured JSON logging for debugging

### Production Deployment
- **Database**: PostgreSQL 12+ recommended for production
- **Container**: Docker images available for deployment
- **Environment**: Set production environment variables
- **Monitoring**: Structured logs compatible with log aggregation

### Known Limitations
- **Single Tenant**: No multi-tenancy support
- **Authentication**: No built-in authentication system
- **File Storage**: Local filesystem only (no cloud storage)
- **Workflow Versioning**: No version control for workflows

## Data Model & Architecture

### Database Schema
The application uses PostgreSQL with the following core tables:

**workflows**
- `id` (TEXT PK) - Unique workflow identifier
- `name` (TEXT) - Human-readable workflow name
- `created_at` (DATETIME) - Creation timestamp

**nodes**
- `id` (TEXT PK) - Unique node identifier
- `workflow_id` (TEXT FK → workflows.id) - Parent workflow
- `node_type` (TEXT) - Node type: `extract_text` | `generative_ai` | `formatter` | `agent`
- `config_json` (TEXT) - Node configuration as JSON
- `order_index` (INTEGER) - Linear execution order (fallback)

**edges** (NEW)
- `id` (TEXT PK) - Unique edge identifier
- `workflow_id` (TEXT FK → workflows.id) - Parent workflow
- `from_node_id` (TEXT FK → nodes.id) - Source node
- `to_node_id` (TEXT FK → nodes.id) - Target node
- `from_port` (TEXT) - Source port (default: "output")
- `to_port` (TEXT) - Target port (default: "input")
- `condition` (TEXT, NULLABLE) - Conditional edge logic

**jobs**
- `id` (TEXT PK) - Unique job identifier
- `workflow_id` (TEXT FK → workflows.id) - Parent workflow
- `status` (TEXT) - Job status: `Pending` | `Running` | `Succeeded` | `Failed`
- `final_output` (TEXT, NULLABLE) - Final workflow output
- `error_message` (TEXT, NULLABLE) - Error details if failed
- `started_at` (DATETIME) - Execution start time
- `finished_at` (DATETIME, NULLABLE) - Execution completion time

**files**
- `id` (TEXT PK) - Unique file identifier
- `filename` (TEXT) - Original filename
- `mime_type` (TEXT) - File MIME type
- `size_bytes` (INTEGER) - File size in bytes
- `path` (TEXT) - Storage path
- `created_at` (DATETIME) - Upload timestamp

### Configuration & Network
- **Backend Port**: 8000 (configurable)
- **Frontend Port**: 3000 (configurable)
- **CORS**: Configured for `http://localhost:3000`
- **Database**: PostgreSQL on port 5432

# Additional Development Information

## Alternative Deployment Options

### Docker Development (Full Containerization)
```bash
# From repo root - everything containerized
docker compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# PostgreSQL: localhost:5432
```
Dev compose mounts source directories and enables hot reload (backend) and HMR (frontend).

### Production Build
```bash
# Frontend static build
cd client
VITE_API_BASE=https://api.example.com npm run build
# Upload client/dist to your static host

# Backend production
# Use production PostgreSQL instance
# Set production environment variables
```

## Troubleshooting

### Common Development Issues

**"Unresolved reference 'fastapi'" in PyCharm**
- Configure Python interpreter to use `.venv/bin/python`
- Mark project root as Sources Root
- Ensure virtual environment is activated: `source .venv/bin/activate`

**Import errors when running tests**
- Use `PYTHONPATH=.` when running pytest
- Ensure database is running: `docker compose up -d postgres`

**Frontend blank page or startup error**
- Ensure `client/index.html` exists with `<div id="root"></div>`
- Ensure `client/src/main.tsx` renders `<App />` to `#root`
- Run `npm install` again if dependencies changed

**Backend not responding**
- Confirm Uvicorn is running on port 8000
- Terminal should show FastAPI app started and routes registered
- Check database connection: `docker compose ps postgres`

**CORS issues**
- Check `server/main.py` CORS settings include `http://localhost:3000`
- Verify frontend is running on expected port

**Database connection issues**
- Ensure PostgreSQL is running: `docker compose up -d postgres`
- Check DATABASE_URL environment variable
- Verify database migrations are applied: `alembic upgrade head`

**File upload issues**
- Check `uploads/` directory exists and is writable
- Verify PDF file size is under 10MB
- Ensure file is valid PDF format

### Performance Issues

**Slow workflow execution**
- Check LLM API key configuration
- Verify network connectivity to OpenAI
- Monitor system resources during large DAG execution

**High memory usage**
- Large DAGs (>200 nodes) may consume significant memory
- Consider breaking complex workflows into smaller components

---

## License
For assignment use only.
