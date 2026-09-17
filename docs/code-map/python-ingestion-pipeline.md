# 文件入库流水线导航

> 用途:分析“上传文件 -> 解析入库 -> 切块 -> embedding -> 写索引 -> 更新状态”的第一入口。
> 默认链路指标准文件入库。Dataflow、RAPTOR、GraphRAG、reembedding 等会在 `TaskHandler.handle()` 中分流。

## 一句话主线

前端上传文件,API 保存原始文件和 Document/File 记录;前端再触发解析,API 创建 Task 并推入 Redis;后台 worker 消费 Task,取原文件,按 parser 切块,生成 embedding,写入 `settings.docStoreConn`,最后更新 Task/Document 状态。

## 完整跳转链

### 1. 前端页面触发上传

文件:`web/src/pages/dataset/dataset/use-upload-document.ts`

- `useHandleUploadDocument()` — 上传弹窗逻辑入口。
- `onDocumentUploadOk()` — 用户确认上传后执行。
- `uploadDocument(fileList, parserConfig)` — 上传文件。
- `runDocumentByIds({ documentIds, run: 1 })` — 当 `parseOnCreation=true` 时,上传后立即触发解析。

### 2. 前端上传 hook

文件:`web/src/hooks/use-document-request.ts`

- `useUploadDocument()` — 封装上传 mutation。
- `mutationFn()` — 构造 `FormData`,把每个 file append 到 `file` 字段。
- `uploadDocument(id, formData)` — 调前端 service。

### 3. 前端解析 hook

文件:`web/src/hooks/use-document-request.ts`

- `useRunDocument()` — 封装解析/停止/重跑 mutation。
- `runDocumentByIds()` — 对外入口。
- `kbService.documentIngest({ doc_ids, run, ...option })` — 调后端 `/documents/ingest`。

### 4. 前端 service 和 URL

文件:`web/src/services/knowledge-service.ts`

- `uploadDocument(datasetId, formData)` — POST 上传文件。
- `methods.documentIngest` — POST 触发解析。

文件:`web/src/utils/api.ts`

- `documentUpload(datasetId)` — `/api/v1/datasets/{datasetId}/documents`。
- `documentIngest` — `/api/v1/documents/ingest`。

### 5. 后端接收上传

文件:`api/apps/restful_apis/document_api.py`

- `upload_document(dataset_id, tenant_id)` — HTTP 上传入口。
- `_upload_local_documents(kb, tenant_id)` — 本地文件上传路径。
- `FileService.upload_document(...)` — 保存文件并建 Document/File 记录。

补充入口:

- `_upload_web_document()` — URL 网页转 PDF 上传。
- `_upload_empty_document()` — 创建空文档。

### 6. 保存原始文件和文档记录

文件:`api/db/services/file_service.py`

- `FileService.upload_document()` — 上传落库主函数。
- `settings.STORAGE_IMPL.put(kb.id, location, blob)` — 写原始文件到对象存储。
- `DocumentService.insert(doc)` — 创建 `Document` 记录。
- `FileService.add_file_from_kb(doc, kb_folder["id"], kb.tenant_id)` — 创建 `File` 和 `File2Document` 关联。
- `FileService.get_parser(doc_type, filename, default)` — 按文件类型修正 parser,例如图片/音频/PPT/邮件。

文件:`api/db/services/file2document_service.py`

- `File2DocumentService.get_storage_address(doc_id=...)` — 后续通过 Document 找回 `(bucket, name)`。

### 7. 后端接收解析请求

文件:`api/apps/restful_apis/document_api.py`

- `ingest(tenant_id)` — `/documents/ingest` 入口。
- `_run_sync(user_id, req)` — 校验权限、处理 cancel/rerun/delete/apply_kb。
- `DocumentService.run(doc_tenant_id, doc_dict, kb_table_num_map)` — 触发后台任务。

另一个入口:

- `parse_documents(tenant_id, dataset_id)` — `/datasets/{dataset_id}/documents/parse`,内部同样调 `DocumentService.run()`。

### 8. DocumentService 分派任务

文件:`api/db/services/document_service.py`

- `DocumentService.run(tenant_id, doc, kb_table_num_map)` — 入库任务分派入口。
- `queue_dataflow(...)` — 如果 `doc["pipeline_id"]` 存在,走 Dataflow 分支。
- `File2DocumentService.get_storage_address(doc_id=doc["id"])` — 标准分支取 storage 地址。
- `queue_tasks(doc, bucket, name, 0)` — 标准文件入库分支。

### 9. 创建 Task 并推 Redis

文件:`api/db/services/task_service.py`

- `queue_tasks(doc, bucket, name, priority)` — 创建入库任务。
- `new_task()` — 生成单个 Task 基础字段。
- PDF 分支 — 按页范围拆多个 Task。
- table 分支 — 按行范围拆多个 Task。
- 默认分支 — 普通文件通常一个 Task。
- `bulk_insert_into_db(Task, parse_task_array, True)` — 写 Task 表。
- `DocumentService.begin2parse(doc["id"])` — Document 标记为解析中。
- `REDIS_CONN.queue_product(settings.get_svr_queue_name(priority, suffix), message=unfinished_task)` — 推入 Redis 队列。

### 10. Worker 消费 Redis

文件:`rag/svr/task_executor.py`

- `main()` — task executor 进程入口。
- `task_manager()` — 单次任务执行包装。
- `handle_task()` — 消费并执行一个 task。
- `collect()` — 从 Redis 取消息。
- `REDIS_CONN.queue_consumer(...)` — 消费 Redis 队列。
- `TaskService.get_task(msg["id"])` — 从 DB 补齐 task、document、knowledgebase、tenant 信息。

### 11. 默认进入重构版执行器

文件:`rag/svr/task_executor.py`

- `handle_task()` — 根据 `TE_RUN_MODE` 选择执行器。
- `TaskManager.run_refactored_task(...)` — 默认 `TE_RUN_MODE=0` 时执行。
- `do_handle_task(task)` — 旧版执行器,仅 `TE_RUN_MODE` 非 0/1 时走;用于理解历史链路,改代码优先看重构版。

### 12. TaskManager 创建上下文

文件:`rag/svr/task_executor_refactor/task_manager.py`

- `TaskManager.run_refactored_task(...)` — 重构版入口。
- `TaskContext(...)` — 包装 raw task、限流器、progress/cancel 回调。
- `TaskHandler(ctx=task_context)` — 创建任务处理器。
- `handler.handle_task()` — 进入总编排。

文件:`rag/svr/task_executor_refactor/task_context.py`

- `TaskContext` — task 字段访问门面,如 `ctx.id`、`ctx.doc_id`、`ctx.parser_id`、`ctx.parser_config`、`ctx.kb_parser_config`。

### 13. TaskHandler 总编排

文件:`rag/svr/task_executor_refactor/task_handler.py`

- `TaskHandler.handle_task()` — 任务处理入口,负责异常/cancel 清理。
- `TaskHandler.handle()` — 按 `task_type` 分流。
- `_bind_embedding_model()` — 绑定 embedding 模型并取得 vector size。
- `_init_kb(vector_size)` — 调 `settings.docStoreConn.create_idx(...)` 初始化索引。
- `_run_standard_chunking(...)` — 标准文件入库入口。
- `_run_standard_chunking_impl(...)` — 标准文件入库完整实现。

标准分支之外:

- `_run_dataflow()` — Dataflow pipeline。
- `_run_raptor()` — RAPTOR。
- `_run_graphrag()` — GraphRAG。

### 14. Worker 取原始文件

文件:`rag/svr/task_executor_refactor/task_handler.py`

- `_run_standard_chunking_impl(...)`
- `File2DocumentService.get_storage_address(doc_id=ctx.doc_id)` — 查 `(bucket, name)`。
- `_get_storage_binary(bucket, name)` — 取原文件 bytes。
- `settings.STORAGE_IMPL.get(bucket, name)` — 实际对象存储读取。

### 15. 构建 chunks

文件:`rag/svr/task_executor_refactor/chunk_service.py`

- `ChunkService.build_chunks(storage_binary)` — 构建 chunks 主入口。
- `get_parser(ctx.parser_id)` — 选择 parser 模块。
- `run_chunking(chunker, storage_binary, ctx)` — 调具体 parser。
- `extract_outline(cks, ctx)` — PDF outline 元数据提取。
- `_prepare_docs_and_upload(cks)` — 生成 chunk id、补公共字段、上传 chunk 图片。
- `extract_keywords(docs, ctx)` — 可选自动关键词。
- `generate_questions(docs, ctx)` — 可选自动问题。
- `generate_metadata(docs, ctx)` / `apply_built_in_metadata(ctx)` — 可选 metadata。
- `apply_tags(docs, ctx)` — 可选 tag。

### 16. Parser 选择和调用

文件:`rag/svr/task_executor_refactor/chunk_builder.py`

- `get_parser(parser_id)` — parser factory。
- `run_chunking(chunker, binary, ctx)` — 调用 `chunker.chunk(...)`。
- `merge_table_parser_config_from_kb(ctx.raw_task)` — table parser 合并 KB 级配置。
- `extract_outline(cks, ctx)` — 持久化 PDF outline。

具体 parser 文件:

- `rag/app/naive.py::chunk()` — `naive` / `general` / `knowledge_graph` 常用默认解析。
- `rag/app/table.py::chunk()` — 表格。
- `rag/app/qa.py::chunk()` — 问答对。
- `rag/app/paper.py::chunk()` — 论文。
- `rag/app/book.py::chunk()` — 书籍。
- `rag/app/presentation.py::chunk()` — PPT。
- `rag/app/picture.py::chunk()` — 图片。
- `rag/app/audio.py::chunk()` — 音频。
- `rag/app/email.py::chunk()` — 邮件。
- `rag/app/resume.py::chunk()` — 简历。
- `rag/app/one.py::chunk()` — 整文档单块。
- `rag/app/tag.py::chunk()` — 标签集。

### 17. Embedding

文件:`rag/svr/task_executor_refactor/embedding_service.py`

- `EmbeddingService.embed_chunks(docs, embedding_model, parser_config)` — embedding 主入口。
- `EmbeddingUtils.prepare_texts_for_embedding(docs)` — 准备标题和正文。
- `embedding_model.encode(...)` — 调具体 embedding 模型。
- `EmbeddingUtils.combine_title_content_vectors(...)` — 文件名/标题向量与正文向量加权合并。
- `EmbeddingUtils.attach_vectors(docs, vects)` — 写入 `q_{vector_size}_vec` 字段。

文件:`rag/llm/embedding_model.py`

- 各厂商 embedding 实现的 `encode(...)`。

### 18. 写入检索引擎

文件:`rag/svr/task_executor_refactor/chunk_service.py`

- `ChunkService.insert_chunks(task_id, task_tenant_id, task_dataset_id, chunks)` — 写索引入口。
- `_create_mother_chunks(chunks)` — 从 `mom` / `mom_with_weight` 生成 mother chunks。
- `_insert_mother_chunks(...)` — 写 mother chunks。
- `_insert_main_chunks(...)` — 写主 chunks。
- `_intercept_doc_store_insert(chunks, index_name, task_dataset_id)` — 生产模式下调 `settings.docStoreConn.insert(...)`。
- `_update_task_chunk_ids(task_id, chunk_ids)` — 写回 Task 的 chunk ids。
- `_rollback_insertion(...)` — Task 丢失或异常时回滚已写 chunks/images。

文件:`common/settings.py`

- `docStoreConn` — 全局文档索引连接,后端可能是 Elasticsearch、OpenSearch 或 Infinity。

### 19. 后置处理

文件:`rag/svr/task_executor_refactor/post_processor.py`

- `PostProcessor.process_table_parser_metadata(task_doc_id, chunks)` — table parser 聚合文档级 metadata。
- `PostProcessor.insert_toc_chunk(toc_chunk, chunk_service)` — 插入 TOC chunk。

文件:`rag/svr/task_executor_refactor/task_handler.py`

- `_build_toc(ctx, docs, progress_cb)` — 可选生成目录 chunk。
- `_process_toc_thread(toc_thread)` — 等待 TOC 生成。
- `_run_document_post_chunking_if_last(...)` — 最后一个分片任务完成后执行文档级后处理。

文件:`rag/svr/task_executor_refactor/chunk_post_processor.py`

- `run_document_post_chunking_if_last(...)` — 文档级后处理入口。
- `run_document_structure_compile(...)` — 可选结构编译。
- `run_tree_templates(...)` / `rechunk_doc_by_tree(...)` — 可选 tree/rechunk 相关处理。

### 20. 更新状态

文件:`api/db/services/task_service.py`

- `TaskService.update_chunk_ids(id, chunk_ids)` — 保存 task 对应 chunk id 列表。
- `TaskService.update_progress(id, info)` — 更新 task 进度;失败时也会把 Document 置为 FAIL。
- `TaskService.do_cancel(id)` — 判断是否取消。

文件:`api/db/services/document_service.py`

- `DocumentService.begin2parse(doc_id, keep_progress=False)` — 标记 Document 进入解析中。
- `DocumentService.increment_chunk_num(doc_id, kb_id, token_num, chunk_num, duration)` — 累加 Document 和 Knowledgebase 的 token/chunk 统计。
- `DocumentService.update_progress()` / `update_progress_immediately()` — 刷新 Document 维度进度。

## 推荐断点顺序

1. `web/src/pages/dataset/dataset/use-upload-document.ts::onDocumentUploadOk`
2. `api/apps/restful_apis/document_api.py::upload_document`
3. `api/db/services/file_service.py::upload_document`
4. `api/apps/restful_apis/document_api.py::ingest`
5. `api/db/services/document_service.py::run`
6. `api/db/services/task_service.py::queue_tasks`
7. `rag/svr/task_executor.py::collect`
8. `rag/svr/task_executor_refactor/task_handler.py::_run_standard_chunking_impl`
9. `rag/svr/task_executor_refactor/chunk_service.py::build_chunks`
10. `rag/svr/task_executor_refactor/chunk_builder.py::run_chunking`
11. `rag/app/<parser>.py::chunk`
12. `rag/svr/task_executor_refactor/embedding_service.py::embed_chunks`
13. `rag/svr/task_executor_refactor/chunk_service.py::insert_chunks`
14. `api/db/services/document_service.py::increment_chunk_num`

## 改代码入口速查

- 上传接口/参数:`api/apps/restful_apis/document_api.py`
- 文件落存储/Document 创建:`api/db/services/file_service.py`
- Task 拆分/排队:`api/db/services/task_service.py`
- Worker 编排:`rag/svr/task_executor_refactor/task_handler.py`
- 切块前后处理:`rag/svr/task_executor_refactor/chunk_service.py`
- parser 分派:`rag/svr/task_executor_refactor/chunk_builder.py`
- 具体切块策略:`rag/app/*.py`
- embedding:`rag/svr/task_executor_refactor/embedding_service.py` 和 `rag/llm/embedding_model.py`
- 写索引:`rag/svr/task_executor_refactor/chunk_service.py` 和 `common/settings.py`
- table metadata / TOC / 文档级后处理:`rag/svr/task_executor_refactor/post_processor.py`、`chunk_post_processor.py`
