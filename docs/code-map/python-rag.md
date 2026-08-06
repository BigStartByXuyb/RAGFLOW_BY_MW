# `rag/` — RAG 核心引擎导航

> 真正的全局单例配置在 `common/settings.py`:`docStoreConn`(:90)、`retriever`(:93)、`kg_retriever`(:94),在 `init_settings()` 中实例化(:371、:374)。`rag/settings.py` 只是 license 占位。

## 目录结构

```
rag/
├── app/                  # 文档分块策略(按文档类型分派)
├── llm/                  # LLM 多厂商适配(chat/embed/rerank/cv/tts/ocr/seq2txt)
├── nlp/                  # 检索核心 + 中文分词/查询构造/词权重/同义词
├── svr/                  # 后台任务执行服务
│   └── task_executor_refactor/   # task_executor 重构版(服务化拆分)
├── graphrag/             # 知识图谱增强检索
│   ├── general/          #   标准 GraphRAG(实体抽取/社区报告/Leiden 聚类/索引)
│   ├── light/            #   LightRAG 轻量抽取
│   └── ner/              #   基于 NER 的图抽取
├── advanced_rag/         # Agentic RAG / 深度研究编排
│   ├── harness/          #   编排框架(orchestrator/tools/planner/prompts)
│   └── knowlege_compile/ #   知识预编译(RAPTOR/mind_map/wiki)
├── flow/                 # 数据流水线 DSL(parser→chunker→extractor→tokenizer)
├── prompts/              # 提示词模板(.md)+ 生成器
└── utils/                # 存储/连接工具(ES/Infinity/MinIO/S3/Redis 等)
```

## 文档分块 `rag/app/`

每模块暴露统一 `chunk(filename, binary, ...)` 入口,由 `svr/task_executor.py` 的 `FACTORY` 字典(:114)按 `parser_id` 分派。

| 文件:行号 | 文档类型 |
|---|---|
| `rag/app/naive.py:950` | 通用分块(默认);含 `Docx`(:445)/`Pdf`(:717)/`Markdown`(:761) |
| `rag/app/paper.py:135` | 学术论文(按章节/摘要结构化) |
| `rag/app/book.py:64` | 书籍长文档 |
| `rag/app/qa.py:289` | 问答对(Excel/Pdf/Docx) |
| `rag/app/table.py:384` | 表格数据(按行列结构化) |
| `rag/app/laws.py:168` | 法律条文(按条款) |
| `rag/app/manual.py:138` | 手册/说明书 |
| `rag/app/one.py:60` | 整文档不切分 |
| `rag/app/presentation.py:129` | 演示文稿(按页) |
| `rag/app/resume.py:2479` | 简历(结构化字段,需 tenant_id) |
| `rag/app/picture.py:41` / `audio.py:27` | 图片(OCR+视觉)/ 音频(语音转写) |
| `rag/app/email.py:29` / `tag.py:37` | 邮件 / 标签集 |

## LLM 接入层 `rag/llm/`

**统一封装**:每模块有抽象基类 `Base(ABC)`,厂商子类用类属性 `_FACTORY_NAME` 声明厂商;`rag/llm/__init__.py:165-195` 反射扫描自动注册进工厂字典(`ChatModel/EmbeddingModel/...`,:145-163)。新增厂商只需继承 + 加 `_FACTORY_NAME`。

| 文件:基类行号 | 职责 | 代表实现 |
|---|---|---|
| `rag/llm/chat_model.py:220` | 对话生成(60+ 厂商) | `chat`/`chat_streamly`;`OpenAI_APIChat`(:1053)、`GoogleChat`(:1259)、`LiteLLMBase`(:1579) |
| `rag/llm/embedding_model.py:146` | 文本向量化 | `BuiltinEmbed`(:222)、`OpenAIEmbed`(:258)、`QWenEmbed`(:379) |
| `rag/llm/rerank_model.py:32` | 结果重排 | `JinaRerank`(:96)、`CoHereRerank`(:284) |
| `rag/llm/cv_model.py:59` | 视觉/多模态 | `GptV4`(:332)、`QWenCV`(:407) |
| `rag/llm/tts_model.py:69` | 文字转语音 | `FishAudioTTS`(:141)、`OpenAITTS`(:240) |
| `rag/llm/sequence2txt_model.py:38` | 语音转文字 | `GPTSeq2txt`(:100) |
| `rag/llm/ocr_model.py:29` | OCR(混入 Parser) | `MinerUOcrModel`(:37)、`MistralOcrModel`(:332) |

其他:`model_meta.py`(元数据)、`tool_decorator.py`(function-calling)、`key_utils.py`(Key 加解密)。

## 检索逻辑 `rag/nlp/`

核心是 `search.Dealer`,全局实例 `settings.retriever`(`common/settings.py:371`);`KGSearch` 继承它,实例 `settings.kg_retriever`(:374)。`dialog_service.py:1690` 按是否走 KG 选择。

| 文件:行号 | 说明 |
|---|---|
| `rag/nlp/search.py:39` | **`class Dealer`** 检索核心类 |
| `rag/nlp/search.py:134` | `search()` 底层查询(全文 + KNN 向量召回) |
| `rag/nlp/search.py:549` | `retrieval()` **对外主检索入口**(混合检索+重排+分页) |
| `rag/nlp/search.py:461` | `rerank()` token 权重+向量相似度加权重排 |
| `rag/nlp/search.py:494` | `rerank_by_model()` 用 rerank 模型重排 |
| `rag/nlp/search.py:251` | `insert_citations()` 答案回插引用 |
| `rag/nlp/search.py:840` | `retrieval_by_toc()` 基于目录检索 |
| `rag/nlp/search.py:903` | `retrieval_by_children()` 父子块检索 |
| `rag/nlp/query.py:28` | `class FulltextQueryer` 全文查询构造 |
| `rag/nlp/query.py:42` | `question()` 问题转加权全文查询 |
| `rag/nlp/rag_tokenizer.py` | 中文分词器 |
| `rag/nlp/term_weight.py:27` / `synonym.py:34` | 词项权重 / 同义词扩展 |

## GraphRAG `rag/graphrag/`

| 文件:行号 | 说明 |
|---|---|
| `rag/graphrag/search.py:35` | **`class KGSearch(Dealer)`** 图谱检索器 |
| `rag/graphrag/search.py:139` | `retrieval()` 图谱增强检索主入口 |
| `rag/graphrag/general/index.py:256` | **`run_graphrag_for_kb()`** 知识库级图谱构建总入口 |
| `rag/graphrag/general/index.py:731` | `generate_subgraph()` 生成子图 |
| `rag/graphrag/general/index.py:821` | `merge_subgraph()` 合并子图 |
| `rag/graphrag/general/index.py:851` | `resolve_entities()` 实体消解 |
| `rag/graphrag/general/extractor.py:51` | `class Extractor` 抽取基类(`__call__`:131) |
| `rag/graphrag/general/leiden.py` | Leiden 社区聚类 |
| `rag/graphrag/light/graph_extractor.py` | LightRAG 轻量抽取 |
| `rag/graphrag/ner/ner_extractor.py` | 基于 NER 的实体抽取 |
| `rag/graphrag/utils.py:262` | `tidy_graph()` / `graph_merge()`(:306) |

## 任务执行服务 `rag/svr/`

| 文件:行号 | 说明 |
|---|---|
| `rag/svr/task_executor.py:1908` | **`main()`** 后台任务执行器进程主入口 |
| `rag/svr/task_executor.py:1741` | `handle_task()` 单任务处理循环 |
| `rag/svr/task_executor.py:1408` | `do_handle_task()` 任务分派核心 |
| `rag/svr/task_executor.py:114` | `FACTORY` parser_id → app 分块模块映射 |
| `rag/svr/task_executor.py:303` | `build_chunks()` 调 chunker 生成分块(:311 取 FACTORY) |
| `rag/svr/task_executor.py:713` | `embedding()` 分块向量化 |
| `rag/svr/task_executor.py:1292` | `insert_chunks()` 写入文档存储 |
| `rag/svr/task_executor.py:1060` | `run_raptor_for_kb()` RAPTOR 递归聚类摘要 |
| `rag/svr/task_executor.py:766` | `run_dataflow()` 执行 flow DSL |
| `rag/svr/task_executor.py:223` | `collect()` 从 Redis 队列拉任务 |
| `rag/svr/task_executor_refactor/` | 重构版:`task_handler.py` / `chunk_service.py` / `embedding_service.py` / `raptor_service.py` |

## Advanced RAG / Flow / Prompts

**Advanced RAG(Agentic)**
- `rag/advanced_rag/agentic_rag.py:71` `class RAGTools` — `retrieve()`(:352)、`web_retrieve()`(:411)、`structured_retrieve()`(:422)、`extract_keywords()`(:325)
- `rag/advanced_rag/harness/pipeline.py:19` `class Pipeline`(`execute`:35);`harness/orchestrator/` 三策略:`agentic.py`/`decompose.py`/`direct.py`
- `rag/advanced_rag/knowlege_compile/raptor.py` — RAPTOR 树构建

**Flow 流水线 DSL**
- `rag/flow/pipeline.py:28` `class Pipeline(Graph)`(`run`:118)
- `rag/flow/base.py:33` `class ProcessBase` 组件基类(`invoke`:41 / `_invoke`:59)
- `rag/flow/parser/parser.py:330` `class Parser`;`chunker/token_chunker.py` + `title_chunker/`;`compiler/compiler.py`

**Prompts**
- `rag/prompts/generator.py:139` `kb_prompt()`;`citation_prompt()`(:214);`vision_llm_describe_prompt()`(:357)
- `rag/prompts/*.md` — 60+ 模板(TOC 抽取/简历/跨语言/充分性检查)

## 核心链路

摄取:`task_executor.main()` → `do_handle_task()` → `build_chunks()`(FACTORY 分派 `rag/app/*.chunk()`)→ `embedding()` → `insert_chunks()` 写 `docStoreConn`;可选 `run_graphrag_for_kb()`/`run_raptor_for_kb()`。
查询:`dialog_service` → `settings.retriever`(Dealer)或 `settings.kg_retriever`(KGSearch)的 `retrieval()`。
