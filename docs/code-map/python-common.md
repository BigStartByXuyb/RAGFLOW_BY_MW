# `common/` · `sdk/` · `mcp/` · `memory/` — 辅助模块导航

四个 Python 辅助模块合并在一份地图中。所有路径相对仓库根。

---

## 1. `common/` — 公共工具库

顶层扁平化工具模块(~35 个 .py + 两个子包)。运行时配置由 `common/settings.py` 统一装配。

### 运行时配置(最重要)
- `common/settings.py:218` `init_settings()` — **全局装配入口**。按 `DOC_ENGINE` 选 `docStoreConn`(:310 ES / :313 Infinity / :319 OceanBase)、`msgStoreConn`(memory 用,:330-335)、对象存储 `STORAGE_IMPL`(:350,`StorageFactory`:349 依 `STORAGE_IMPL_TYPE` 选 MINIO/S3/OSS/GCS/AZURE)。文件头声明大量全局配置变量(LLM/DB/OAuth/SMTP/存储)。
- `common/config_utils.py:55` `read_config()`、`:136` `decrypt_database_config`。
- `common/constants.py` — 全量枚举(`RetCode:45`、`LLMType:86`、`ParserType:123`、`Storage:224`、`MemoryType:234`、`MCPServerType:216` 等)。

### HTTP / 网络 / 安全
- `common/http_client.py:118/172` `async_request()`/`sync_request()` — httpx 封装,内置超时/重试/退避、URL 参数脱敏(`_redact_sensitive_url_params`:57)。
- `common/ssrf_guard.py:117/190` `assert_url_is_safe()`/`assert_host_is_safe()` — SSRF 防护(仅允许公网可路由 IP);`pin_dns()`(:63)monkey-patch `socket.getaddrinfo` 防 DNS rebinding;`ALLOW_ANY_HOST` 可绕过。
- `common/connection_utils.py:30` `timeout()` 装饰器;`:103/121` `construct_response`/`sync_construct_response`(统一 HTTP 响应体)。

### 加密 / Token
- `common/crypto_utils.py:25` `BaseCrypto`(PBKDF2+PKCS7+`RAGF` 魔数头);`AESCrypto:147`/`AES128CBC:180`/`AES256CBC:194`/`SM4CBC:208`;`CryptoUtil:240` 工厂。
- `common/token_utils.py:126` `num_tokens_from_string()`(tiktoken cl100k_base);`truncate:183`;`record_run_token_usage:68` + `token_usage_sink`(:54 ContextVar,按 agent run 聚合用量)。

### 元数据过滤(检索下推)
- `common/metadata_utils.py:30` `meta_filter()` 内存态过滤;`turn2jsonschema:388`。
- `common/metadata_es_filter.py:180` `MetaFilterTranslator`(条件→ES query);`build_meta_filter_query:315`、`plan_pushdown:329`。
- `common/metadata_infinity_filter.py:73` `MetaFilterTranslator`(Infinity 版);`build_infinity_filter:212`。

### 存储 / 文档引擎抽象 `common/doc_store/`
- `doc_store_base.py:148` `DocStoreConnection(ABC)` — 文档存储引擎统一抽象(`create_idx`/`search`:197/`insert`/`update`/`delete`/`sql`);查询表达式 `MatchTextExpr:58`/`MatchDenseExpr:72`/`MatchSparseExpr:90`/`MatchTensorExpr:106`/`FusionExpr:122`/`OrderByExpr:132`。
- `es_conn_base.py`/`infinity_conn_base.py`/`ob_conn_base.py` — 三引擎基类;`*_conn_pool.py` — 连接池。

### MCP 工具调用(客户端侧)
- `common/mcp_tool_call_conn.py:49` `MCPToolCallSession(ToolCallSession)` — 连 MCP server 调工具(`tool_call:220`、`get_tools:204`);`mcp_tool_metadata_to_openai_tool:323`(MCP tool → OpenAI function)。

### 数据源连接器 `common/data_source/`(规模最大,~60+ 文件)
- `interfaces.py` — 抽象层:`BaseConnector:209`、`LoadConnector:31`、`PollConnector:49`、`CheckpointedConnector:265`、`CredentialsProviderInterface:116`。
- `connector_runner.py:83` `ConnectorRunner` — 执行调度。
- 具体连接器:`github/`、`google_drive/`、`jira/`、`bitbucket/`、`confluence_connector.py`、`slack_connector.py`、`notion_connector.py`、`salesforce_connector.py`、`sharepoint_connector.py`、`gmail_connector.py`、`rdbms_connector.py`、`rest_api_connector.py` 等(SaaS/云盘/邮件/数据库/RSS)。

### 其他
`misc_utils.py:35` `get_uuid()`、`:196` `once()`;`string_utils.py`(`clean_markdown_block:49`);`file_utils.py:31` `get_project_base_directory()`;`query_base.py`(`QueryBase` 基类,被 memory 检索继承);还有 `time_utils`/`float_utils`/`text_utils`/`log_utils`/`exceptions`/`asyncio_utils` 等。

---

## 2. `sdk/python/` — 官方 Python SDK(包名 `ragflow_sdk`)

**纯 REST 客户端**,只封装 `/api/v1` 端点,不含服务端逻辑;beartype 运行时类型校验。

- `sdk/python/ragflow_sdk/__init__.py:23` — 包入口,`__all__`(:34)导出 `RAGFlow, DataSet, Chat, Session, Document, Chunk, Agent, Memory`。
- `sdk/python/ragflow_sdk/ragflow.py:27` — **`RAGFlow` 主客户端**。`api_url = {base_url}/api/{version}` + Bearer 头(:34)。主要 API:
  - Dataset:`create_dataset:56`、`list_datasets:98`
  - Chat:`create_chat:118`、`list_chats:155`
  - 检索:`retrieve:187`(POST `/retrieval`,支持 metadata_condition、cross_languages、use_kg、toc_enhance)
  - Agent:`list_agents:233`、`create_agent:260`、`update_agent:281`
  - Memory:`create_memory:316`、`add_message:350`、`search_message:359`

### 资源模型 `sdk/python/ragflow_sdk/modules/`
- `base.py:18` `Base` — 基类(`_update_from_dict:23` dict→属性、`to_json:30`、代理 HTTP 方法)。
- `dataset.py:22` `DataSet` — `upload_documents:54`、`parse_documents:150`、`get_auto_metadata:165`;内嵌 `ParserConfig:23`。
- `document.py:23` `Document` — `download:65`、`list_chunks:78`、`add_chunk:90`。
- `chunk.py:28` `Chunk`;`chat.py:22` `Chat`(`create_session:46`)。
- `session.py:25` `Session` — `ask:39`(核心问答,`_ask_chat:154`/`_ask_agent:160`,流式 `_structure_answer:140`);`Message:179`。
- `agent.py:21` `Agent`;`memory.py:20` `Memory`(`list_memory_messages:59`、`forget_message:67`)。

---

## 3. `mcp/` — MCP Server / Client

基于官方 `mcp` SDK + Starlette + uvicorn。

### Server(入口)
- `mcp/server/server.py:822` `main()` — click CLI 服务端入口。
  - `RAGFlowConnector:58` — 反向代理到 RAGFlow REST API(`/datasets`/`/chats`/`/retrieval`),带 LRU+TTL 元数据缓存;`retrieval:263`、`list_datasets:234`。
  - 暴露 3 个 MCP 工具(`list_tools:535`):`ragflow_retrieval`、`ragflow_list_datasets`、`ragflow_list_chats`;调度 `call_tool:653`。
  - **两种传输**(`create_starlette_app:705`):SSE(`/sse` + `/messages/`,:736-751)、Streamable HTTP(`/mcp` GET/POST/DELETE,:755-786)。
  - **两种启动模式**(`LaunchMode:38`):`self-host`(单租户,需 `--api-key`)、`host`(多租户,`AuthMiddleware:711` 强制鉴权,`_extract_token_from_headers:468`)。
  - 默认 `127.0.0.1:9382`,后端 `http://127.0.0.1:9380`;env 覆盖 `RAGFLOW_MCP_*`(:834-842)。

### Client(示例)
- `mcp/client/client.py:22` — SSE 客户端示例。
- `mcp/client/streamable_http_client.py:20` — Streamable HTTP 客户端示例。

> **双身份别混淆**:`mcp/` 是对外 MCP Server(把检索暴露为工具);`common/mcp_tool_call_conn.py` 是 MCP Client(让 agent 调外部 MCP 工具)。方向相反。

---

## 4. `memory/` — 对话记忆服务

记忆存储连接 `settings.msgStoreConn` 由 `common/settings.py:326-335` 按 `DOC_ENGINE` 装配。

### Services
- `memory/services/messages.py:34` **`MessageService`** — 记忆消息全生命周期(类方法)。索引名 `index_name:29`(`memory_{prefix}_{uid}`);`insert_message:51`、`update_message:57`、`delete_message:64`、`list_message:69`、`get_recent_messages:125`、`search_message:151`(混合检索)、容量管理 `calculate_memory_size:186` / FIFO 淘汰 `pick_messages_to_delete_by_fifo:218`。
- `memory/services/query.py:43` **`MsgTextQuery(QueryBase)`** — 全文检索查询构建;`question:49`(分词/同义词扩展/term weighting → `MatchTextExpr`)、`get_vector:27`(→ `MatchDenseExpr`)。

### Utils
- `memory/utils/es_conn.py:36` `ESConnection`(memory 专用,继承 `common/doc_store` 的 base);字段映射 `map_message_to_es_fields:52`、`search:112`、`get_forgotten_messages:263`。
- `memory/utils/infinity_conn.py:31` / `ob_conn.py:76` — Infinity / OceanBase 适配。
- `memory/utils/msg_util.py:19` `get_json_result_from_llm_response()`(解析记忆抽取 JSON);`prompt_util.py:22` `PromptAssembler`;`aggregation_utils.py:20`;`highlight_utils.py:23`。

> memory 有独立 `{es,infinity,ob}_conn.py`(继承 `common/doc_store/*_conn_base`),经 `settings.msgStoreConn` 注入;知识库检索走 `settings.docStoreConn`。两者共用 `doc_store_base.py` 的查询表达式与抽象接口。
