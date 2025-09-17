---
title: Data Model – Optional DAG Workflows & AI Agent Node
branch: 004-description-optional-support
date: 2025-09-17
spec: ./spec.md
---

## Entities

### Workflow
- id: string (UUID)
- name: string (unique within project scope)
- created_at: datetime
- updated_at: datetime
- policies: object (branch failure policy: fail-fast | continue-others | custom)

### Node
- id: string (UUID)
- workflow_id: string (FK → Workflow.id)
- node_type: enum(`extract_text` | `generative_ai` | `formatter` | `agent`)
- config: object (typed per node_type)
- created_at: datetime
- order_index: integer (legacy; optional when full DAG edges exist)

### Edge
- id: string (UUID)
- workflow_id: string (FK → Workflow.id)
- from_node_id: string (FK → Node.id)
- from_port: string
- to_node_id: string (FK → Node.id)
- to_port: string
- condition?: string (optional expression)

### Run
- id: string (UUID)
- workflow_id: string
- status: enum(`Pending` | `Running` | `Succeeded` | `Failed`)
- started_at: datetime
- finished_at?: datetime
- final_output?: string
- error_message?: string

### NodeRun
- id: string (UUID)
- run_id: string (FK → Run.id)
- node_id?: string (FK → Node.id)
- node_type: string
- status: enum
- started_at: datetime
- finished_at?: datetime
- input_text?: string
- output_text?: string
- error_message?: string

### Job
- id: string (UUID)
- workflow_id: string (FK → Workflow.id)
- status: enum
- started_at: datetime
- finished_at?: datetime
- error_message?: string
- final_output?: string

### JobStep
- id: string (UUID)
- job_id: string (FK → Job.id)
- node_id?: string (FK → Node.id)
- node_type: string
- status: enum
- started_at: datetime
- finished_at?: datetime
- input_text?: string
- output_text?: string
- error_message?: string
- config_snapshot?: object

### UploadedFile
- id: string (UUID)
- filename: string
- mime_type: string (PDF only)
- size_bytes: int (≤ 10MB)
- file_path: string
- created_at: datetime

## Validation Rules
- Graph must be a DAG (no cycles) – validate on save and run.
- Fan-in uses AND-join by default; all required inputs must arrive.
- Edges must connect existing nodes and valid ports.
- Agent limits: ≤10 concurrent ops, 30s timeout/tool call, retries 3 with backoff.
- Redact sensitive fields in persisted logs/metadata.

## State Transitions
- Job/Run: Pending → Running → Succeeded | Failed
- NodeRun/JobStep: Pending → Running → Succeeded | Failed


