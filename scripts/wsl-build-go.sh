#!/bin/bash
# Builds RAGFlow's Go server binary (linux/amd64) inside the WSL distro.
#
# Run from Windows:
#   wsl -d ragflow -u root -e bash /root/build/ragflow-build.sh
#   wsl -d ragflow -u root -e bash /root/build/ragflow-build.sh --sync
#
# Options:
#   --sync   rsync the Windows working tree into the WSL build copy first
#
# The script is resumable: if WSL gets recycled mid-run, just run it again.
# It clears partial (zero-byte) downloads and retries until the module cache
# verifies, then builds.
#
# Overrides: REPO=... SRC=... LOG=... GOMAXPROCS=...
set -o pipefail

export HOME=/root
# Pin the Linux toolchain: WSL inherits the Windows PATH, where `go` resolves to
# go.exe. That silently downloads through the Windows network stack (no proxy)
# and leaves empty .mod files behind, which then fail go.sum verification.
export PATH=/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export GOPROXY=https://goproxy.cn,direct
export GOSUMDB=sum.golang.google.cn
export GOMAXPROCS=${GOMAXPROCS:-4}
# Keep the compiler's parallelism modest: the host is memory-tight and a wide
# build is what gets the WSL VM killed.
export GOFLAGS="-p=2"

# pdfium's static libc++ ships from Chromium's clang-20 toolchain. Linking it
# with clang 18 (Ubuntu's default) produces a binary that segfaults on startup
# with the instruction pointer on the stack, so pin clang++/ld.lld to 20.x.
if [ -x /usr/bin/clang++-20 ] && ! clang++ --version 2>/dev/null | head -n1 | grep -q 'version 20'; then
    ln -sf /usr/bin/clang++-20 /usr/bin/clang++
    ln -sf /usr/bin/clang-20 /usr/bin/clang
    ln -sf /usr/bin/ld.lld-20 /usr/bin/ld.lld
    echo ">>> switched clang++/clang/ld.lld to the 20.x toolchain"
fi
echo ">>> toolchain: $(clang++ --version | head -n1) / $(ld.lld --version | head -n1)"

REPO=${REPO:-/root/build/ragflow}
SRC=${SRC:-/mnt/d/RAG_FLOW/ragflow}
LOG=${LOG:-/root/build/build.log}

if [ "$1" = "--sync" ]; then
    echo ">>> syncing source: $SRC -> $REPO"
    rsync -a --delete \
        --exclude node_modules --exclude .venv --exclude __pycache__ \
        --exclude '*.pyc' --exclude '.playwright*' --exclude 'web/dist' \
        --exclude '.worktrees' \
        --exclude '/.git' \
        --exclude '/bin' --exclude '/cpp/cmake-build-release' --exclude '/cpp/build' \
        "$SRC/" "$REPO/" || exit 1
fi

cd "$REPO" || { echo "ERROR: repo not found at $REPO"; exit 1; }

CACHE=${GOMODCACHE:-/root/go/pkg/mod}/cache/download

echo ">>> dropping partial downloads left by interrupted runs"
find "$CACHE" -type f -size 0 -delete 2>/dev/null
find "$CACHE" -name '*.tmp' -delete 2>/dev/null

# A killed run can also leave the extracted module tree full of zero-byte
# source files; Go keeps trusting those, so wipe the whole cache in that case.
if find "${GOMODCACHE:-/root/go/pkg/mod}" -type f -size 0 2>/dev/null | grep -q .; then
    echo ">>> corrupt module tree detected, wiping the module cache"
    go clean -modcache
fi

# Go caches *failed* builds too: after a run is killed mid-compile, the next
# build replays "expected 'package', found 'EOF'" against files that are now
# fine. Clearing the build cache is what makes a rerun actually work.
echo ">>> clearing the Go build cache"
go clean -cache

echo ">>> fetching dependencies (retries until the cache verifies)"
attempt=0
while [ $attempt -lt 12 ]; do
    attempt=$((attempt + 1))
    echo ">>> go mod download (attempt $attempt)"
    go mod download 2>&1 | tail -3
    find "$CACHE" -type f -size 0 -delete 2>/dev/null
    if go mod verify > /dev/null 2>&1; then
        echo ">>> module cache verified after $attempt attempt(s)"
        break
    fi
    sleep 2
done

if ! go mod verify > /dev/null 2>&1; then
    echo ">>> WARNING: module cache still does not verify; continuing anyway"
fi

echo ">>> building the C++ static library + Go binaries (full log: $LOG)"
# build.sh fans the C++ build out to `nproc` jobs. Cap the visible CPU set so a
# wide build cannot starve the host and get this WSL VM recycled mid-compile.
# `nproc` honours the affinity mask, so taskset is enough.
JOBS=${JOBS:-4}
bash -c "taskset -c 0-$((JOBS - 1)) bash build.sh --all" 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}

if [ $rc -ne 0 ]; then
    echo ">>> BUILD FAILED (rc=$rc), last lines:"
    tail -20 "$LOG"
    exit $rc
fi

echo ">>> BUILD OK"
ls -la "$REPO/bin/"
