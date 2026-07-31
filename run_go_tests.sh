#!/bin/bash
set -e

PACKAGES=(
    "./go/admin/..."
#    "./go/binding/..."
    "./go/cache/..."
    "./go/cli/..."
    "./go/common/..."
    "./go/dao/..."
    "./go/engine/..."
    "./go/entity/..."
    "./go/handler/..."
    "./go/ingestion/..."
    "./go/router/..."
    "./go/server/..."
    "./go/service/..."
    "./go/storage/..."
    "./go/tokenizer/..."
    "./go/utility/..."
)

echo "Running tests for specific packages..."
for pkg in "${PACKAGES[@]}"; do
    echo "=== Testing $pkg ==="
    go test $pkg -v -cover -test.v
    echo ""
done

#echo "Running all tests except failed packages..."
#go test $(go list ./go/... | grep -v -E '(cli|service|binding)$') -v