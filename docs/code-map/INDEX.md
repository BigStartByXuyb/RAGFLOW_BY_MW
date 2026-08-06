# RAGFlow 代码导航地图 · 索引

> 两层懒加载结构。本文件是精简索引:先在这里定位到模块,再按需打开对应详情文件。
> 所有路径均相对仓库根 `D:\RAG_FLOW\ragflow\`。文件引用格式 `路径:行号` 可直接点击跳转。

## 整体架构一句话

RAGFlow = **Python 双擎(AI 密集型) + Go 后端(高并发编排) + React 前端**。
Python 侧负责文档解析、向量计算、LLM 调用、Agent 编排;Go 侧(`internal/`)负责 HTTP 服务、业务编排、任务调度;两者通过 NATS 协作。本地图目前只覆盖 **Python 部分**。

## Python 模块索引

| 模块 | 一句话职责 | 详情文件 |
|---|---|---|
| `api/` | Quart(异步 Flask 兼容)HTTP 后端:REST 路由、认证、Peewee ORM、启动入口 | [python-api.md](python-api.md) |
| `rag/` | RAG 核心引擎:文档分块、LLM 多厂商适配、混合检索、GraphRAG、任务执行器 | [python-rag.md](python-rag.md) |
| `agent/` | Agent 编排引擎:Canvas 工作流运行时、组件节点、工具调用、代码沙箱、18 个模板 | [python-agent.md](python-agent.md) |
| `deepdoc/` | 文档深度解析:PDF/Office 等解析器 + OCR/版面/表格视觉识别(ONNX),可独立部署 | [python-deepdoc.md](python-deepdoc.md) |
| `common/` `sdk/` `mcp/` `memory/` | 公共工具库、官方 Python SDK、MCP Server/Client、对话记忆服务 | [python-common.md](python-common.md) |

## 关键跨模块事实(避免踩坑)

- **配置单例在 `common/settings.py`**,不是 `api/settings.py` / `rag/settings.py`(后两者是空占位/license 桩)。`init_settings()` 装配 `docStoreConn`、`retriever`、`kg_retriever`、`msgStoreConn` 等全局对象。
- **路由自动注册**:`api/apps/__init__.py` 导入时扫描目录注册 Blueprint,没有手写的 `register_blueprint` 清单。
- **组件/工具/LLM 厂商均为约定式自动注册**:靠反射扫描类 + `_FACTORY_NAME` / 类名,新增无需改注册代码。
- **MCP 双身份别混淆**:`mcp/` 是对外 MCP Server(把检索暴露为工具);`common/mcp_tool_call_conn.py` 是 MCP Client(让 agent 调外部 MCP 工具)。
- **检索器两条路**:普通检索 `settings.retriever`(`rag/nlp/search.py` 的 `Dealer`);知识图谱检索 `settings.kg_retriever`(`rag/graphrag/search.py` 的 `KGSearch`,继承 Dealer)。

## 核心数据链路(速记)

- **摄取(构建期)**:`rag/svr/task_executor.py:main()` 消费队列 → `do_handle_task()` → `build_chunks()`(经 `FACTORY` 分派到 `rag/app/*.chunk()`)→ `embedding()` → `insert_chunks()` 写入 `docStoreConn`;可选 `run_graphrag_for_kb()` / `run_raptor_for_kb()`。
- **问答(查询期)**:`api/apps/restful_apis/chat_api.py` → `api/db/services/dialog_service.py` → `settings.retriever`/`kg_retriever` 的 `retrieval()` → LLM(`rag/llm/chat_model.py`)生成 + 引用回插。

## 维护约定

- 每个详情文件独立更新,改了哪个模块只动对应文件。
- 新增 Python 顶级模块时,在本索引表加一行 + 建对应 `python-*.md`。
- 行号会随代码变动漂移,引用前用搜索确认关键类/函数仍在。
