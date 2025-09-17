# Milestone 1: Persist workflows in Postgres (JSONB) with Alembic and run history

Feature Branch: `002-title-milestone-1`
Status: Draft
Input: User description: "Replace in-memory storage with PostgreSQL (JSONB). Keep existing API contracts unchanged. Add run history. Use Alembic for migrations. TEXT for node_type. No JSONB GIN initially. Add pgAdmin for development only."

## Scope
- Replace in-memory data with persistent storage in PostgreSQL using JSONB for flexible node/run configurations.
- Preserve existing REST API contracts and responses on the backend.
- Record workflow execution history (runs and per-node steps) to support auditability and future async execution.
- Development convenience: provide pgAdmin service (dev-only) for inspecting data.

Out of scope for this milestone:
- Asynchronous execution and background processing.
- GENERATIVE_AI, FORMATTER, and PDF text extraction nodes (delivered in subsequent milestones).

## User Scenarios & Testing

### Primary User Story
As a user, I want the workflows and their nodes to persist across server restarts and I want to view execution history, so that I can trust the system state and audit previous runs.

### Acceptance Scenarios
1. Given a clean system, when a user creates a workflow, then the workflow is assigned an ID and is persisted in the database.
2. Given an existing workflow, when a user fetches the workflow by ID, then the response includes its persisted name and the full list of nodes with their saved configuration.
3. Given an existing workflow, when a user adds a node with a JSON configuration, then the node is persisted (including its JSON configuration) and appears in subsequent reads in the correct order.
4. Given a workflow with nodes, when the user triggers a run, then a run record is created and persisted, including status and final output. Per-node step records are also persisted for audit.
5. Given persisted data, when the service restarts, then previously created workflows, nodes, and run history remain available via the same API endpoints.

### Edge Cases
- Invalid workflow ID requested: API returns 404 without exposing internal details.
- Invalid node payload (e.g., malformed JSON): API returns 422 with validation errors.
- Run execution error: run is persisted with FAILED status and error message (final output may be null).

## Functional Requirements
- FR-001: The system MUST persist workflows (id, name, timestamps) in PostgreSQL.
- FR-002: The system MUST persist nodes linked to workflows with an ordered position and a JSON configuration.
- FR-003: The system MUST persist run history for each workflow, including status, timing, and final output.
- FR-004: The system MUST persist per-node run step records linked to a run, including node type, captured config snapshot, status, timing, and input/output text where applicable.
- FR-005: Existing API contracts and response models MUST remain unchanged for create/get/add-node/run.
- FR-006: The system MUST validate `node_type` values in the application layer (TEXT stored in DB; enforced via Enum in request/response schemas).
- FR-007: The system MUST use Alembic for schema migrations and provide an initial migration that creates the required tables and indexes.
- FR-008: The system SHOULD provide a development-only pgAdmin service for DB inspection (no production dependency implied).
- FR-009: The system SHOULD avoid JSONB GIN indexes initially; revisit when JSON field querying becomes a performance need.

## Key Entities
- Workflow: represents a user-defined workflow (id, name, created_at, updated_at).
- Node: represents a step within a workflow (id, workflow_id, node_type as TEXT, config as JSONB, order, created_at).
- Run: represents a workflow execution (id, workflow_id, status, started_at, finished_at, error_message, final_output).
- RunNode (Run Step): represents a per-node execution step within a run (id, run_id, node_id (optional), node_type, config_json as JSONB, status, started_at, finished_at, input_text, output_text, error_message).

## Non-Functional & Constraints
- Database: PostgreSQL with JSONB for flexible configuration fields.
- Configuration: `DATABASE_URL` configured for the backend; dev docker-compose includes `postgres` and `pgadmin` services.
- Data integrity: foreign keys between workflows→nodes and runs→run_nodes.
- Indexing: initial B-tree indexes on `nodes(workflow_id, order)` and `runs(workflow_id, started_at DESC)`.
- Compatibility: keep Pydantic schemas and API interfaces stable for the client.

## Review & Acceptance Checklist
- [x] No changes required for existing client API usage.
- [x] Data persists across restarts.
- [x] Run history is captured and queryable via existing or minimal new endpoints.
- [x] Alembic initial migration exists and can be applied end-to-end in the dev environment.
- [x] pgAdmin is available in development for verification.

