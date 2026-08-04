# Session Task: Python DataFlow and Canvas-Agent Removal

**Owner:** current `/root` session only. Other sessions do not need to read or execute this task record.

> **Branch-only handoff artifact:** Keep this task record, the matching design, and the implementation plan committed on `codex/python-dataflow-canvas-removal` so another machine can resume the work. Exclude these `docs/superpowers/**` handoff files from the final commit(s) merged to the main branch.

## Objective

Remove the Python and frontend product surfaces for user-configurable DataFlow pipelines and drag-and-drop canvas agents, while retaining the fixed RAG document-processing flow, standard chat, knowledge-base question answering, and knowledge-base APIs.

## In scope

- Frontend DataFlow and canvas-agent pages, routes, menu entries, API clients, types, feature-specific translations, and feature-only tests.
- Python DataFlow and canvas-agent APIs, services, ORM models, schema/migrations, templates, task/log code, and residual references.
- Existing DataFlow/canvas-agent database records and tables, removed through an explicit, ordered migration.
- A whole-repository residual-reference audit and retained-Python call-path review after deletion.

## Out of scope

- Go and C++ code.
- Fixed RAG document processing: upload, parsing/OCR, chunking, embedding, indexing, and retrieval.
- Standard chat, knowledge-base question answering, and knowledge-base API endpoints.

## Completion criteria

1. No user-visible DataFlow or drag-and-drop canvas-agent entry remains.
2. No Python or frontend production reference remains to their removed APIs, models, templates, routes, tables, or task/log handlers.
3. The ordered database migration removes feature-owned data only after all remaining dependent fields and foreign keys have been removed.
4. Retained RAG/chat/knowledge-base translations and tests remain valid; feature-only translations and tests are removed.
5. The final task record lists residual-reference searches, code-review findings, and validation commands/results.

## Handoff status — 2026-08-04

### Completed and committed

- `08cbb89`, `5cabc54`: regression tests for retained knowledge-base and standard-chat surfaces.
- `f04a3b8`, `a982cb0`, `0366a04`: DataFlow fields, joins, queue dispatch, and request-validation surfaces removed from retained Python knowledge-base/document paths.
- `403c4ec`, `c010217`: Python canvas-agent/DataFlow runtime, APIs, admin routes, templates, worker paths, and reviewed residual references removed. `PipelineOperationLogService` remains because the fixed document-processing worker still uses it for operation history; it no longer depends on canvas data.

### Verified so far

- Task 1 and Task 2 received independent review approval after fixes.
- Task 3's first review found startup and residual-reference failures; the follow-up cleanup is committed as `c010217` and requires a final independent review before the task is marked complete.
- AST parsing, targeted Ruff checks, removed-reference scans, and `git diff --check` were run by implementation tasks.
- Full pytest could not run in this Windows isolated worktree: `uv run pytest` attempts to build `editdistance==0.8.1` with CPython 3.13/MSVC and fails; later checks also found the local virtual environment lacks `pytest` and `quart`.

### Remaining work

1. Independently review commit `c010217` and resolve any findings.
2. Remove feature-owned database models/tables and `knowledgebase.pipeline_id` / `document.pipeline_id` via an ordered, rerunnable migration; preserve fixed document-processing tables and history.
3. Remove frontend DataFlow and canvas-agent pages, routes, navigation, API client/hooks, feature-only translations and tests; retain knowledge-base, standard chat, and their translations/tests.
4. Run repository-wide residual-reference and retained-call-path audit, update this record with exact commands/results, then run available Python/frontend verification.
