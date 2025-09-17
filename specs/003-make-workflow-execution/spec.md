# Feature Specification: Asynchronous Execution, LLM, Formatter, and PDF Text Extraction

**Feature Branch**: `003-make-workflow-execution`  
**Created**: 2025-09-17  
**Status**: Draft  
**Input**: User description: "Make workflow execution asynchronous. Implement NodeType.GENERATIVE_AI with user-configurable model and prompt (and optional parameters). Implement NodeType.FORMATTER with user-configurable formatting rules (e.g., lowercase, uppercase, half-width ↔ full-width). Allow PDF file uploads and implement NodeType.EXTRACT_TEXT to extract text from uploaded PDFs."

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies  
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## User Scenarios & Testing (mandatory)

### Primary User Story
As a user, I can build a workflow that processes text from various sources, run it asynchronously without blocking the interface, and configure nodes to generate text with an LLM, format text with chosen rules, and extract text from uploaded PDF files, so that I can reliably automate content processing end-to-end.

### Acceptance Scenarios
1. Given a workflow with one or more nodes, when I trigger a run, then I receive a run identifier immediately and the workflow executes asynchronously until completion.
2. Given a run identifier, when I query the run, then I can see the current status (e.g., queued, running, succeeded, failed) and, when finished, the final output.
3. Given a workflow containing a GENERATIVE_AI node, when I provide a prompt and select a model (and optional parameters such as temperature or maximum output length), then the node uses these inputs to produce text that is included in the workflow output.
4. Given a workflow containing a FORMATTER node, when I configure one or more formatting rules (e.g., lowercase, uppercase, half-width to full-width, full-width to half-width), then the input text is transformed accordingly in a deterministic and ordered manner.
5. Given the application allows file uploads, when I upload a valid PDF and add an EXTRACT_TEXT node referencing that file, then the node outputs the extracted text for downstream nodes in the workflow.
6. Given a workflow combining EXTRACT_TEXT → GENERATIVE_AI → FORMATTER, when I run the workflow asynchronously, then the result reflects extracted PDF text, generated content based on the prompt/model, and the applied formatting rules, observable in the run output.

### Edge Cases
- Invalid or unsupported node type in a workflow should be rejected with a clear error.
- LLM configuration errors (e.g., missing prompt or invalid model name) should clearly explain what to fix without exposing sensitive details.
- LLM service unavailability or timeouts should cause the run (or step) to fail gracefully with status and error message visible in run details.
- Uploading a non-PDF file or a corrupted/encrypted password-protected PDF should be rejected with a clear message; the workflow should not proceed with EXTRACT_TEXT for that file.
- Oversized PDF files or excessively long text should be limited per documented constraints; users should receive a clear error or truncation notice.
- FORMATTER with no rules configured should behave as a no-op and not fail the run.
- Multiple FORMATTER rules should execute in the configured order; conflicting rules should have deterministic outcomes.
- Cancelling or re-running while a previous run is still in progress should be handled predictably (e.g., allowed as a new run with its own identifier) without corrupting results.

## Requirements (mandatory)

### Functional Requirements
- **FR-001**: The system MUST allow users to trigger a workflow run and return immediately with a run identifier without waiting for execution to finish.
- **FR-002**: The system MUST allow users to retrieve run status and final output by run identifier.
- **FR-003**: The system MUST support node type GENERATIVE_AI, where users can configure at least: model selection and prompt text; optional parameters MAY include, but are not limited to, creativity/temperature and maximum output length.
- **FR-004**: The system MUST support node type FORMATTER, where users can configure one or more rules from a set including lowercase, uppercase, half-width → full-width conversion, and full-width → half-width conversion. Rule execution order MUST be preserved.
- **FR-005**: The system MUST allow users to upload PDF files for use within workflows, subject to documented size and type constraints.
- **FR-006**: The system MUST support node type EXTRACT_TEXT that reads an uploaded PDF and outputs extracted text for downstream nodes.
- **FR-007**: The system MUST provide clear validation errors for misconfigurations (e.g., missing prompt, unsupported formatting rule, invalid file type) without exposing implementation details.
- **FR-008**: The system MUST make asynchronous execution and its states understandable to users (e.g., distinguish queued, running, succeeded, failed) via observable status.
- **FR-009**: The system SHOULD allow users to view per-node step results and errors associated with a run for transparency and troubleshooting.
- **FR-010**: The system SHOULD handle large inputs (long PDF text, long prompts) within reasonable, documented limits and communicate any truncation or limits applied.

*Clarifications:*
- **FR-011**: Concurrent runs per workflow are allowed up to 2 simultaneously; additional triggers are queued FIFO per workflow with a per-workflow pending-queue cap of 20. When the queue is full, the system rejects new run requests with a clear message to try again later.
- **FR-012**: Each EXTRACT_TEXT node accepts exactly one PDF file reference. Maximum PDF size is 10 MB. Only MIME type `application/pdf` is accepted. Multiple EXTRACT_TEXT nodes may exist in a single workflow, each bound to its own uploaded file.
- **FR-013**: PDF text extraction targets text-based PDFs (no OCR). Supported languages include English and Japanese; other languages are best-effort. Vertical writing and complex scripts may degrade quality. Encrypted or password-protected PDFs are rejected.
- **FR-014**: At least one default general-purpose LLM option is available without extra configuration. Usage is subject to fair-use limits: up to 100 runs per day and 30 runs per hour per environment. Prompts are limited to 4,000 characters, and outputs to approximately 1,000 tokens.
- **FR-015**: Intermediate per-node inputs/outputs and timings are visible in the run details view for transparency and troubleshooting; the main runs list shows only high-level status and summary.

### Key Entities (include if feature involves data)
- **Workflow**: A user-defined sequence of nodes that process and transform text; users initiate runs against a workflow.
- **Node**: A step within a workflow; supported types include GENERATIVE_AI (produces text using a model and prompt), FORMATTER (transforms text by rules), and EXTRACT_TEXT (extracts text from an uploaded PDF). Each node has user-configurable parameters relevant to its type.
- **Run**: An instance of workflow execution that proceeds asynchronously; has an identifier, a status lifecycle (e.g., queued → running → succeeded/failed), timestamps, and a final output visible to users.
- **UploadedFile**: A file provided by the user for workflow input; for this feature, PDF is supported for text extraction, governed by documented size/type constraints.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous  
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [ ] User description parsed
- [ ] Key concepts extracted
- [ ] Ambiguities marked
- [ ] User scenarios defined
- [ ] Requirements generated
- [ ] Entities identified
- [ ] Review checklist passed

---


