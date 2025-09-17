---
title: Research – Optional DAG Workflows & AI Agent Node
branch: 004-description-optional-support
date: 2025-09-17
spec: ./spec.md
---

## Decisions

- DAG validation and scheduling
  - Decision: Enforce acyclicity at design-time and run-time; schedule via topological order with readiness when all required inputs available.
  - Rationale: Guarantees correctness; aligns with acceptance criteria and typical workflow engines.
  - Alternatives considered: Dynamic cycle detection at runtime only (rejected: poor UX and late failures), naive DFS without explicit port validation (rejected: ambiguous data dependencies).

- Fan-out and fan-in semantics
  - Decision: Default AND-join semantics for merges; explicit port wiring defines data availability. Support one-to-many edges for fan-out.
  - Rationale: Matches primary user story; predictable execution.
  - Alternatives: OR-join or threshold-based joins (out of scope; future extension).

- AI Agent node scope and policy
  - Decision: Agent accepts objective, optional success criteria, and allowed tools; executes a bounded loop of plan→act→observe until success/failure/budget-exhausted.
  - Rationale: Ensures bounded, auditable behavior per FR-009..FR-011.
  - Limits: tool whitelist, ≤10 concurrent ops, ≤30s per tool call, token/cost budgets, retries (1s/2s/4s) up to 3 for transient errors.
  - Alternatives: Unbounded agent loops, autonomous tool discovery (rejected due to safety and determinism).

- Persistence model per Constitution
  - Decision: Persist workflows, nodes, edges, runs, node runs, jobs, files. Prefer SQLite single-file for minimal setup; allow swap to Postgres in dev.
  - Rationale: Constitution I (Persistence-First, minimal SQLite) while acknowledging current repo uses SQLAlchemy and Postgres in dev.
  - Alternatives: In-memory only (rejected: violates Constitution), external queues/brokers (out of scope for minimal async).

- Async execution model
  - Decision: Background task per run returning `job_id`; clients poll `GET /jobs/{job_id}`.
  - Rationale: Constitution II; meets acceptance criteria for async job tracking.
  - Alternatives: Celery/Redis or distributed brokers (defer; unnecessary for scope).

- Observability and redaction
  - Decision: Structured logs include request_id/job_id, node_type, timings; redact secrets and PII; surface non-determinism for AI nodes.
  - Rationale: Constitution V; aids triage and auditing.

## Resolved Unknowns (from Technical Context)

- Language/Version: Python 3.11 (backend), React 18 + TypeScript (frontend) – confirmed from repo and README.
- Storage: SQLite minimal target (Constitution), Postgres acceptable for dev; abstracted via SQLAlchemy.
- Testing: pytest structure exists; contract/integration/unit present – plan generates contracts aligning with tests later.
- Project Type: Web (frontend + backend) – structure Option 2.
- Performance Goals: Concurrency cap 50 nodes in parallel; job queue limits per README; acceptable for assignment scope.

## Tooling Choices for Agent Tools

- Available tools: PDF text extractor, Formatter, LLM call (OpenAI-compatible).
- Interface: name, input schema, output schema, constraints; audit logs per invocation.

## Risks & Mitigations

- Cycle detection misses edge cases → Use Kahn’s algorithm and validate on both save and run.
- Unbounded agent steps → Enforce max iterations and budgets; explicit termination reasons.
- API drift between plan and implementation → Contracts (OpenAPI) serve as source of truth; tests to be generated in /tasks phase.

## Alternatives Considered

- Graph DB for DAG storage (Neo4j) – rejected for complexity.
- Server-sent events for live run updates – out of scope; polling sufficient.

## Summary

Design adopts topological scheduling with explicit port wiring, AND-join merges, and a bounded AI Agent loop operating under strict policy and budgets. Persistence is required (SQLite minimal), async job model is used, and observability focuses on safety and auditability.


