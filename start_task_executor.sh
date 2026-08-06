#!/bin/bash
# 启动 RAGFlow task_executor(解析 worker)
cd /mnt/d/RAG_FLOW/ragflow/.claude/worktrees/dev-private || exit 1
export PYTHONPATH=$(pwd)
export HF_ENDPOINT=https://hf-mirror.com
export LLM_TIMEOUT_SECONDS=60
exec /home/xuyb/ragflow-venv/bin/python rag/svr/task_executor.py
