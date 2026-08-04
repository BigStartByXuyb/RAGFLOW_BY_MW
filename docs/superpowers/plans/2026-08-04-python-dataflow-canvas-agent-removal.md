# Python DataFlow and Canvas-Agent Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove user-configurable DataFlow and drag-and-drop canvas-agent functionality from Python and the frontend while keeping fixed document ingestion, knowledge-base retrieval, standard chat, and knowledge-base APIs working.

**Architecture:** Retained knowledge-base upload always uses its existing parser configuration and task queue; it no longer stores, looks up, or dispatches a DataFlow identifier. The Python canvas-agent subsystem and the frontend canvas/agent application are deleted as complete feature slices, then the schema migration removes their persisted data. A final repository audit classifies any matching residual occurrence as either deleted, retained fixed-RAG code, or explicitly out-of-scope Go/C++ code.

**Tech Stack:** Python 3.13, Quart, Peewee, React, TypeScript, Vite, Vitest, ruff, pytest.

## Global Constraints

- Remove user-configurable DataFlow pipelines and drag-and-drop canvas agents completely; do not hide routes or retain compatibility adapters.
- Preserve the fixed internal RAG flow: upload, parsing/OCR, chunking, embedding, indexing, retrieval, standard chat, and knowledge-base APIs.
- Do not modify Go or C++.
- Delete feature-only translations and tests; retain and repair translations and tests for RAG, standard chat, and knowledge-base APIs.
- Make the schema migration safe to rerun against an already-clean database.
- Do not stage or alter the pre-existing unrelated working-tree changes.

## File map

- `api/apps/restful_apis/agent_api.py`, `api/apps/restful_apis/bot_api.py`, `api/apps/services/canvas_replica_service.py`: remove the Python HTTP and runtime layer for canvas agents and DataFlow.
- `agent/`, `rag/flow/`: remove Python canvas/DataFlow execution and templates after retained RAG callers are detached.
- `api/db/db_models.py`, `api/db/services/canvas_service.py`, `api/db/services/user_canvas_version.py`, `api/db/services/pipeline_operation_log_service.py`: remove feature-owned ORM models/services and add ordered cleanup migration.
- `api/db/services/document_service.py`, `api/db/services/knowledgebase_service.py`, `api/db/services/file_service.py`, `api/db/services/task_service.py`, `api/db/__init__.py`, `api/db/init_data.py`: detach retained ingestion, knowledge-base, and initialization paths from pipeline/canvas state.
- `api/apps/backward_compat.py`, `api/apps/restful_apis/openai_api.py`, `api/apps/restful_apis/chat_api.py`: remove only agent/canvas compatibility exports while retaining normal chat and documented knowledge-base behavior.
- `web/src/pages/agent/`, `web/src/pages/agents/`, `web/src/pages/dataflow-result/`, `web/src/services/agent-service.ts`, `web/src/hooks/use-agent-request.ts`: remove the canvas/DataFlow application and transport clients.
- `web/src/routes.tsx`, `web/src/pages/home/applications.tsx`, `web/src/pages/home/agent-list.tsx`, `web/src/pages/dataset/**`, `web/src/components/{data-pipeline-select,document-pipeline-dialog,chunk-method-dialog,pipeline-operator-tabs}/**`: remove user-facing links, form controls, types, and payload fields for DataFlow.
- `web/src/locales/**`: remove only keys no longer referenced after feature deletion.
- `docs/superpowers/session-tasks/2026-08-04-python-dataflow-canvas-agent-removal-root.md`: append the exact audit commands and their results when implementation finishes.

### Task 1: Establish retained-surface regression checks

**Files:**
- Modify: `test/testcases/test_web_api/test_dataset_management/test_dataset_sdk_routes_unit.py`
- Modify: existing focused chat API unit test under `test/testcases/test_web_api/`
- Test: `test/testcases/test_web_api/test_dataset_management/test_dataset_sdk_routes_unit.py`

**Interfaces:**
- Consumes: retained `/api/v1/datasets` request handlers and existing standard-chat handler modules.
- Produces: tests proving a knowledge base can be created/updated without `pipeline_id`, and that the normal chat module remains importable without agent modules.

- [ ] **Step 1: Add failing retained-contract tests**

```python
def test_create_dataset_does_not_require_pipeline_id(module, monkeypatch):
    monkeypatch.setattr(module, "validate_and_parse_json_request", _payload({"name": "kb", "parser_id": "naive"}))
    result = run_async(module.create_dataset())
    assert result["code"] == 0
    assert "pipeline_id" not in result["data"]

def test_standard_chat_module_imports_without_agent_api(monkeypatch):
    sys.modules.pop("api.apps.restful_apis.agent_api", None)
    module = importlib.import_module("api.apps.restful_apis.chat_api")
    assert callable(module.session_completion)
```

- [ ] **Step 2: Run the focused tests and confirm the first test currently exposes pipeline output/dependency**

Run: `uv run pytest test/testcases/test_web_api/test_dataset_management/test_dataset_sdk_routes_unit.py -q`

Expected: the new dataset assertion fails before the pipeline field is removed.

- [ ] **Step 3: Keep these tests while completing Tasks 2–4; do not delete them with the feature tests**

```python
# The tests intentionally exercise only retained APIs; no agent or DataFlow fixture is imported.
```

- [ ] **Step 4: Re-run the focused tests after Task 4**

Run: `uv run pytest test/testcases/test_web_api/test_dataset_management/test_dataset_sdk_routes_unit.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the retained-contract tests with the backend detachment changes**

Run: `git add test/testcases/test_web_api/test_dataset_management/test_dataset_sdk_routes_unit.py api/db api/apps && git commit -m "refactor: remove Python DataFlow backend"`

### Task 2: Detach fixed ingestion and knowledge-base APIs from DataFlow state

**Files:**
- Modify: `api/db/__init__.py`
- Modify: `api/db/services/document_service.py`
- Modify: `api/db/services/knowledgebase_service.py`
- Modify: `api/db/services/file_service.py`
- Modify: `api/db/services/task_service.py`
- Modify: `api/apps/restful_apis/dataset_api.py`
- Modify: `api/apps/services/dataset_api_service.py`
- Delete: `api/db/services/pipeline_operation_log_service.py`

**Interfaces:**
- Consumes: `DocumentService.insert`, document parse/reparse queueing, and dataset create/update payloads.
- Produces: retained ingestion always dispatches the normal parser/task path and returns dataset/document objects with no `pipeline_id`, `pipeline_name`, or DataFlow progress information.

- [ ] **Step 1: Remove conditional DataFlow dispatch and pipeline joins**

```python
# DocumentService: always queue the fixed parser task.
queue_tasks(tenant_id, [doc_id])

# Knowledgebase and Document select lists: omit pipeline_id and remove UserCanvas joins.
```

- [ ] **Step 2: Remove pipeline fields from request validation and response projection**

```python
for removed_key in ("pipeline_id", "pipeline_name", "pipeline_avatar"):
    payload.pop(removed_key, None)
```

- [ ] **Step 3: Delete the DataFlow task/log API and imports**

```python
# Remove queue_dataflow, CANVAS_DEBUG_DOC_ID, PipelineOperationLogService,
# DataFlow-only task status constants, and their callers. Keep queue_tasks.
```

- [ ] **Step 4: Run retained ingestion/API tests**

Run: `uv run pytest test/testcases/test_web_api/test_dataset_management/test_dataset_sdk_routes_unit.py -q`

Expected: PASS with no import of `canvas_service`, `pipeline_operation_log_service`, or `queue_dataflow`.

- [ ] **Step 5: Run targeted static checks**

Run: `uv run ruff check api/db api/apps/restful_apis/dataset_api.py api/apps/services/dataset_api_service.py`

Expected: PASS.

### Task 3: Remove the Python canvas-agent and DataFlow backend slices

**Files:**
- Delete: `api/apps/restful_apis/agent_api.py`
- Delete: `api/apps/restful_apis/bot_api.py`
- Delete: `api/apps/services/canvas_replica_service.py`
- Delete: `api/db/services/canvas_service.py`
- Delete: `api/db/services/user_canvas_version.py`
- Delete: `agent/`
- Delete: `rag/flow/`
- Modify: `api/apps/__init__.py`
- Modify: `api/apps/backward_compat.py`
- Modify: `api/apps/restful_apis/openai_api.py`
- Modify: `api/ragflow_server.py`
- Modify: `api/db/joint_services/user_account_service.py`

**Interfaces:**
- Consumes: route registration, compatibility route wrappers, server startup imports, and account-deletion cleanup.
- Produces: no Python route or runtime imports `Canvas`, `UserCanvasService`, `CanvasReplicaService`, `agent_api`, `bot_api`, or a DataFlow queue; standard chat registration remains intact.

- [ ] **Step 1: Remove registrations and wrappers that expose agent/canvas routes**

```python
# Delete agent_api/bot_api imports and every wrapper forwarding to
# agent_api.agent_chat_completion or agent_api.download_attachment.
# Retain wrappers importing chat_api, dataset_api, document_api, and openai_api.
```

- [ ] **Step 2: Delete the feature-owned modules and templates**

```powershell
Remove-Item -LiteralPath 'api/apps/restful_apis/agent_api.py','api/apps/restful_apis/bot_api.py','api/apps/services/canvas_replica_service.py','api/db/services/canvas_service.py','api/db/services/user_canvas_version.py','api/db/services/pipeline_operation_log_service.py' -Force
Remove-Item -LiteralPath 'agent','rag/flow' -Recurse -Force
```

- [ ] **Step 3: Remove account cleanup and startup code that only exists for the deleted models**

```python
# Remove delete_user_agents() and the corresponding account-deletion status text.
# Remove template initialization and plugin/runtime imports reachable only from agent/.
```

- [ ] **Step 4: Prove retained route modules import**

Run: `uv run python -c "import api.apps.restful_apis.chat_api; import api.apps.restful_apis.dataset_api; import api.apps.restful_apis.document_api"`

Expected: exit code 0.

- [ ] **Step 5: Commit the removal slice separately**

Run: `git add api agent rag && git commit -m "refactor: remove Python canvas agents"`

### Task 4: Remove schema, feature records, and obsolete model fields

**Files:**
- Modify: `api/db/db_models.py`
- Test: `test/testcases/test_web_api/test_dataset_management/test_dataset_sdk_routes_unit.py`

**Interfaces:**
- Consumes: Peewee `migrate_db()` and the DB-specific `DatabaseMigrator`.
- Produces: a rerunnable migration that removes `knowledgebase.pipeline_id` and `document.pipeline_id`, then deletes/drops `pipeline_operation_log`, `user_canvas_version`, `canvas_template`, and `user_canvas`; ORM classes for these tables no longer exist.

- [ ] **Step 1: Add idempotent migration helpers before removing model declarations**

```python
def drop_column_if_exists(migrator, table_name, column_name):
    if DB.table_exists(table_name) and column_name in DB.get_columns(table_name):
        migrate(migrator.drop_column(table_name, column_name))

def drop_table_if_exists(table_name):
    if DB.table_exists(table_name):
        DB.execute_sql(f"DROP TABLE {table_name}")
```

- [ ] **Step 2: Apply dependency-order cleanup in `migrate_db()`**

```python
drop_column_if_exists(migrator, "document", "pipeline_id")
drop_column_if_exists(migrator, "knowledgebase", "pipeline_id")
for table_name in ("pipeline_operation_log", "user_canvas_version", "canvas_template", "user_canvas"):
    drop_table_if_exists(table_name)
```

- [ ] **Step 3: Remove `UserCanvas`, `CanvasTemplate`, `UserCanvasVersion`, and `PipelineOperationLog` declarations and their table creation registration**

```python
# Delete the four DataBaseModel classes and remove them from init_database/create_tables lists.
```

- [ ] **Step 4: Run migration twice against the project test database**

Run: `uv run python -c "from api.db.db_models import migrate_db; migrate_db(); migrate_db()"`

Expected: both invocations finish without a missing-table or missing-column exception.

- [ ] **Step 5: Re-run retained dataset test**

Run: `uv run pytest test/testcases/test_web_api/test_dataset_management/test_dataset_sdk_routes_unit.py -q`

Expected: PASS.

### Task 5: Remove frontend canvas/DataFlow UI and detach retained knowledge-base forms

**Files:**
- Delete: `web/src/pages/agent/`
- Delete: `web/src/pages/agents/`
- Delete: `web/src/pages/dataflow-result/`
- Delete: `web/src/services/agent-service.ts`
- Delete: `web/src/hooks/use-agent-request.ts`
- Delete: `web/src/components/data-pipeline-select/`
- Delete: `web/src/components/document-pipeline-dialog/`
- Delete: `web/src/components/pipeline-operator-tabs/`
- Modify: `web/src/routes.tsx`
- Modify: `web/src/utils/api.ts`
- Modify: `web/src/pages/home/applications.tsx`
- Modify: `web/src/pages/dataset/dataset-overview/overview-table.tsx`
- Modify: `web/src/pages/dataset/dataset-overview/interface.ts`
- Modify: `web/src/pages/dataset/setting/**`
- Modify: `web/src/pages/dataset/dataset-setting/**`
- Modify: `web/src/components/chunk-method-dialog/index.tsx`
- Modify: `web/src/components/document-preview/hooks.ts`
- Modify: every retained component importing `@/pages/agent/*`, `@/hooks/use-agent-request`, or `agent-service`.

**Interfaces:**
- Consumes: `Routes`, dataset setting schemas, document parser-change payloads, and retained REST API helpers.
- Produces: no frontend route, navigation item, request payload, or import exposes agents/DataFlow; knowledge-base forms offer built-in parser configuration only.

- [ ] **Step 1: Remove agent/DataFlow routes, navigation, endpoint constants, and service hooks**

```typescript
// Delete Routes.Agent, Routes.AgentTemplates, Routes.Agents, Routes.AgentExplore,
// Routes.AgentList, Routes.AgentLogPage, Routes.AgentShare, and Routes.DataflowResult.
// Delete every api.ts URL whose path contains /agents or /dataflow.
```

- [ ] **Step 2: Simplify knowledge-base form schemas to built-in parsing**

```typescript
const formSchema = z.object({
  parser_id: z.string(),
  parser_config: z.record(z.unknown()),
});
// Remove ParseType.Pipeline, pipeline_id, DataFlowSelect, and pipeline navigation.
```

- [ ] **Step 3: Remove pipeline-result links and agent-only document download/preview branches**

```typescript
// Dataset rows render fixed parsing progress only.
// Document preview resolves retained document URLs without the agent branch.
```

- [ ] **Step 4: Delete the feature directories and run the frontend type checker**

Run: `Remove-Item -LiteralPath 'web/src/pages/agent','web/src/pages/agents','web/src/pages/dataflow-result','web/src/services/agent-service.ts','web/src/hooks/use-agent-request.ts','web/src/components/data-pipeline-select','web/src/components/document-pipeline-dialog','web/src/components/pipeline-operator-tabs' -Recurse -Force; Set-Location web; npm run type-check`

Expected: type checking reports no unresolved agent/DataFlow imports.

- [ ] **Step 5: Commit the frontend removal**

Run: `git add web && git commit -m "refactor: remove canvas and DataFlow UI"`

### Task 6: Preserve retained translations and remove feature-only localization/tests

**Files:**
- Modify: `web/src/locales/**`
- Modify: retained test files importing deleted types or routes
- Delete: tests under deleted agent/DataFlow feature directories
- Test: retained dataset/chat frontend tests and API tests

**Interfaces:**
- Consumes: all `t(...)` calls reachable from retained routes and the retained test suite.
- Produces: every retained translation lookup resolves; no test imports a removed feature symbol.

- [ ] **Step 1: Enumerate keys used by retained source before deleting locale entries**

Run: `rg -No "t\\(['\"][^'\"]+" web/src --glob '!pages/agent/**' --glob '!pages/agents/**' --glob '!pages/dataflow-result/**' | Sort-Object -Unique`

Expected: a list of retained translation keys used to decide locale deletions.

- [ ] **Step 2: Remove only agent/DataFlow keys no longer found in the retained-key list**

```json
// Remove unreachable agent, flow, dataflowParser, and pipeline-run labels only.
// Keep shared header, dataset, chat, parser, upload, and error labels.
```

- [ ] **Step 3: Delete feature-only tests and repair retained tests' imports/payloads**

```typescript
expect(savedDataset).not.toHaveProperty('pipeline_id');
expect(screen.queryByText(/dataflow|agent/i)).not.toBeInTheDocument();
```

- [ ] **Step 4: Run retained frontend tests**

Run: `Set-Location web; npm run test -- --run src/pages/dataset`

Expected: PASS.

- [ ] **Step 5: Run frontend lint and type checks**

Run: `Set-Location web; npm run lint; npm run type-check`

Expected: PASS.

### Task 7: Whole-code review, residual audit, and completion record

**Files:**
- Modify: `docs/superpowers/session-tasks/2026-08-04-python-dataflow-canvas-agent-removal-root.md`
- Test: repository-wide search plus retained Python imports and focused test commands

**Interfaces:**
- Consumes: final source tree and all preceding validation results.
- Produces: a recorded audit demonstrating no in-scope residual dependency remains and no retained RAG/chat/knowledge-base call path reaches deleted Python/frontend code.

- [ ] **Step 1: Search for deleted Python/frontend identifiers and classify every result**

Run: `rg -n -i "canvas_replica_service|UserCanvas(Service|Version|Template)|PipelineOperationLog|queue_dataflow|/agents|/dataflow|agent_api|bot_api|pipeline_id|DataFlowSelect" --glob '!go/**' --glob '!cpp/**' --glob '!docs/superpowers/**'`

Expected: no production Python/frontend result; any remaining result must be a deliberately retained generic word with no dependency on the removed feature.

- [ ] **Step 2: Search directory-level imports and public route registration**

Run: `rg -n "from agent|import agent|@/pages/agent|@/pages/agents|use-agent-request|agent-service|data-pipeline-select" api rag web/src --glob '!go/**'`

Expected: no result.

- [ ] **Step 3: Review retained call paths with CodeGraph**

Run: `codegraph explore "Trace dataset create/update/upload, document parse queueing, standard chat completion, and knowledge-base API routes. Confirm none reaches deleted agent, canvas, or DataFlow modules."`

Expected: the returned call paths contain only retained dataset/document/chat/retrieval modules.

- [ ] **Step 4: Run the final focused verification suite**

Run: `uv run pytest test/testcases/test_web_api/test_dataset_management/test_dataset_sdk_routes_unit.py -q; uv run ruff check api rag; Set-Location web; npm run type-check; npm run lint`

Expected: every command exits with code 0.

- [ ] **Step 5: Record evidence and commit the audit**

```markdown
## Final audit

- Residual search: `<exact command>` — `<exit code and classified results>`
- Retained call-path review: `<CodeGraph summary>`
- Python validation: `<command and result>`
- Frontend validation: `<command and result>`
```

Run: `git add docs/superpowers/session-tasks/2026-08-04-python-dataflow-canvas-agent-removal-root.md && git commit -m "docs: record feature removal audit"`

## Plan self-review

- Scope coverage: Tasks 2–5 remove every approved Python/frontend surface; Task 4 deletes the persisted feature records; Tasks 1 and 6 protect retained APIs, translations, and tests; Task 7 fulfills the required code review and residual audit.
- Placeholder scan: no `TODO`, `TBD`, or deferred implementation steps are present.
- Type consistency: retained dataset/document surfaces use `parser_id` and `parser_config`; removed surfaces use the consistently named `pipeline_id`, `UserCanvas*`, and `DataFlow*` identifiers.
