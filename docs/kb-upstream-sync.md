# 与上游同步知识库改动

本分支（`codex/kb-sync`）用于把 `upstream/main` 的知识库改动搬进本仓库，同时**不重新引入**已删除的 DataFlow 流水线与画布 Agent。

## 前提

- 上游仍在维护 `agent/`、`rag/flow/`、`web/src/pages/agent*`、`web/src/pages/dataflow-result/`，直接 `git merge upstream/main` 会产生约 237 个 modify/delete 冲突，以及 `internal/` → `go/` 目录改名带来的数千文件冲突，不可行。
- 因此按**路径范围分批 adopt**：对一批白名单路径直接取上游版本，再重放本仓库自己的改动，最后跑审计。
- Go / C++ 目录（本仓库的 `go/`、`cpp/`）与上游已结构性分叉，本流程不碰。

## 批次划分

| 批次 | 范围 | 状态 |
| --- | --- | --- |
| 1 | `deepdoc/`、`rag/app/`、`rag/nlp/`、`rag/utils/`、`rag/llm/`、`rag/prompts/`、`conf/`、`common/*.py` | 已完成（见 `sync(kb): adopt upstream knowledge-base core`） |
| 2 | `api/` 知识库与检索接口（`api/apps/restful_apis/`、`api/apps/services/`、`api/db/`），需与删除改造手工合并 | 待做 |
| 3 | `rag/svr/`、`rag/advanced_rag/`、`common/data_source/`（含新连接器）、`memory/` | 待做 |
| 4 | 前端知识库页面（`web/src/pages/dataset*`、`chunk`、`files`、`next-search*`、`document-viewer` 及对应 hooks/locales） | 待做 |
| 5 | 需要重做删除的混合批次（`mixed-removed-and-kept` 68 个提交） | 待做 |

批次 2 与 4 的路径同时被本仓库的删除改造动过（约 90 个文件），adopt 之后必须逐个重放删除改动。

## 单批操作步骤

在同步 worktree（`D:\RAG_FLOW\ragflow-kb-sync`）内执行：

```bash
git fetch upstream
git checkout upstream/main -- <批次路径>
# 重放本仓库改动：对照 `git diff <fork point> HEAD -- <路径>`，把删除相关的改动加回去
git checkout HEAD -- <本批要保留为旧版的文件>
python scripts/kb_sync_audit.py --lock <上游 uv.lock>
git add -A && git commit
```

审计脚本会检查四类问题：语法错误、未改动文件对被 adopt 模块的失效导入、是否重新引入已删除功能、上游 lock 里解析不到的第三方依赖。三者必须为 0 才能提交。

## 已知需要手工处理点

- `common/token_utils.py`：上游把模块级 `encoder` 换成惰性 `get_encoder()`，同步后所有旧调用点都要改成 `get_encoder()`。
- RAPTOR：上游移除了 `get_raptor_tree_builder` / `get_raptor_clustering_method` 等配置项，改为固定 `tree_builder = "raptor"`、`clustering_method = "watershed"`。
- `common/settings.py` 会硬引用 `rag/utils/gaussdb_conn.py` 与 `memory/utils/gaussdb_conn.py`，adopt 时必须一起取这两个文件。
- `pyproject.toml` / `uv.lock` 需与代码批次一起同步（上游新增 `trafilatura`、`rapidfuzz`、`langdetect`、`regex` 等依赖）。

## 验证

本仓库当前没有可用的后端虚拟环境，批次验证止于静态检查。跑运行时验证前先执行 `uv sync --python 3.13 --all-extras`，然后至少覆盖：

```bash
uv run pytest test/unit_test/rag test/unit_test/common
ruff check
cd web && npm run type-check && npm run lint
```
