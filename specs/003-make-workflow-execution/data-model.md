# Data Model

## Entities

### Workflow
- id: string (UUID)
- name: string
- created_at: datetime
- updated_at: datetime

### Node
- id: string (UUID)
- workflow_id: string (FK → Workflow)
- node_type: enum { extract_text, generative_ai, formatter }
- order: integer (position)
- config: JSON (type-specific)
- created_at: datetime

### Job (Run)
- id: string (UUID)
- workflow_id: string (FK → Workflow)
- status: enum { Pending, Running, Succeeded, Failed }
- started_at: datetime
- finished_at: datetime | null
- error_message: string | null
- final_output: string | null

### JobStep (Run Step)
- id: string (UUID)
- job_id: string (FK → Job)
- node_id: string (FK → Node) | null
- node_type: enum (copy from Node)
- config_snapshot: JSON
- status: enum { Pending, Running, Succeeded, Failed }
- started_at: datetime
- finished_at: datetime | null
- input_text: string | null
- output_text: string | null
- error_message: string | null

### UploadedFile
- id: string (UUID)
- filename: string
- mime_type: string (must be application/pdf)
- size_bytes: integer (<= 10MB)
- path: string (local storage)
- created_at: datetime

## Relationships
- Workflow 1—N Node (ordered by `order`)
- Workflow 1—N Job
- Job 1—N JobStep (ordered by execution)
- UploadedFile referenced by Node.config for EXTRACT_TEXT

## Validation Rules
- Node.node_type must be one of allowed values
- FORMATTER rules array executes in order; unknown rules rejected
- GENERATIVE_AI requires prompt and model; optional params capped
- UploadedFile MIME must be application/pdf; size <= 10MB
- Job status transitions: Pending→Running→(Succeeded|Failed) (no loops)
