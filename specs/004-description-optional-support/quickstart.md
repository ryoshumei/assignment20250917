---
title: Quickstart – Optional DAG Workflows & AI Agent Node
branch: 004-description-optional-support
date: 2025-09-17
spec: ./spec.md
---

## Prerequisites
- Python 3.11+, Node.js 18+
- Docker (for Postgres dev) or SQLite for minimal mode

## Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt

# Apply migrations (if using Postgres as in README)
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m alembic upgrade head

# Start API
cd server
PYTHONPATH=.. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m uvicorn main:app --reload --port 8000
```

## Frontend
```bash
cd client
npm install
npm run dev
# Open http://localhost:3000
```

## Validate User Scenarios

### Basic Linear Workflow
```bash
# 1) Create workflow
curl -s http://localhost:8000/workflows -X POST -H 'Content-Type: application/json' -d '{"name":"linear-demo"}'

# 2) Add nodes (extract_text → generative_ai → formatter)
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{"node_type":"extract_text","config":{"file_id":"<pdf_id>"}}'
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{"node_type":"generative_ai","config":{"model":"gpt-4.1-mini","prompt":"Summarize: {text}"}}'
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{"node_type":"formatter","config":{"rules":["uppercase"]}}'

# 3) Run (async)
curl -s http://localhost:8000/workflows/{wf_id}/run

# 4) Poll job status
curl -s http://localhost:8000/jobs/{job_id}
```

### DAG Workflow with Edges
```bash
# 1) Create workflow
curl -s http://localhost:8000/workflows -X POST -H 'Content-Type: application/json' -d '{"name":"dag-demo"}'

# 2) Add nodes for diamond pattern
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{"node_type":"extract_text","config":{"file_id":"<pdf_id>"}}' | jq -r '.node_id'  # → node_a
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{"node_type":"generative_ai","config":{"model":"gpt-4.1-mini","prompt":"Summarize: {text}"}}' | jq -r '.node_id'  # → node_b
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{"node_type":"formatter","config":{"rules":["lowercase"]}}' | jq -r '.node_id'  # → node_c
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{"node_type":"formatter","config":{"rules":["uppercase"]}}' | jq -r '.node_id'  # → node_d

# 3) Create edges (A→B, A→C, B→D, C→D diamond pattern)
curl -s http://localhost:8000/workflows/{wf_id}/edges -X POST -H 'Content-Type: application/json' -d '{"from_node_id":"{node_a}","to_node_id":"{node_b}"}'
curl -s http://localhost:8000/workflows/{wf_id}/edges -X POST -H 'Content-Type: application/json' -d '{"from_node_id":"{node_a}","to_node_id":"{node_c}"}'
curl -s http://localhost:8000/workflows/{wf_id}/edges -X POST -H 'Content-Type: application/json' -d '{"from_node_id":"{node_b}","to_node_id":"{node_d}"}'
curl -s http://localhost:8000/workflows/{wf_id}/edges -X POST -H 'Content-Type: application/json' -d '{"from_node_id":"{node_c}","to_node_id":"{node_d}"}'

# 4) Verify edges (should show 4 edges, no cycles)
curl -s http://localhost:8000/workflows/{wf_id}/edges

# 5) Run DAG workflow (executes with topological scheduling)
curl -s http://localhost:8000/workflows/{wf_id}/run

# 6) Poll job status
curl -s http://localhost:8000/jobs/{job_id}
```

### Agent Node Workflow
```bash
# 1) Create workflow with agent
curl -s http://localhost:8000/workflows -X POST -H 'Content-Type: application/json' -d '{"name":"agent-demo"}'

# 2) Add agent node with bounded execution
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{
  "node_type":"agent",
  "config":{
    "objective":"Process and format text efficiently",
    "tools":["llm_call","formatter"],
    "budgets":{"execution_time":30},
    "max_concurrent":2,
    "timeout_seconds":25,
    "max_retries":2,
    "max_iterations":3,
    "formatting_rules":["lowercase"]
  }
}'

# 3) Run agent workflow
curl -s http://localhost:8000/workflows/{wf_id}/run

# 4) Monitor with detailed status
curl -s http://localhost:8000/jobs/{job_id}
```

## Notes

### DAG Workflow Features
- **Cycle Detection**: Automatic validation prevents circular dependencies
- **Topological Scheduling**: Nodes execute in dependency order with maximum parallelism
- **AND-join Semantics**: Downstream nodes wait for ALL upstream dependencies
- **Input Aggregation**: Multi-input nodes receive concatenated outputs (alphabetically sorted)
- **Parallel Execution**: Independent nodes run concurrently within execution batches

### Agent Node Features
- **Bounded Execution**: Configurable limits on iterations, time, and concurrent operations
- **Tool Whitelisting**: Restricted to `llm_call` and `formatter` tools only
- **Policy Enforcement**: max_concurrent ≤ 10, timeout_seconds ≤ 30, max_retries ≤ 3
- **Structured Logging**: Comprehensive execution tracking with PII redaction
- **Retry Logic**: Exponential backoff for transient failures

### Frontend Constraints
- **Extract Text Node**: Requires PDF file upload before node can be added
- **Generative AI Node**: Always available, no upload requirement
- **Agent Node**: Configure objective, tools, and budget constraints in UI


