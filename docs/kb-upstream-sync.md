# 与上游同步知识库改动

目标：把 `upstream/main` 的知识库修复搬进本仓库，同时**不重新引入**已删除的 DataFlow 流水线与画布 Agent。

## 为什么不用 merge

- 上游仍在维护 `agent/`、`rag/flow/`、`web/src/pages/agent*`、`web/src/pages/dataflow-result/`，而这些目录我们已删除（651 个文件）。
- 分叉以来上游改了其中 237 个文件，`git merge upstream/main` 会产生大量 modify/delete 冲突；另有 `internal/` → `go/` 目录改名带来的数千文件冲突。
- Go / C++ 目录（本仓库的 `go/`、`cpp/`）与上游已结构性分叉，本流程不碰。

## 选择标准（越靠前越保守）

1. **精确可摘**：提交涉及的每个文件在本仓库中仍等于该提交父提交的版本，补丁可原样应用。
2. **三方可摘**：补丁在本仓库上做三方合并无冲突（在隔离 worktree 里逐个试跑确认）。
3. **手工合并**：需要逐块解决冲突，仅在确认价值后才做。

当前批次只使用第 1、2 档，不做任何手工冲突解决。

## 批次记录

| 批次 | 方式 | 结果 |
| --- | --- | --- |
| 1 | 精确可摘 13 个 + 三方可摘 51 个，共 64 个上游提交（`git cherry-pick -x`） | 103 文件，+6406/−559，审计四项全 0 |

候选池：`upstream/main` 中触及 `api|rag|deepdoc|conf|common|test` 的提交，排除触及 `agent/`、`rag/flow/`、`web/` 的提交，以及本仓库已改动或已删除的文件。

## 单批步骤

```bash
git fetch upstream
git worktree add --detach /tmp/cherrycheck <fork-baseline>   # 隔离试跑，避免污染同步 worktree
# 1) 精确可摘：逐文件比较 HEAD:<file> 与 <hash>^:<file> 的 blob 是否一致
# 2) 三方可摘：在隔离 worktree 里对每个提交执行 git cherry-pick -n，冲突则 abort + reset
# 3) 在同步分支按时间顺序 git cherry-pick -x <hash>，遇到冲突就跳过并记录
python scripts/kb_sync_audit.py --range <baseline>..HEAD --lock <upstream uv.lock>
```

审计四项必须全为 0 才能提交：语法错误、未改动文件对被摘取模块的失效导入、重新引入已删除功能、上游 lock 解析不到的第三方依赖。

## 待处理的联动点

- 摘取涉及 `api/` 或 `web/` 的批次时，路径会与删除改造重叠（约 90 个文件），需要逐个重放删除改动。
- `pyproject.toml` / `uv.lock` 尚未同步；涉及新依赖的批次必须一起更新。
- 本仓库当前没有后端虚拟环境，批次验证止于静态检查。跑运行时验证前先 `uv sync --python 3.13 --all-extras`，再至少覆盖 `uv run pytest test/unit_test/rag test/unit_test/common` 和 `ruff check`。
