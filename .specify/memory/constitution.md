# Workflow Web App Constitution

## Core Principles

### I. Persistence-First (Minimal)
All workflow, node, job, and file metadata must be persisted in a datastore (no in-memory single source of truth).
- Datastore: SQLite (single file, zero-ops) for the minimal requirement; swappable later.
- Minimal migrations are acceptable (handwritten schema or lightweight scripts).

### II. Async Job Execution
Workflow execution is always asynchronous.
- Run returns a job_id immediately; clients poll job status/results.
- States: Pending, Running, Succeeded, Failed; include error message on failure.
- Minimal implementation can use FastAPI background tasks; no external brokers required.

### III. Minimal Node Contract
Provide three built-in node types with serializable configs:
- NodeType.EXTRACT_TEXT: extract text from uploaded PDF files.
- NodeType.GENERATIVE_AI: call an LLM with configurable prompt/model and optional params.
- NodeType.FORMATTER: format text (e.g., upper/lower/normalize) based on rules.
Nodes behave as pure transformations: input → process(config) → output.

### IV. Minimal REST API
Keep endpoints simple and debuggable:
- Workflows: POST /workflows, GET /workflows/{id}, POST /workflows/{id}/nodes
- Run: POST /workflows/{id}/run → { job_id }
- Jobs: GET /jobs/{job_id} → { status, result?, error? }
- Upload: POST /files (PDF only) → { file_id }
Enable CORS; return clear error messages; limit file size and MIME.

### V. Observability & Security (Just Enough)
“Just Enough” means only the minimal set needed for usability, debugging, and a safety baseline—no over-engineering.
- Observability: structured logs with request_id/job_id, node type, state, latency; errors include stack traces.
- Basic metrics (if available): request latency/count, job success/failure, external LLM latency/errors.
- Security: secrets via env vars; do not log secrets or full prompts; PDF-only uploads with size/MIME checks; least-privilege write access; scoped CORS for dev.

## Technology & Constraints
- Backend: FastAPI (Python 3.11+), async-first.
- Datastore: SQLite (SQLAlchemy or minimal SQL), single-file persistence.
- LLM: OpenAI-compatible API configurable via env (LLM_API_BASE, LLM_API_KEY).
- PDF extraction: PyPDF2 (or minimal equivalent); only .pdf accepted.
- HTTP client: httpx (async).
- Frontend: React + Vite; minimal UI to create/view workflows, add nodes, upload PDF, run, and poll job result.
- File storage: local uploads/ directory; max 10MB; PDF MIME only.
- Minimal schema: tables/collections for workflows, nodes, jobs, files.

## Development Workflow & Quality Gates
- PR & review: every change via PR; reviewer checks compliance with this constitution.
- Must-pass checks locally: app starts; can create/get workflow; can add all three node types; can upload PDF; can run and retrieve result via GET /jobs/{id}.
- Documentation: README must include setup/run, endpoint specs, env vars, known limits, and time spent.
- Versioning: SemVer; breaking changes require explicit notice and migration guidance.

## Governance
This constitution supersedes other practices. Amendments require:
- Documented motivation, impact, and migration plan in a PR;
- Reviewer confirmation that complexity is necessary (YAGNI guardrail);
- Verified runability and observability of changes.
Runtime development guidance follows the project README.

**Version**: 0.1.0 | **Ratified**: 2025-09-17 | **Last Amended**: 2025-09-17