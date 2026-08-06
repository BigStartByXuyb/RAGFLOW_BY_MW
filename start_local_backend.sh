#!/usr/bin/env bash

set -u

ROOT="/mnt/d/RAG_FLOW/ragflow/.claude/worktrees/dev-private"
cd "$ROOT" || exit 1

source .venv/bin/activate
export PYTHONPATH="$ROOT"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

mkdir -p logs

python api/ragflow_server.py >> logs/ragflow_server.console.log 2>&1 &
RAGFLOW_PID=$!

python admin/server/admin_server.py >> logs/admin_server.console.log 2>&1 &
ADMIN_PID=$!

python rag/svr/task_executor.py -i 0 >> logs/task_executor.console.log 2>&1 &
WORKER_PID=$!

cleanup() {
  kill "$RAGFLOW_PID" "$ADMIN_PID" "$WORKER_PID" 2>/dev/null || true
  wait "$RAGFLOW_PID" "$ADMIN_PID" "$WORKER_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM
wait
