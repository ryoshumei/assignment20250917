# Quickstart: Workflow App with PostgreSQL Persistence

This quickstart guide demonstrates how to use the Workflow App with full PostgreSQL persistence and run history tracking.

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+

## Quick Start

### 1. Start the Development Environment

```bash
# Start PostgreSQL database
docker compose up -d postgres

# Wait for database to be healthy
docker compose ps postgres

# Install dependencies and start backend
cd server
python3 -m pip install -r requirements.txt
cd ..

# Apply database migrations
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m alembic upgrade head

# Start backend server
cd server
PYTHONPATH=.. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start Frontend (Optional)

```bash
# In a new terminal
cd client
npm install
npm run dev
```

### 3. Access the Application

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000 (if started)
- **pgAdmin**: http://localhost:5050 (if started with `docker compose --profile dev up`)

## API Usage Examples

### Create a Workflow

```bash
curl -X POST "http://localhost:8000/workflows" \
  -H "Content-Type: application/json" \
  -d '{"name": "Document Processing Pipeline"}'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Document Processing Pipeline"
}
```

### Add Nodes to Workflow

```bash
# Add text extraction node
curl -X POST "http://localhost:8000/workflows/550e8400-e29b-41d4-a716-446655440000/nodes" \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "extract_text",
    "config": {"source": "document.pdf"}
  }'

# Add AI processing node
curl -X POST "http://localhost:8000/workflows/550e8400-e29b-41d4-a716-446655440000/nodes" \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "generative_ai",
    "config": {"prompt": "Summarize this document", "model": "gpt-4"}
  }'

# Add formatting node
curl -X POST "http://localhost:8000/workflows/550e8400-e29b-41d4-a716-446655440000/nodes" \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "formatter",
    "config": {"format": "json"}
  }'
```

### View Workflow

```bash
curl "http://localhost:8000/workflows/550e8400-e29b-41d4-a716-446655440000"
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Document Processing Pipeline",
  "nodes": [
    {
      "id": "node-1",
      "node_type": "extract_text",
      "config": {"source": "document.pdf"}
    },
    {
      "id": "node-2",
      "node_type": "generative_ai",
      "config": {"prompt": "Summarize this document", "model": "gpt-4"}
    },
    {
      "id": "node-3",
      "node_type": "formatter",
      "config": {"format": "json"}
    }
  ]
}
```

### Execute Workflow

```bash
curl -X POST "http://localhost:8000/workflows/550e8400-e29b-41d4-a716-446655440000/run"
```

Response:
```json
{
  "final_output": "[EXTRACTED] [GEN_AI with prompt='Summarize this document']: INITIAL TEXT FROM SOME DOC ..."
}
```

### View Run History

```bash
# List all runs for a workflow
curl "http://localhost:8000/workflows/550e8400-e29b-41d4-a716-446655440000/runs"
```

Response:
```json
{
  "runs": [
    {
      "id": "run-123",
      "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "Succeeded",
      "started_at": "2025-09-17T12:00:00Z",
      "finished_at": "2025-09-17T12:00:05Z",
      "final_output": "[EXTRACTED] [GEN_AI with prompt='Summarize this document']: ..."
    }
  ]
}
```

### View Detailed Run Information

```bash
# Get detailed run information with per-node steps
curl "http://localhost:8000/runs/run-123"
```

Response:
```json
{
  "run": {
    "id": "run-123",
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "Succeeded",
    "started_at": "2025-09-17T12:00:00Z",
    "finished_at": "2025-09-17T12:00:05Z",
    "final_output": "..."
  },
  "steps": [
    {
      "id": "step-1",
      "run_id": "run-123",
      "node_id": "node-1",
      "node_type": "extract_text",
      "status": "Succeeded",
      "started_at": "2025-09-17T12:00:01Z",
      "finished_at": "2025-09-17T12:00:02Z",
      "input_text": "Initial text from some doc ...",
      "output_text": "[EXTRACTED] Initial text from some doc ..."
    },
    {
      "id": "step-2",
      "run_id": "run-123",
      "node_id": "node-2",
      "node_type": "generative_ai",
      "status": "Succeeded",
      "started_at": "2025-09-17T12:00:02Z",
      "finished_at": "2025-09-17T12:00:04Z",
      "input_text": "[EXTRACTED] Initial text from some doc ...",
      "output_text": "[GEN_AI with prompt='Summarize this document']: [EXTRACTED] Initial text from some doc ..."
    },
    {
      "id": "step-3",
      "run_id": "run-123",
      "node_id": "node-3",
      "node_type": "formatter",
      "status": "Succeeded",
      "started_at": "2025-09-17T12:00:04Z",
      "finished_at": "2025-09-17T12:00:05Z",
      "input_text": "[GEN_AI with prompt='Summarize this document']: [EXTRACTED] Initial text from some doc ...",
      "output_text": "[GEN_AI WITH PROMPT='SUMMARIZE THIS DOCUMENT']: [EXTRACTED] INITIAL TEXT FROM SOME DOC ..."
    }
  ]
}
```

## Key Features

### ✅ **PostgreSQL Persistence**
- All workflows, nodes, and run history are persisted in PostgreSQL
- Survives application restarts
- JSONB storage for flexible node configurations

### ✅ **Complete Run History**
- Every workflow execution is recorded with timestamps
- Individual node execution steps are tracked
- Input/output tracking for debugging and audit trails
- Error handling and failure tracking

### ✅ **Structured Logging**
- Request IDs for request tracing
- Run IDs and node execution logging
- Comprehensive audit trail in application logs

### ✅ **Development Tools**
- pgAdmin for database management (http://localhost:5050)
- OpenAPI documentation (http://localhost:8000/docs)
- Docker Compose for easy setup

## Database Schema

The application uses 4 main tables:

- **workflows**: Workflow metadata
- **nodes**: Node definitions with JSONB configurations
- **runs**: Workflow execution records
- **run_nodes**: Individual node execution steps

## Configuration

### Environment Variables

Create a `.env` file (see `.env.example`):

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db
LOG_LEVEL=INFO
```

### Database Management

```bash
# Create new migration after model changes
PYTHONPATH=. python3 -m alembic revision --autogenerate -m "Description"

# Apply migrations
PYTHONPATH=. python3 -m alembic upgrade head

# View migration history
PYTHONPATH=. python3 -m alembic history
```

## Testing

### Run All Tests

```bash
# Contract tests (API endpoint validation)
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m pytest tests/contract/ -v

# Integration tests (persistence and run history)
PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m pytest tests/integration/ -v

# Unit tests (model validation)
PYTHONPATH=. python3 -m pytest tests/unit/ -v
```

## Troubleshooting

### Database Connection Issues

1. Ensure PostgreSQL is running: `docker compose ps postgres`
2. Check database logs: `docker compose logs postgres`
3. Verify connection: `docker compose exec postgres psql -U postgres -d workflow_db -c "SELECT 1;"`

### Migration Issues

1. Check current migration status: `PYTHONPATH=. python3 -m alembic current`
2. View migration history: `PYTHONPATH=. python3 -m alembic history`
3. Reset to latest: `PYTHONPATH=. python3 -m alembic upgrade head`

### API Issues

1. Check application logs for request IDs and error details
2. Verify API endpoints at http://localhost:8000/docs
3. Test with simple curl commands from this guide

## Next Steps

- Explore the OpenAPI documentation at http://localhost:8000/docs
- Use pgAdmin to explore the database schema
- Create more complex workflows with different node configurations
- Monitor run history and performance through the API