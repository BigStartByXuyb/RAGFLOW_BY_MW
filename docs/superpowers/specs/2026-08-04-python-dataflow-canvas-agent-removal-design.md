# Python DataFlow and Canvas-Agent Removal Design

## Goal

Remove user-configurable DataFlow pipelines and drag-and-drop canvas agents from the Python product and frontend without changing the fixed RAG document-processing flow or the retained chat and knowledge-base APIs.

## Scope and boundaries

The removal covers feature-owned frontend pages, routes, navigation, API clients, types, translations, and tests; and Python APIs, services, models, templates, task/log handlers, database schema/migrations, and references. Existing feature records are deleted by migration.

The fixed process used by a knowledge base after file upload remains: text extraction/OCR, chunking, embedding, indexing, retrieval, normal chat, and public knowledge-base APIs. It is an internal implementation flow, not a user-editable DataFlow pipeline. Go and C++ are outside this task.

## Chosen approach

Perform a full feature removal rather than hiding UI or retaining compatibility wrappers. First detach retained knowledge-base code from DataFlow fields and calls, then remove feature surfaces, and finally remove the now-unreferenced database schema and records through an ordered migration. This keeps one implementation path for document ingestion and avoids dead configuration state.

## Architecture and data flow after removal

Knowledge-base upload invokes the existing fixed document-processing path directly. It must not inspect, create, or persist a pipeline/canvas identifier. Standard chat and knowledge-base APIs continue to use retrieval and dialog services only; no request route may initialize a canvas, schedule a DataFlow run, or load a canvas-agent version.

## Data migration

The migration must remove dependent DataFlow/canvas references from retained tables before dropping feature-owned tables. It must delete existing feature-owned rows in dependency order, then drop the corresponding tables, indexes, and foreign keys. The migration must be idempotent for a database that has already had the feature data removed.

## Error handling

After deployment, removed paths are absent rather than returning compatibility responses. Retained endpoints must reject no valid request solely because a removed pipeline/canvas field no longer exists. Migration failures must stop before an unsafe table drop and surface the failing dependency clearly.

## Testing and review

Keep or repair translations and tests for retained RAG, standard chat, and knowledge-base APIs. Delete only tests that exercise removed features. Run focused frontend static/type/test validation and focused Python import/lint/API tests. Finally search the entire repository for removed Python/frontend symbols, routes, tables, filenames, and imports; review each remaining occurrence to ensure it is either outside scope (Go/C++) or belongs to the retained internal RAG path.
