# Session Task: Python DataFlow and Canvas-Agent Removal

**Owner:** current `/root` session only. Other sessions do not need to read or execute this task record.

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
