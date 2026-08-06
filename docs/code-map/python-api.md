# `api/` — HTTP 后端导航

> **框架**:Quart(异步、Flask 兼容),非经典 Flask。全局配置在 `common/settings.py`。
> 路由在导入时**自动发现注册**,无手写 blueprint 清单。

## 目录结构

```
api/
├── ragflow_server.py       # 主进程入口 (__main__)
├── settings.py             # 空占位(真实配置在 common/settings.py)
├── constants.py            # API_VERSION 等常量
├── apps/                   # HTTP 层
│   ├── __init__.py         #   Quart app 初始化 + blueprint 自动注册 + 认证
│   ├── auth/               #   OAuth / OIDC / GitHub 登录客户端
│   ├── restful_apis/       #   所有当前 REST 路由文件
│   │   └── utils/          #     请求校验辅助
│   └── services/           #   app 级服务胶水层
├── channels/               # 聊天机器人渠道(钉钉/飞书/Discord/Telegram/微信等)
│   └── core/               #   base.py / registry.py 渠道抽象
├── db/                     # 数据层
│   ├── db_models.py        #   所有 Peewee ORM 模型 + DB 连接
│   ├── init_data.py        #   种子数据 + 超级用户初始化
│   ├── joint_services/     #   跨模型服务
│   └── services/           #   每模型业务逻辑服务
└── utils/                  # api_utils / crypt / file_utils 等
```

## 启动入口

- `api/ragflow_server.py:82` — `__main__`。流程:init logger(:84)→ load settings(:96)→ `init_web_db()`(:106)→ `init_web_data()`(:107)→ load plugins(:129)→ 启动 `update_progress` 线程(:159)→ 启动 chat channels(:160)→ `app.run()`(:165)。
- app 对象:`from api.apps import app`(`ragflow_server.py:36`)。
- `api/db/runtime_config.py:20` `RuntimeConfig` — DEBUG/host/port。

## HTTP 入口与路由注册

- `api/apps/__init__.py:61` — `app = Quart(__name__)`;CORS(:62)、QuartSchema/OpenAPI(:65)、session/redis(:78-83)。
- `api/apps/__init__.py:349` `register_page()` + `:340` `search_pages_path()` — 扫描目录注册每个文件的 `manager` Blueprint,循环在 `:376`。
- URL 前缀:`restful_apis/` 下的文件前缀 `/api/{API_VERSION}`;其余 `/{API_VERSION}/{page_name}`(`:362-363`)。
- 错误处理器:404/401/ModelException 在 `:384-418`;DB teardown 在 `:421`。
- 向后兼容路由:`api/apps/backward_compat.py`(`__init__.py:379-381`)。

## 主要路由文件(均在 `api/apps/restful_apis/`,前缀 `/api/{API_VERSION}`)

| 文件 | 主要 API |
|---|---|
| `user_api.py:61` | 认证 `/auth/login`、`/auth/logout`、OAuth 登录+回调(:165,:179)、用户 CRUD、密码/OTP |
| `dataset_api.py:37` | 知识库 CRUD `/datasets`、tags、metadata、知识图谱、wiki |
| `document_api.py:99` | 文档:上传、解析、停止、metadata、缩略图、ingest |
| `chunk_api.py:181` | 分块 `/datasets/<id>/chunks` CRUD + 检索 |
| `chat_api.py:360` | 对话(dialog)+ sessions/messages CRUD |
| `bot_api.py:54` | `/chatbots/<dialog_id>/completions` |
| `agent_api.py:430` | `/agents/<id>/sessions` — agent/canvas 会话 |
| `models_api.py:31` / `provider_api.py:30` | 模型列表/默认模型;LLM provider 管理 |
| `tenant_api.py:41` | `/tenants/<id>/users` 租户成员 |
| `file_api.py:45` / `file2document_api.py:99` / `file_commit_api.py:107` | 文件存储/关联/版本 |
| `search_api.py:43` | `/searches` 保存的搜索应用 |
| `mcp_api.py:70` | `/mcp/servers` MCP server 注册 |
| `memory_api.py:30` | `/memories` 记忆存储 |
| `connector_api.py:49` | 数据连接器 |
| `openai_api.py:237` | OpenAI 兼容 `/openai/<chat_id>/chat/completions` |
| `dify_retrieval_api.py:111` | `/dify/retrieval` Dify 集成 |
| `stats_api.py:24` / `system_api.py:38` | 健康检查/统计 |

## 认证

- `api/apps/__init__.py:144` `_load_user()` — 从 Bearer/JWT/API/Beta token 解析用户;`:110` `_load_user_from_session()` cookie 兜底;token 类型定义 `:94-97`。
- `api/apps/__init__.py:235` `login_required` 装饰器;`login_user()`/`logout_user()` 在 `:283`/`:316`。
- JWT:`itsdangerous URLSafeTimedSerializer` + `settings.get_secret_key()`(`:187`)。
- OAuth 客户端工厂:`api/apps/auth/__init__.py:25` `get_auth_client()` → `oauth.py:32` `OAuthClient`(基类)/ `oidc.py:69` `OIDCClient` / `github.py:21` `GithubOAuthClient`。
- Token 模型:`APIToken`(`api/db/db_models.py:1068`)。

## 数据库层

- `api/db/db_models.py` — 全部 Peewee 模型。DB 连接 `DB`(:627);基类 `BaseModel:151` / `DataBaseModel:639`;支持 MySQL/Postgres/OceanBase。
- 建表:`init_database_tables()`(:646);`close_connection()`(:631)。
- 种子:`api/db/init_data.py` — `init_web_data():137`、`init_superuser():47`、`add_graph_templates():109`、`add_compilation_templates():133`。
- 查询辅助:`api/db/db_utils.py` — `query_db():102`、`bulk_insert_into_db():27`。
- 枚举:`api/db/__init__.py` — `UserTenantRole:23`、`TenantPermission:30`、`FileType:40`、`CanvasCategory:60`。

**关键模型**(`api/db/db_models.py`):`User:679`、`Tenant:722`、`UserTenant:748`、`LLMFactories:772`/`LLM:786`/`TenantLLM:805`、`Knowledgebase:837`、`Document:894`、`File:924`、`Task:1002`、`Dialog:1020`、`Conversation:1056`、`APIToken:1068`、`UserCanvas:1101`/`CanvasTemplate:1119`、`MCPServer:1146`、`Search:1189`、`Connector:1260`、`Memory:1349`、`SystemSettings:1372`。

**每模型服务**(`api/db/services/`):`user_service.py`、`knowledgebase_service.py`、`document_service.py`、`dialog_service.py`(检索问答核心)、`conversation_service.py`、`canvas_service.py`、`task_service.py`、`llm_service.py`、`common_service.py`(共享 CRUD 基类)等。跨模型:`api/db/joint_services/`。

## 常用工具

- `api/utils/api_utils.py` — `server_error_response`、`get_json_result`(全局标准响应封装)。
- `api/utils/crypt.py` — 密码/token 加密。
- `api/common/check_team_permission.py` — 团队/租户权限校验。
- `api/apps/services/` — 桥接路由与 db 服务:`dataset_api_service.py`、`document_api_service.py`、`canvas_replica_service.py` 等。
- `api/channels/bootstrap.py:start_channel_server` — 启动聊天渠道监听(`ragflow_server.py:141`);渠道插件系统:`api/channels/core/registry.py` + `core/base.py`。

## 踩坑提醒

- 全局配置/secret-key/DB 走 `common/settings.py`(`settings.init_settings()` 在 `apps/__init__.py:40` 调用),**不是** `api/settings.py`。
