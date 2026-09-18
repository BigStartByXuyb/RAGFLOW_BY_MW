#!/bin/bash
# Runs Go tests for a package inside the WSL distro, with the same toolchain
# pinning and CGO/native-lib flags that build.sh wires. Raw `go test` in this
# repo misses those flags, so always go through this script instead.
#
# Usage (from Windows):
#   wsl -d ragflow -u root -e bash /mnt/d/RAG_FLOW/ragflow/scripts/wsl-test-go.sh --sync ./go/ingestion/service/...
#
# Options:
#   --sync   rsync the Windows working tree into the WSL build copy first
#
# Overrides: REPO=... SRC=... LOG=... GOMAXPROCS=...
set -o pipefail

export HOME=/root
# WSL inherits the Windows PATH, where `go` resolves to go.exe. Pin the Linux
# toolchain so module downloads and the compiler come from the distro.
export PATH=/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export GOPROXY=https://goproxy.cn,direct
export GOSUMDB=sum.golang.google.cn
export GOMAXPROCS=${GOMAXPROCS:-4}
export GOFLAGS="-p=2"

# pdfium's static libc++ ships from Chromium's clang-20 toolchain; linking it
# with clang 18 yields a binary that segfaults on startup.
if [ -x /usr/bin/clang++-20 ] && ! clang++ --version 2>/dev/null | head -n1 | grep -q 'version 20'; then
    ln -sf /usr/bin/clang++-20 /usr/bin/clang++
    ln -sf /usr/bin/clang-20 /usr/bin/clang
    ln -sf /usr/bin/ld.lld-20 /usr/bin/ld.lld
fi

REPO=${REPO:-/root/build/ragflow}
SRC=${SRC:-/mnt/d/RAG_FLOW/ragflow}
LOG=${LOG:-/root/build/test.log}

if [ "$1" = "--sync" ]; then
    shift
    echo ">>> syncing source: $SRC -> $REPO"
    rsync -a --delete \
        --exclude node_modules --exclude .venv --exclude __pycache__ \
        --exclude '*.pyc' --exclude '.playwright*' --exclude 'web/dist' \
        --exclude '.worktrees' \
        --exclude '/bin' --exclude '/cpp/cmake-build-release' --exclude '/cpp/build' \
        "$SRC/" "$REPO/" || exit 1
fi

PKGS=("$@")
if [ ${#PKGS[@]} -eq 0 ]; then
    PKGS=("./go/...")
fi

cd "$REPO" || { echo "ERROR: repo not found at $REPO"; exit 1; }

echo ">>> toolchain: $(clang++ --version | head -n1)"
echo ">>> testing: ${PKGS[*]}"
bash build.sh --test "${PKGS[@]}" 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}
echo ">>> test rc=$rc (full log: $LOG)"
exit $rc
