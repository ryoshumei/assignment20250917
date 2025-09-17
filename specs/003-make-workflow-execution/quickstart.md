# Async Workflow Execution - Quickstart Guide

## Overview
This guide demonstrates the complete async workflow execution system with PDF processing, LLM integration, and text formatting.

## Prerequisites
- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:3000` (optional)
- PostgreSQL database running
- OpenAI API key configured in environment (`LLM_API_KEY`)

## Quick Start Workflow

### 1) Setup Environment
```bash
# Set required environment variables
export LLM_API_KEY="your_openai_api_key_here"
export DATABASE_URL="postgresql://postgres:password@localhost:5432/workflow_db"

# Start services
docker compose up -d postgres
uvicorn server.main:app --reload --port 8000
```

### 2) Create a Workflow
```bash
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"name": "PDF Processing Demo"}'
```
**Response**: `{ "id": "workflow-uuid", "name": "PDF Processing Demo" }`

### 3) Upload a PDF File
```bash
curl -X POST http://localhost:8000/files \
  -F "file=@your_document.pdf"
```
**Response**: `{ "file_id": "file-uuid", "filename": "your_document.pdf", "message": "File uploaded successfully" }`

### 4) Add Processing Nodes (In Order)

#### 4a) Extract Text Node
```bash
curl -X POST http://localhost:8000/workflows/{workflow_id}/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "extract_text",
    "config": { "file_id": "file-uuid" }
  }'
```

#### 4b) Generative AI Node (OpenAI Processing)
```bash
curl -X POST http://localhost:8000/workflows/{workflow_id}/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "generative_ai",
    "config": {
      "model": "gpt-4.1-mini",
      "prompt": "Summarize the following text in 2-3 sentences: {text}",
      "temperature": 0.7,
      "max_tokens": 150
    }
  }'
```

#### 4c) Formatter Node (Text Processing)
```bash
curl -X POST http://localhost:8000/workflows/{workflow_id}/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "formatter",
    "config": {
      "rules": ["lowercase", "full_to_half"]
    }
  }'
```

### 5) Execute Workflow Asynchronously
```bash
curl -X POST http://localhost:8000/workflows/{workflow_id}/run
```
**Response**: `{ "job_id": "job-uuid", "message": "Job queued successfully" }`

### 6) Monitor Job Progress
```bash
# Poll job status
curl http://localhost:8000/jobs/{job_id}
```

**Response States**:
- `Pending`: Job queued, waiting to start
- `Running`: Job executing, processing nodes
- `Succeeded`: Job completed successfully
- `Failed`: Job encountered an error

**Successful Response**:
```json
{
  "id": "job-uuid",
  "workflow_id": "workflow-uuid",
  "status": "Succeeded",
  "started_at": "2025-01-15T10:30:00Z",
  "finished_at": "2025-01-15T10:30:15Z",
  "final_output": "this document discusses workflow automation and ai processing systems. it covers integration patterns and execution models for document processing workflows.",
  "error_message": null
}
```

### 7) View Job History
```bash
curl http://localhost:8000/workflows/{workflow_id}/runs
```
**Response**: `{ "runs": [Job, Job, ...] }`

## Frontend Usage (Alternative)

### Using the Web Interface
1. Open `http://localhost:3000`
2. Create a new workflow
3. Upload a PDF file using the file input
4. Configure and add nodes:
   - **Extract Text**: Automatically uses uploaded file
   - **Generative AI**: Configure model, prompt, and parameters
   - **Formatter**: Select transformation rules
5. Click "Run Workflow Async"
6. Monitor job status in real-time
7. View results and job history

## Advanced Features

### Concurrency Control
- **Max Running Jobs**: 2 per workflow
- **Queue Limit**: 20 jobs (FIFO)
- **Rate Limiting**: HTTP 429 when queue is full

### Error Handling
```bash
# Check failed job details
curl http://localhost:8000/jobs/{failed_job_id}
```
Common errors:
- File not found
- Invalid LLM configuration
- API rate limits
- Malformed PDF files

### Performance Expectations
- **Job Startup**: < 2 seconds
- **PDF Processing**: < 5 seconds (typical documents)
- **LLM Processing**: 5-30 seconds (depending on content size)
- **Text Formatting**: < 1 second
- **Status Polling**: < 1 second per request

### Supported Models
- `gpt-4.1-mini` (recommended for speed)
- `gpt-4o` (balanced performance)
- `gpt-5` (highest quality)

### Formatter Rules
- `lowercase`: Convert to lowercase
- `uppercase`: Convert to uppercase
- `full_to_half`: Full-width → half-width characters
- `half_to_full`: Half-width → full-width characters

## Troubleshooting

### Common Issues
1. **"LLM API key not configured"**
   - Set `LLM_API_KEY` environment variable

2. **"File not found" errors**
   - Ensure PDF was uploaded successfully
   - Use correct `file_id` in extract_text config

3. **Job stuck in "Pending"**
   - Check concurrency limits (max 2 running jobs)
   - Verify database connectivity

4. **PDF upload fails**
   - Check file size (< 10MB)
   - Ensure valid PDF format
   - Verify MIME type is `application/pdf`

### Monitoring
```bash
# Check system health
curl http://localhost:8000/docs  # API documentation

# Database status
docker compose ps postgres
```

## Integration Examples

### Batch Processing
```bash
# Process multiple PDFs
for pdf in *.pdf; do
  FILE_ID=$(curl -X POST http://localhost:8000/files -F "file=@$pdf" | jq -r .file_id)
  # ... create workflow and process
done
```

### Custom Prompts
```json
{
  "node_type": "generative_ai",
  "config": {
    "model": "gpt-4o",
    "prompt": "Extract key insights from this document: {text}. Focus on: 1) Main topics 2) Action items 3) Important dates",
    "temperature": 0.3,
    "max_tokens": 300
  }
}
```

This completes the async workflow execution system with full PDF processing, LLM integration, and real-time job monitoring capabilities.
