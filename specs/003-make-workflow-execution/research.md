# Research & Decisions

- **Decision**: Asynchronous execution with job states Pending/Running/Succeeded/Failed
  - Rationale: Non-blocking UX; aligns with constitution
  - Alternatives: Synchronous run — rejected for UX and scalability

- **Decision**: Concurrency limit = 2 concurrent runs per workflow; FIFO queue cap = 20
  - Rationale: Prevent resource contention in minimal environment
  - Alternatives: Unlimited, global queue — rejected for predictability

- **Decision**: PDF uploads only; max size 10MB; MIME `application/pdf`; no OCR
  - Rationale: Keep scope minimal; leverage text-based extraction
  - Alternatives: OCR (e.g., Tesseract) — out of scope for milestone

- **Decision**: LLM defaults available; prompt limit 4,000 chars; output ~1,000 tokens; fair-use 100/day, 30/hour
  - Rationale: Cost/control; ensures demo stability
  - Alternatives: Unlimited — rejected for abuse risk

- **Decision**: Intermediate step I/O visible in run details; list view shows status summary
  - Rationale: Transparency for debugging
  - Alternatives: Hide internals — rejected for usability

- **Decision**: Storage = SQLite single-file; JSON config per node
  - Rationale: Zero-ops; flexible configs
  - Alternatives: Postgres — heavier than required for this milestone
