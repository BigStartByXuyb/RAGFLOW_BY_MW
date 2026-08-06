# `agent/` — Agent 编排引擎导航

> 以 JSON DSL 定义有向图(components + downstream/upstream),由 `Canvas` 运行时逐节点异步执行,支持流式事件、工具调用、代码沙箱、多智能体协作。

## 目录结构

```
agent/
├── canvas.py             # 【核心】运行时:Graph/Canvas 类,DSL 解析 + 执行引擎
├── dsl_migration.py      # 旧版 DSL schema 迁移
├── settings.py           # 参数校验常量
├── component/            # 编排控制类组件 + 基类
│   ├── base.py           #   ComponentBase / ComponentParamBase
│   ├── __init__.py       #   组件自动发现与注册(component_class 工厂)
│   └── *.py              #   begin/llm/agent_with_tools/categorize/switch/iteration/loop/...
├── tools/                # LLM 可调用工具(搜索/检索/代码执行等)
│   ├── base.py           #   ToolBase / ToolParamBase / 调用会话
│   └── *.py              #   retrieval/code_exec/tavily/google/arxiv/... (20+)
├── sandbox/              # 代码沙箱
│   ├── client.py         #   统一入口 + provider 加载
│   ├── providers/        #   6 种后端(local/ssh/e2b/aliyun/tenki/self_managed)
│   └── executor_manager/ #   自托管沙箱服务(FastAPI + Docker)
├── plugin/               # LLM 工具插件系统(pluginlib)
├── templates/            # 18 个预置 Agent 工作流 JSON
└── test/dsl_examples/    # 7 个 DSL 示例
```

## 核心运行时 `canvas.py`

| 文件:行号 | 说明 |
|---|---|
| `agent/canvas.py:49` | `class Graph` 图基类(docstring 49-88 给出完整 DSL 结构范例) |
| `agent/canvas.py:90` | `Graph.__init__` 接收 dsl 字符串 → json.loads → 迁移 → `load()` |
| `agent/canvas.py:102` | `Graph.load` **DSL → 运行对象核心转换**:建参数、`param.check()`、实例化组件存入 `cpn["obj"]` |
| `agent/canvas.py:202/231/283` | `get_value_with_variable`/`get_variable_value`/`set_variable_value` 变量引用解析(`{cpn@var}`/`{sys.x}`/`{env.x}`) |
| `agent/canvas.py:330` | `class Canvas(Graph)` 实际运行时(globals/history/retrieval/memory 状态) |
| `agent/canvas.py:429` | `Canvas.run`(async 生成器)**主执行入口** |
| `agent/canvas.py:470` | `Canvas._run_impl` **核心执行循环**,yield 流式事件(workflow_started/node_started/message/node_finished/user_inputs) |
| `agent/canvas.py:546` | `_run_batch` asyncio+线程池并发执行同批组件 |
| `agent/canvas.py:711-761` | 路径推进:按组件类型(iteration/loop/categorize/switch)扩展 `path` |

外部调用点:`api/db/services/canvas_service.py:316`(实例化 Canvas)与 `:344`(`async for ans in canvas.run(...)`)。

## 组件节点 `component/`

**基类** `agent/component/base.py`:
- `:43` `ComponentParamBase(ABC)` — `update()`(:136 递归配置注入)、`check()`(:60 子类必实现)、各 `check_*` 校验器。
- `:351` `ComponentBase(ABC)` — `:358` `variable_ref_patt_re`(变量引用正则)、`:398/412` `invoke`/`invoke_async`(计时+异常包装)、`:441` `_invoke`(抽象,真正逻辑)、`:444/449/469` `output`/`set_output`/`get_input`。

**注册** `agent/component/__init__.py`:
- `:26` `_import_submodules` + `:39` 提取类 → 自动注册进 `__all_classes`(约定式,无需手动登记)。
- `:53` `component_class(class_name)` **工厂函数**:依次在 `agent.component`、`agent.tools`、`rag.flow` 查找,供 canvas 动态实例化。

**组件类型**:

| 组件 | 位置 | 作用 |
|---|---|---|
| Begin | `component/begin.py:36` | 入口(继承 UserFillUp),支持 conversational/task/Webhook |
| UserFillUp | `component/fillup.py:36` | 运行中向用户请求补充输入 |
| LLM | `component/llm.py:86` | LLM 生成(所有 LLM 类父类) |
| Agent | `component/agent_with_tools.py:74` | 带工具/MCP/子 Agent 的智能体(继承 LLM+ToolBase) |
| Categorize | `component/categorize.py:90` | LLM 意图分类路由(输出 `_next`) |
| Switch | `component/switch.py:56` | 条件分支 |
| Iteration/IterationItem | `component/iteration.py:45` | 数组遍历循环 |
| Loop/LoopItem/ExitLoop | `component/loop.py:39` / `exit_loop.py:26` | 条件循环 |
| Message | `component/message.py:66` | 消息输出(流式+TTS) |
| Invoke | `component/invoke.py:58` | 外部 HTTP 调用 |
| VariableAggregator/Assigner | `variable_aggregator.py:55` / `variable_assigner.py:40` | 变量聚合/赋值 |
| StringTransform | `component/string_transform.py:48` | 字符串处理 |
| DataOperations/ListOperations | `data_operations.py:44` / `list_operations.py:49` | 数据/列表操作 |
| Browser/DocGenerator/ExcelProcessor | `browser.py:84` / `docs_generator.py:76` / `excel_processor.py:82` | 浏览器/文档/Excel |

`Agent`(agent_with_tools.py)同时继承 `LLM` + `ToolBase`,`__init__`(:77)加载子工具(`_load_tool_obj`:136)、绑定 MCP、构建 `LLMToolPluginCallSession` 并 `bind_tools` —— 多智能体/工具编排核心。

## 工具调用 `tools/`

**基类** `agent/tools/base.py`:
- `:34/42` `ToolParameter`/`ToolMeta` 工具元数据 schema。
- `:50` `LLMToolPluginCallSession(ToolCallSession)` — `:55/58` `tool_call`/`tool_call_async` 是 function-calling 实际分发点(区分本地工具/MCPToolBinding/MCPToolCallSession)。
- `:98` `ToolParamBase(ComponentParamBase)` — `:105` `_init_inputs`、`:115` `get_meta`(生成 OpenAI function schema)。
- `:135` `ToolBase(ComponentBase)` — `:148/164` `invoke`/`invoke_async`;`:191` `_retrieve_chunks`(外部结果转引用 chunk)。

**工具实现**(每文件一对 Param+Tool 子类):
- 检索/执行:`retrieval.py:82`(知识库检索,`RetrievalParam`:37)、`code_exec.py:323`(对接 sandbox)、`exesql.py:71`、`crawler.py:55`、`email.py:73`
- 搜索:`tavily.py:92`、`google.py:478`、`duckduckgo.py:63`、`searxng.py:69`、`bgpt.py:74`
- 学术:`arxiv.py:56`、`pubmed.py:66`、`googlescholar.py:61`、`wikipedia.py:133`
- 金融/数据:`akshare.py:53`、`tushare.py:44`、`yahoofinance.py:62`、`qweather.py:112`
- 其他:`github.py:55`、`deepl.py:80`

## 代码沙箱 `sandbox/`

- `agent/sandbox/client.py:39` `get_provider_manager`(单例);`:57` `_load_provider_from_settings`;`:83` `provider_classes` 映射 6 种后端(self_managed/aliyun_codeinterpreter/e2b/local/ssh/tenki)。`code_exec.py:354` 通过 `execute_code` 调用。
- Provider 抽象:`sandbox/providers/base.py:47` `ExecutionResult`(stdout/stderr/exit_code/execution_time);实现在 `providers/local.py`/`ssh.py`/`e2b.py` 等。
- 自托管服务:`sandbox/executor_manager/`(FastAPI):`main.py`、`api/routes.py`、`core/container.py`(Docker 生命周期)、`services/security.py` + `seccomp-profile-default.json`(系统调用限制)。部署:`sandbox/docker-compose.yml`。

## 预置模板 `templates/`

JSON 格式,顶层字段:`id`/`title`(多语言)/`description`/`canvas_type`/`dsl`(完整可运行 canvas)。参考 `templates/deep_research.json` 的 Agent 内嵌子 Agent(tools 里再套 `component_name:"Agent"`)多智能体编排。

18 个模板:`advanced_ingestion_pipeline`、`cajal_scientific_paper_agent`、`chunk_summary`、`customer_feedback_dispatcher`、`cv_analysis_and_candidate_evaluation`、`data_analysis_beginner_assistant`、`deep_research`、`market_seo_article_writer`、`photo_text_translator`、`reflective_academic_paper_generator`、`seo_article_writer`、`smart_customer_service_specialist`、`stock_market_research_assistant`、`text2sql_data_expert`、`title_chunker`、`trip_planner`、`user_interaction`、`web_search_assistant`、`your_starter_dataset_chatbot`。

`test/dsl_examples/` 有 7 个精简 DSL 示例,适合快速理解骨架。

## 速查

| 关注点 | 文件:行号 |
|---|---|
| 运行时主入口 | `agent/canvas.py:429` `Canvas.run` |
| 执行循环 | `agent/canvas.py:470` `Canvas._run_impl` |
| DSL→对象加载 | `agent/canvas.py:102` `Graph.load` |
| 组件工厂/注册 | `agent/component/__init__.py:53` `component_class` |
| 组件基类 | `agent/component/base.py:351` `ComponentBase` |
| 工具基类 | `agent/tools/base.py:135` `ToolBase` |
| 多智能体 | `agent/component/agent_with_tools.py:74` `Agent` |
| 沙箱入口 | `agent/sandbox/client.py:39` |
| 外部调用点 | `api/db/services/canvas_service.py:316,344` |

**数据流要点**:DSL 是组件图,`Canvas` 维护 `path`/`globals`(含 `sys.*`/`env.*`)/`history`/`retrieval` 四类状态;组件用 `{cpn_id@output_var}` 引用上游输出;`_run_impl` 按组件类型(categorize/switch 的 `_next`、iteration/loop 的 start/parent)动态扩展 `path` 实现分支循环。component/tools/rag.flow 三命名空间共用同一套注册机制。
