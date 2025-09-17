---
title: Tasks – Optional DAG Workflows & AI Agent Node
feature_dir: /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/specs/004-description-optional-support
branch: 004-description-optional-support
date: 2025-09-17
source_docs:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/specs/004-description-optional-support/plan.md
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/specs/004-description-optional-support/data-model.md
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/specs/004-description-optional-support/contracts/openapi.yaml
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/specs/004-description-optional-support/research.md
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/specs/004-description-optional-support/quickstart.md
---

## Overview
This tasks.md is dependency-ordered and parallel-ready [P]. Follow TDD: write tests first, then implement.

## Parallel Execution Guidance
- [P] means tasks can run concurrently because they touch different files or test-only files.
- Group [P] tasks with separate shells/tmux panes.
- Example commands shown per task (adapt paths as needed).

## Environment Setup

T001. Backend/Frontend environment ready [P]
- Files: N/A
- Commands:
  - python3 -m venv .venv && source .venv/bin/activate && pip install -r /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/requirements.txt
  - (optional) cd /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/client && npm ci
- Accept:
  - pip installs succeed; optional npm install succeeds.

## Contracts & Tests (before implementation)

T002. Extend OpenAPI contracts for DAG edges
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/specs/004-description-optional-support/contracts/openapi.yaml
- Changes:
  - Add endpoints:
    - POST /workflows/{id}/edges: create edge(s) with validation errors on invalid node refs or cycles
    - GET /workflows/{id}/edges: list edges for workflow
  - Ensure `node_type` enum includes `agent` (already present); no breakage.
- Accept:
  - OpenAPI validates (basic YAML lint) and documents new endpoints and schemas.

T003. Add contract test for POST /workflows/{id}/edges [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/contract/test_workflows_edges_post.py (new)
- Commands:
  - pytest -q /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/contract/test_workflows_edges_post.py -q
- Accept:
  - Fails RED due to missing implementation.

T004. Add contract test for GET /workflows/{id}/edges [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/contract/test_workflows_edges_get.py (new)
- Commands:
  - pytest -q /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/contract/test_workflows_edges_get.py -q
- Accept:
  - Fails RED due to missing implementation.

T005. Add contract test for adding `agent` node type validation [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/contract/test_workflows_nodes_post_agent.py (new)
- Scenarios:
  - Valid agent config (objective, tools whitelist, budgets) → 200 + node_id
  - Invalid config (no tools, timeout > 30s, concurrency > 10) → 400
- Commands:
  - pytest -q /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/contract/test_workflows_nodes_post_agent.py -q
- Accept:
  - Fails RED due to missing validation.

T006. Add integration test: DAG fan-out/fan-in without agent [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/integration/test_dag_fan_in_out.py (new)
- Scenarios:
  - Create workflow; add 3 nodes; add edges forming diamond; run; poll job; expect Succeeded; verify all steps executed once; verify AND-join merge behavior.
- Commands:
  - pytest -q /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/integration/test_dag_fan_in_out.py -q
- Accept:
  - Fails RED pending implementation.

T007. Add integration test: optional Agent node bounded loop [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/integration/test_agent_node.py (new)
- Scenarios:
  - Add agent with tools whitelist (pdf_extract, formatter, llm_call), budgets; run; verify bounded iterations, termination reason present, Succeeded or Failed deterministically.
- Commands:
  - pytest -q /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/integration/test_agent_node.py -q
- Accept:
  - Fails RED pending implementation.

## Data Models & Migrations

T008. Add `EdgeDB` model to DB models (no DTOs)
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/db_models.py
- Changes:
  - Create `edges` table with: id, workflow_id (FK), from_node_id (FK), from_port (str), to_node_id (FK), to_port (str), condition (nullable str), created_at.
  - Relationships: WorkflowDB.edges; NodeDB.inbound_edges/outbound_edges (optional minimal relationships acceptable).
- Dependencies: T003-T004 (tests exist to drive schema), T002 (contract defined)
- Accept:
  - Imports compile; alembic autogen detects table.

T009. Create Alembic migration for edges
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/migrations/versions/<timestamp>_add_edges_table.py (new)
- Commands:
  - cd /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917 && PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m alembic revision -m "add edges table" --autogenerate
  - PYTHONPATH=. DATABASE_URL=postgresql://postgres:password@localhost:5432/workflow_db python3 -m alembic upgrade head
- Dependencies: T008
- Accept:
  - Migration applies cleanly to dev DB.

T010. Extend API schemas/enums for Agent on backend (types only) [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/models.py
- Changes:
  - Add `AGENT = "agent"` to `NodeType` enum.
- Dependencies: none
- Accept:
  - Imports compile; existing tests unaffected.

## Services & Validation

T011. Add `agent_service.py` with config validation and execution policy
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/services/agent_service.py (new)
- Behavior:
  - validate_config(config) → (bool, error_msg)
  - enforce limits: tools whitelist required; ≤10 concurrent ops; per-call timeout ≤30s; retries ≤3 with 1s/2s/4s backoff; budgets present when tools used.
- Accept:
  - Unit tests (see T020) RED until implemented.

T012. Add `graph_service.py` for DAG validation and topological sort
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/services/graph_service.py (new)
- Behavior:
  - validate_edges_no_cycles(workflow_id, edges, nodes) → raises on cycle/invalid refs
  - topo_schedule(edges, nodes) → iterator of ready node batches (AND-join)
- Accept:
  - Unit tests (see T021) RED until implemented.

T013. Wire agent/node validation in `POST /workflows/{wf_id}/nodes`
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/main.py
- Changes:
  - Import agent_service; when `NodeType.AGENT`, call validate_config; return 400 on invalid.
- Dependencies: T010, T011
- Accept:
  - Contract test T005 turns GREEN.

## API Endpoints – Edges

T014. Implement POST /workflows/{wf_id}/edges
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/main.py
- Changes:
  - Add endpoint to upsert or create edges; validate via graph_service.validate_edges_no_cycles; persist EdgeDB rows.
- Dependencies: T008, T009, T012, T002, tests T003
- Accept:
  - Contract test T003 GREEN.

T015. Implement GET /workflows/{wf_id}/edges
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/main.py
- Changes:
  - Return edges list for workflow.
- Dependencies: T014
- Accept:
  - Contract test T004 GREEN.

## Execution Engine – Async Jobs

T016. Update job execution to DAG-based topological scheduling
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/services/job_service.py
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/services/graph_service.py
- Changes:
  - Replace linear `for node in workflow.nodes` with topo batches from graph_service.topo_schedule.
  - Implement AND-join input aggregation: combine upstream outputs deterministically (e.g., join with "\n\n").
- Dependencies: T012, Edge models (T008-T009)
- Accept:
  - Integration test T006 turns GREEN after full pipeline.

T017. Implement Agent node execution with bounded loop
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/services/job_service.py
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/services/agent_service.py
- Changes:
  - Add `_execute_agent_node(config, input_text)` with limits from agent_service; uses llm_service and formatter/pdf tools per whitelist.
- Dependencies: T011, T016
- Accept:
  - Integration test T007 GREEN.

## Frontend (minimal support for new edges & agent type)

T018. Extend client types for `agent` and `Edge`
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/client/src/types.ts
- Changes:
  - Add `agent` to NodeType union; define `Edge` type.
- Accept:
  - TypeScript compiles.

T019. Add API functions for edges
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/client/src/api.ts
- Changes:
  - addEdge(workflowId, edgePayload); getEdges(workflowId)
- Accept:
  - Dev server compiles; manual call works against backend.

## Observability & Safety

T020. Add structured logging and redaction for Agent steps [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/server/services/job_service.py
- Changes:
  - Log request_id/job_id/node_id; redact secrets/PII in inputs/outputs for agent.
- Accept:
  - Logs present during run; no secrets leaked.

## Unit & Perf Tests (Polish)

T021. Unit tests for agent_service validation [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/unit/test_agent_service.py (new)
- Accept:
  - GREEN after T011.

T022. Unit tests for graph_service cycle detection/topo [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/unit/test_graph_service.py (new)
- Accept:
  - GREEN after T012.

T023. Performance test up to 50 nodes with fan-out/fan-in [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/tests/performance/test_dag_performance.py (new)
- Accept:
  - Runtime under agreed threshold; no timeouts; memory stable.

## Docs

T024. Update quickstart with edges + agent examples [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/specs/004-description-optional-support/quickstart.md
- Changes:
  - Add curl examples to create edges and agent node config; note limits.
- Accept:
  - Steps succeed against running backend.

T025. Update feature spec references if needed [P]
- Files:
  - /Users/ryo/PycharmProjects/PythonProject/private/assignment20250917/specs/004-description-optional-support/spec.md
- Changes:
  - Ensure text aligns with final implementation (edges endpoints, agent limits wording).
- Accept:
  - Spec and contracts consistent.

---

## Dependency Order Summary
1) Setup: T001
2) Contracts/Tests (RED): T002 → T003 [P], T004 [P], T005 [P], T006 [P], T007 [P]
3) Models/Migrations: T008 → T009
4) Types/Services: T010 [P] → T011 → T012 → T013
5) Endpoints: T014 → T015
6) Execution Engine: T016 → T017
7) Frontend: T018 [P] → T019
8) Observability: T020 [P]
9) Unit/Perf: T021 [P], T022 [P], T023 [P]
10) Docs: T024 [P], T025 [P]

## Parallel Groups Examples
- Group A [P]: T003, T004, T005, T006, T007
  - Commands:
    - pytest -q tests/contract/test_workflows_edges_post.py & pytest -q tests/contract/test_workflows_edges_get.py & pytest -q tests/contract/test_workflows_nodes_post_agent.py & pytest -q tests/integration/test_dag_fan_in_out.py & pytest -q tests/integration/test_agent_node.py
- Group B [P]: T010, T018, T020, T021, T022, T023, T024, T025
  - Commands:
    - mypy or tsc (for client), pytest for units; edit docs concurrently.

## Notes
- Use real DBs for tests as in existing suite; avoid mocks.
- Respect limits: agent ≤10 concurrent ops; ≤30s/tool call; retries 3 with backoff 1s/2s/4s.
- Ensure DAG validation on both save (edge creation) and run (before scheduling).


